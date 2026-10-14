# CodeAgent 实现文档

> 面向「想要据此自建同类 AI 编程助手」的开发者。本文逐模块拆解 codeagent 的真实实现：它内部怎么做工具调用、怎么做上下文管理、怎么做权限、怎么实现记忆 / Skill / Hook / Subagent / Worktree / Teams / MCP。
>
> 项目版本：`0.2.0`（pyproject.toml 声明），Python ≥ 3.11，本文在 Python 3.13 + `uv` 环境下核验。
> 源码根目录：`codeagent/`，共约 2.2 万行 Python。

---

## 目录

- [0. 阅读指南](#0-阅读指南)
- [1. 项目概览与技术栈](#1-项目概览与技术栈)
- [2. 目录结构总览（模块地图）](#2-目录结构总览模块地图)
- [3. 启动流程（三种模式）](#3-启动流程三种模式)
- [4. 配置系统](#4-配置系统)
- [5. LLM 客户端与三种协议](#5-llm-客户端与三种协议)
- [6. 会话管理与序列化](#6-会话管理与序列化)
- 7. Agent 主循环（事件模型）
- 8. 工具系统
- 9. 系统提示词与上下文管理
- 10. 权限系统
- 11. 沙箱（bwrap / seatbelt）
- 12. MCP 集成
- 13. 记忆系统
- 14. Skill
- 15. Hook
- 16. Subagent
- 17. Worktree
- 18. Teams（多智能体）
- 19. 命令系统（斜杠命令）
- 20. 远程 / 浏览器模式与 TUI
- 21. 附录：配置文件完整示例 + 自建清单

---

## 0. 阅读指南

- 每个章节都会写「**它是怎么做的**」，即代码里真实的类名、函数名、数据结构、文件格式和调用链，而不是泛泛而谈。
- 关键流程用 `1)` `2)` `3)` 编号；文件引用用 `路径:行号` 风格标注（以源码为准）。
- 章节 7 之后的正文直接由「源码逐文件精读」产出，你可以按任意顺序阅读，也可以在自建时把它当作一份「模块规格说明书」。

---

## 1. 项目概览与技术栈

codeagent 是一个**终端（TUI）AI 编程助手**，形态类似 Claude Code / amp / OpenCode：在终端里与用户对话，通过一个「工具调用循环」（agent loop）读写文件、执行命令、调度子代理，完成编码任务。

技术栈（来自 `pyproject.toml`）：

| 依赖 | 版本要求 | 用途 |
|---|---|---|
| `textual` | ≥2.1（实装 8.2.5） | 终端 UI 框架 |
| `anthropic` | ≥0.42（实装 0.98.1） | Anthropic 协议客户端 |
| `openai` | ≥1.60（实装 2.34） | OpenAI / OpenAI 兼容客户端 |
| `mcp` | ≥1.12（实装 1.27） | Model Context Protocol 客户端 |
| `pyyaml` / `pydantic` | ≥6.0 / ≥2.0 | 配置解析与校验 |
| `httpx` / `websockets` | ≥0.27 / ≥14 | 网络（远程/浏览器模式的 WebSocket） |

运行入口：`pyproject.toml` 里 `[project.scripts] codeagent = "codeagent.__main__:main"`，即 `python -m codeagent`。

三种运行模式（由 `__main__.py` 的 `argparse` 决定）：

1. **TUI 交互模式**（默认）：`codeagent` → 启动 Textual 应用 `CodeAgentApp`。
2. **非交互 `-p` 模式**：`codeagent -p "提示词"` → 跑完一次 agent 任务后把最终文本打到 stdout（支持 `--output-format text|stream-json`）。
3. **远程/浏览器模式**：`codeagent --remote` → 在 `0.0.0.0:18888` 起一个 WebSocket 服务器，浏览器访问 `http://localhost:18888`。

---

## 2. 目录结构总览（模块地图）

`codeagent/` 下按职责分包：

```
codeagent/
├── __main__.py          # 入口：argparse → 三种模式分发
├── config.py            # 配置加载/合并（ProviderConfig、AppConfig、load_config）
├── validator.py         # 配置 schema 校验 + 模型 context-window 映射表
├── client.py            # 三种 LLM 客户端（Anthropic / OpenAI / OpenAICompat）+ 流式解析
├── agent.py             # ★ Agent 主循环（事件模型、工具往返、权限、压缩）
├── conversation.py      # ConversationManager（消息历史 + token 估算锚点）
├── serialization.py     # 消息 → anthropic/openai/responses 格式转换
├── prompts.py           # ★ 系统提示词拼接
├── remote.py            # --remote WebSocket 服务器 + 浏览器 UI 数据流
├── web_content.py       # 事件 → 浏览器渲染（markdown 等）
├── app.py               # ★ Textual TUI 应用
├── driver.py            # NoAltScreenDriver（保留 scrollback）
├── cache.py             # 简单缓存
├── teammate_tree.py     # TUI 里的 team 树控件
├── askuser_dialog.py / permission_dialog.py / plan_dialog.py / session_dialog.py
│                        # 各类 TUI 对话框
├── context/             # 上下文窗口预算、压缩、替换状态
│   └── manager.py
├── permissions/         # 权限：模式、危险命令、规则、路径沙箱、总编排
│   ├── checker.py dangerous.py modes.py rules.py sandbox.py
├── sandbox/             # OS 级沙箱：bubblewrap / macOS seatbelt
│   ├── bwrap.py seatbelt.py
├── mcp/                 # MCP 服务器管理与工具包装
│   ├── client.py manager.py tool_wrapper.py
├── memory/              # 记忆：自动记忆、固化、召回、会话、指令
│   ├── auto_memory.py consolidation.py recall.py session.py instructions.py
├── skills/              # Skill：解析、加载、执行、安装
│   ├── parser.py loader.py executor.py install.py builtins/
├── hooks/               # Hook：模型、引擎、事件、条件、执行器、加载
│   ├── models.py engine.py events.py conditions.py executors.py loader.py
├── agents/              # Subagent：加载、解析、任务管理、工具裁剪、trace、fork
│   ├── loader.py parser.py task_manager.py tool_filter.py trace.py fork.py notification.py builtins/
├── worktree/            # git worktree 任务隔离
│   ├── manager.py setup.py session.py changes.py cleanup.py integration.py models.py slug.py
├── teams/               # Teams 多智能体（lead/teammate + spawn 后端）
│   ├── manager.py coordinator.py models.py mailbox.py shared_task.py progress.py registry.py transcript.py
│   ├── backend_detect.py spawn_inprocess.py spawn_tmux.py spawn_iterm2.py
├── tools/               # 全部内置工具 + 注册表
│   ├── __init__.py base.py bash.py read_file.py write_file.py edit_file.py glob.py grep.py diff.py
│   ├── ask_user.py send_message.py exit_plan_mode.py enter_worktree.py exit_worktree.py
│   ├── task_*.py agent_tool.py team_create.py team_delete.py install_skill.py load_skill.py
│   ├── file_state_cache.py synthetic_output.py impl/tool_search.py
├── commands/            # 斜杠命令系统（/help 等）
│   ├── parser.py registry.py loader.py completion.py handlers/
└── filehistory/         # 文件历史快照
```

一个「核心闭合环」从 `__main__.py` 可以看清：`load_config()` → `create_client(provider)` → 组 `PermissionChecker` / `Agent` / 工具注册表（`create_default_registry`）→ `AgentLoader` 加载 subagent → `TeamManager` → `AgentTool` 注册进去 → `agent.run(conv)` 驱动事件循环。后文各章分别展开每一环。

---

## 3. 启动流程（三种模式）

`codeagent/__main__.py` 的 `main()` 按顺序做这些事：

1. `Path(".codeagent").mkdir(...)` 确保日志目录存在；`logging` 写到 `.codeagent/debug.log`（`filemode="w"`，每次启动覆盖）。
2. `argparse` 定义参数：`--mode`（权限模式，4 选 1）、`-p PROMPT`（非交互）、`--output-format text|stream-json`、`--remote`。
3. `load_config()` 读配置；失败抛 `ConfigError` → 打印到 stderr 并 `sys.exit(1)`。
4. `PermissionsMode` 由 `args.mode`（命令行优先）否则用 `config.permission_mode`。
5. `load_hooks(config.raw_hooks)` 加载钩子；有钩子则构造 `HookEngine`。
6. 分支：
   - `-p`：`asyncio.run(_run_prompt(...))`（见下）。
   - `--remote`：`RemoteServer(...).run()`（第 20 章）。
   - 默认：构造 `CodeAgentApp(...)`，`app.run()`（Textual TUI）。

`_run_prompt()`（`-p` 模式的完整装配）是理解全局对象关系的最佳范本，它的装配顺序值得背下来：

1. 取 `provider = config.providers[0]`，`client = create_client(provider)`；`await resolve_context_window(provider)`（尽力而为）。
2. 构造权限三件套：`DangerousCommandDetector` + `PathSandbox(work_dir)` + `RuleEngine`（用户级 `~/.codeagent/permissions.yaml`、项目级、本地级三层）→ 合入 `PermissionChecker`，mode 用 `permission_mode`。
3. `instructions = load_instructions(work_dir)`（读指令文件，见第 13 章）。
4. `registry = create_default_registry()`，再 `registry.register(ToolSearchTool(...))`。
5. 构造 `Agent(client, registry, protocol, work_dir, permission_checker, context_window, instructions_content, hook_engine)`。
6. 构造附属系统：`WorktreeManager`（配 `worktree_config`）、`TraceManager`、`TaskManager`、`AgentLoader`（`enable_verification_agent` 决定是否加验证 agent）→ `agent_loader.load_all()`；`TeamManager(worktree_manager, trace_manager)`。
7. 构造 `AgentTool`（subagent 工具）并 `registry.register`；再注册 `TeamCreateTool`、`TeamDeleteTool`。
8. 设置 `agent.notification_fn = drain_mailbox_only`（把 team 邮箱事件回流）。
9. `conv = ConversationManager(); conv.add_user_message(prompt)`，然后 `async for event in agent.run(conv)` 逐事件消费：文本累加、工具调用/结果记录、usage 汇总；`stream-json` 模式则每个事件打一行 NDJSON；`PermissionRequest` 在 `-p` 模式一律 `set_result(ALLOW)`（自动放行）。
10. 若有运行中的 team，轮询 `team_manager` / `task_manager`，收到通知就 `add_system_reminder` 并 `agent.run_to_completion(...)` 继续处理。

> 关键启示：`-p` 模式和 TUI 模式的**核心 Agent 装配几乎完全一致**，差别只在「事件如何被消费」（TUI 里渲染成界面，`-p` 里打印成文本 / NDJSON）。自建时可以把「Agent 装配」抽成一个函数复用。

---

## 4. 配置系统

### 4.1 查找顺序与分层合并（`config.py:load_config`）

`load_config()` 依序检查三个候选文件，**后加载的覆盖先加载的**（通过 `_merge_config` 逐字段合并）：

1. `~/.codeagent/config.yaml`（用户级）
2. `./.codeagent/config.yaml`（项目级）
3. `./.codeagent/config.local.yaml`（本地，通常 gitignore）

一个都没找到则抛 `ConfigError("No config file found...")`。

`_merge_config` 的合并语义（值得注意的细节）：
- `providers`：只要有就**整体替换**。
- `permission_mode`：覆盖值非 `"default"` 才替换（`default` 表示「没设」）。
- `mcp_servers`：按 `name` 去重合并（同名替换、异名追加）。
- `raw_hooks`：**追加**（不替换）。
- 布尔开关（`enable_fork` / `enable_verification_agent` / `enable_coordinator_mode`）与沙箱字段：只有覆盖层为 `True` 时才打开（即只能「开」，不会把下层的 `true` 关成 `false`）。
- `teammate_mode`：非空才替换。

### 4.2 配置结构（`ProviderConfig`）

`validate_config_structure` → `validate_providers` 要求每个 provider 至少含 `name` / `protocol` / `base_url` / `model` 四个字段。`protocol` 只允许 `anthropic | openai | openai-compat`。

`ProviderConfig` 关键字段与行为：

| 字段 | 默认 | 说明 |
|---|---|---|
| `name` / `protocol` / `base_url` / `model` | 必填 | — |
| `api_key` | `""` | 留空则 `resolve_api_key()` 回退读环境变量 `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` |
| `thinking` | `False` | 是否开启思考（Anthropic thinking / DeepSeek reasoning） |
| `context_window` | `0` | `0`=未设。`get_context_window()` 走 4 层回退 |
| `max_output_tokens` | `0` | `0`→ 按 `thinking` 给 64000 否则 8192 |

**context window 四层回退**（`get_context_window`）：
1. 配置显式 `context_window > 0` → 最高优先。
2. 运行时从 provider 拉取的 `_fetched_context_window`（仅 anthropic 协议会拉 `/v1/models/{model}`，见 `resolve_context_window`）。
3. 内置映射表 `MODEL_CONTEXT_WINDOWS`（`validator.py`）：按模型名子串匹配，如 `"1m"→1M`、`"gpt-4.1"→1M`、`"gpt-4o"→128K`、`"o1/o3/o4"→200K`、`"claude"→200K`。
4. 兜底：模型名含 `"claude"` → 200K，否则 128K。

`resolve_api_key()` 的映射：`anthropic→ANTHROPIC_API_KEY`，`openai`/`openai-compat`→`OPENAI_API_KEY`。`base_url` 里可写 `${VAR}`，`resolve_env_vars` 会替换环境变量。

### 4.3 其它配置段

- `mcp_servers`：每个含 `name` + 二选一 `command`（stdio，配 `args`/`env`）或 `url`（HTTP/SSE，配 `headers`/`transport`）。
- `hooks`：原始列表透传，由 hooks 模块校验（第 15 章）。
- `worktree`：`symlink_directories`（默认 `["node_modules",".venv","vendor"]`）、`stale_cleanup_interval`（3600s）、`stale_cutoff_hours`（24h）（第 17 章）。
- `sandbox`：`enabled` / `auto_allow` / `network_enabled`（默认全 `false`，第 11 章）。
- `permission_mode`：`default | acceptEdits | plan | bypassPermissions`（第 10 章）。
- `enable_fork` / `enable_verification_agent` / `enable_coordinator_mode` / `teammate_mode`：功能开关。

---

## 5. LLM 客户端与三种协议

`client.py` 用 ABC `LLMClient` 定义统一接口：`async def stream(conversation, system="", tools=None) -> AsyncIterator[StreamEvent]`，以及 `set_max_output_tokens()`。`create_client(config)` 按协议分发到三个具体类。

### 5.1 AnthropicClient（protocol=anthropic）

- 用官方 SDK `AsyncAnthropic(api_key, base_url)`，走 `self._client.messages.stream(...)`。
- 声明 `max_tokens`；`thinking: true` 时注入 `thinking={type:"enabled", budget_tokens:...}`，并对 `claude-opus-4-*` / `claude-sonnet-4-*` 且版本号 ≥6 的型号用 `budget_tokens=0`（自适应思考）。
- **Prompt cache**：`_mark_last_user_tail_for_cache` 给最后一条 user 消息尾块、`_mark_last_tool_for_cache` 给最后一个 tool 加 `cache_control={"type":"ephemeral"}`，system 也标记 cache，从而跨轮命中缓存（省 90% 输入费）。
- 解析 streaming 事件：`content_block_start/delta/stop`、`message_delta`、`message_stop`；`thinking_delta` 走 `ThinkingDelta`，`input_json_delta` 走 `ToolCallDelta`。
- **usage 兼容**：MiniMax 等 provider 在 `message_delta` 里才给 input_tokens/cache 读数（`message_start` 给 0），代码用 `getattr` 暂存并在 `message_stop` 后回填。
- 异常映射：认证/限流/网络/状态错误分别转成自有的 `AuthenticationError` / `RateLimitError`（解析 `retry-after`）/ `NetworkError` / `LLMError`。

### 5.2 OpenAIClient（protocol=openai）

- 走较新的 **Responses API**（`client.responses.create`，参数 `input=` 而非 `messages=`，system 用 `instructions=`）。
- 解析事件：`response.output_text.delta`、`response.reasoning_summary_text.delta/done`、`response.function_call_arguments.delta/done`、`response.output_item.added`（function_call / reasoning）、`response.completed`（含最终 usage）。
- `input_tokens` 里已含缓存 token，会减去 `cached_tokens` 保持可加性。

### 5.3 OpenAICompatClient（protocol=openai-compat）★（DeepSeek/任意兼容端点走这里）

- 走 **Chat Completions**（`client.chat.completions.create`），兼容任何 OpenAI 兼容 provider。
- `_convert_tools` 把注册表的 `{"type":"function","name":...,"parameters":...}`（Responses 风格）转成 Chat Completions 风格 `{"type":"function","function":{...}}`。
- 请求带 `stream_options={"include_usage": True}`，从而在流末尾拿到 usage。
- 解析：`delta.content` → 文本；`delta.reasoning_content`（DeepSeek/小米非标准字段）→ `ThinkingDelta`；`delta.tool_calls`（按 `tc.index` 累积多个并发调用）→ 工具调用；`finish_reason in ("tool_calls","stop")` 时结束工具调用块。
- 兼容 provider 可能用 `prompt_tokens_details.cached_tokens` 上报缓存命中，代码同样做减法。

### 5.4 协议选择建议（自建参考）

对 DeepSeek / Kimi / 通义 / vLLM / Ollama 等，一律用 `protocol: openai-compat` + `base_url`；官方 OpenAI 用 `openai`；Anthropic 官方或 Claude 兼容端点用 `anthropic`。

---

## 6. 会话管理与序列化

### 6.1 ConversationManager（`conversation.py`）

核心类 `ConversationManager`，持有一个 `history: list[Message]`。`Message` 由 `role`（user/assistant）+ `content` + 三个块列表组成：

- `tool_uses: list[ToolUseBlock]`（`tool_use_id / tool_name / arguments`）
- `tool_results: list[ToolResultBlock]`（`tool_use_id / content / is_error`）
- `thinking_blocks: list[ThinkingBlock]`（`thinking / signature`）

关键方法：

- `add_user_message` / `add_assistant_message`（可带 thinking/tool_uses）/ `add_system_reminder`（包成 `<system-reminder>...</system-reminder>`，角色仍是 user）。
- `add_tool_results_message`：把一轮工具结果作为一个 user Message 追加（`content=""`，只有 `tool_results`）。
- `inject_environment(context)`：只注入一次（`env_injected` 标志），插到历史**最前**。
- `inject_long_term_memory(instructions, memories)`：只注入一次（`ltm_injected`），内容是 `# codeagentMd`（指令，强调「OVERRIDE 默认行为」）+ `# autoMemory`（记忆）+ `# currentDate`（当天日期），包进 `<system-reminder>`，插到 `history[1]`（若 env 已注入）否则 `history[0]`。
- `replace_history(new)`：压缩后整体替换历史，并清空 `env_injected/ltm_injected` 与 token 锚点。
- `get_messages()`：返回历史副本。

### 6.2 Token 估算「锚点」机制（重要）

这是自建时很值得抄的设计——**混合策略**估 token：

- 每一次 API 响应用完，`agent` 调 `record_usage_anchor(input_tokens, output_tokens, cache_read, cache_creation)`，设 `baseline_tokens = input + cache_read + cache_creation + output`，并记 `anchor_count = len(history)`。
- `current_tokens()`：有锚点 → `baseline + estimate_tokens(锚点之后新增的消息)`；无锚点（冷启动/压缩重置后）→ 对全历史做**字符估算**。
- `estimate_tokens` 用常量 `_CHARS_PER_TOKEN = 3.5`（字符数/3.5），统计 content + thinking + tool_uses + tool_results 的字符。

> 要点：input 里缓存命中部分被各家 provider 从 `input_tokens` 里剔除了，所以要 `input + cache_read + cache_creation` 才等于真实 prompt 大小；再加上 output（assistant 回复已变历史）。这套锚点让「阈值检查」在等待 API 响应期间也能工作。

### 6.3 序列化（`serialization.py`）

把 `ConversationManager.get_messages()` 转成三种协议的请求格式：

- `build_anthropic_messages`：输出 `[{role, content:[{type:"text"/"thinking"/"tool_use"/"tool_result", ...}]}]`，注意 assistant 的 thinking 块、tool_use 块要还原 `id`，user 的 tool_result 要用 `tool_use_id` 对齐。
- `build_chat_completion_messages`：OpenAI 兼容字典（role/content，工具调用转成 `tool_calls` 数组、工具结果转成 `role:"tool"` + `tool_call_id`）。
- `build_openai_input`：Responses API 的 `input` 结构（含 function_call / function_call_output 等条目）。

三者共享同一份 `Message` 抽象，串行化差异被隔离在这一层——自建时这是「一个数据模型，多协议后端」的范本。

> 以下第 7–21 章由源码逐文件精读产出。
---

## 7. Agent 主循环（事件模型）

> 代码位于 `codeagent/agent.py`。运行期存在**两层事件**：底层 provider 无关的流式事件 `StreamEvent`（`codeagent/tools/base.py`，由 `client.py` 的 `LLMClient.stream()` 产出），上层对外暴露的 `AgentEvent`（`agent.py`，由 `Agent.run()` 产出、由 UI/session 层消费）。二者由 `StreamCollector` 转换。

### 7.1 AgentEvent 事件族（agent.py）

dataclass 定义：`StreamText(text)`、`ThinkingText(text)`、`RetryEvent(reason, wait=0.0)`、`ToolUseEvent(tool_name, tool_id, arguments)`、`ToolResultEvent(tool_id, tool_name, output, is_error, elapsed)`、`TurnComplete(turn)`、`LoopComplete(total_turns)`、`UsageEvent(input_tokens, output_tokens)`、`ErrorEvent(message)`、`CompactNotification(before_tokens, message, boundary)`、`HookEvent(hook_id, event, output, success)`、`PermissionRequest(tool_name, description, future: asyncio.Future)`。附加枚举 `PermissionResponse`（`ALLOW`/`DENY`/`ALLOW_ALWAYS`）。

### 7.2 StreamCollector：StreamEvent → AgentEvent

`StreamCollector` 持有一个聚合对象（`text`、`tool_calls: list[ToolCallComplete]`、`thinking_blocks`、`stop_reason`、`input_tokens/output_tokens/cache_read/cache_creation`）。`consume(stream)` 逐条消费底层流：

1. `TextDelta` → 累加并 `yield StreamText`（逐片透传）。
2. `ThinkingDelta` → `yield ThinkingText`。
3. `ThinkingComplete` → `append(ThinkingBlock)`（不 yield）。
4. `ToolCallStart`/`ToolCallDelta` → 忽略（只等完整调用）。
5. `ToolCallComplete` → append 并 `yield ToolUseEvent`。
6. `StreamEnd` → 填充 stop_reason 与用量，流结束。

### 7.3 Agent.run() 主循环

`run(conversation) -> AsyncIterator[AgentEvent]` 是流式对外入口。启动阶段：注入环境上下文、注入长期记忆、执行 `session_start` hook；随后 `while True` 每轮：

1. **迭代上限**：超过 `max_iterations` → `yield ErrorEvent` 并 break。
2. **轮次钩子与注入**：`turn_start` hook；团队邮箱 `_consume_mailbox`；`notification_fn()` 结果作 `add_system_reminder`；`pre_send` hook。
3. **构造 prompt 与工具**：`build_system_prompt(...)`；plan 模式写 plan reminder 并设 `permission_checker.plan_file_path`；deferred 工具提示；`registry.get_all_schemas(protocol)`。
4. **压缩分层**：Layer 1 先 `apply_tool_result_budget` 就地修改并 `append_replacement_records`；Layer 2 `auto_compact(...)`，返回 CompactEvent 则 `yield CompactNotification` 并重新注入 env/long-term-memory；返回 str 则 `yield ErrorEvent`。
5. **发起流式调用**：`client.stream(...)` → `collector.consume(...)`。对每个 `ToolUseEvent` 经 `permission_checker.check()`：`ask` 的进 `deferred_tool_calls`（流结束后串行执行）；其余 `executor.submit(...)` 在 LLM 输出期间并发执行。所有 event 原样 yield。
6. **用量结算**：`post_receive` hook；累加 input/output token；`yield UsageEvent`（**累计值**）。
7. **max_tokens 重试**：`stop_reason=="max_tokens"` 时先升级 `set_max_output_tokens(64000)` 并 `yield RetryEvent`；之后 3 次内追加"拆小任务"消息重试；非 max_tokens 回合归零计数。
8. **无工具调用即完成**：`add_assistant_message`；每 `MEMORY_EXTRACTION_INTERVAL(=1)` 回合 `ensure_future(_extract_memories)`；`turn_end`/`session_end` hook；`file_history.make_snapshot`；`yield LoopComplete` 并 break。
9. **有工具调用**：`add_assistant_message(..., tool_uses, thinking_blocks)`；`record_usage_anchor(...)`。
10. **收取流式结果**：`executor.collect_results()` 按提交顺序 gather，逐个 `_maybe_persist_or_truncate` 组装 `ToolResultBlock` 并 `yield ToolResultEvent`；累计 `consecutive_unknown`。
11. **延迟权限工具串行执行**：逐个 `_execute_tool`，若 yield `PermissionRequest` 则交还调用方，否则收到 `(result, elapsed, is_unknown)`。
12. **停止条件**：连续 3 次未知工具 → ErrorEvent；本轮回调 `ExitPlanMode` → TurnComplete+LoopComplete；否则 `add_tool_results_message` → `turn_end` hook → `yield TurnComplete` 继续。

### 7.4 工具调用往返流程

- **并发安全批处理** `partition_tool_calls`：按 `tool.is_concurrency_safe and registry.is_enabled` 把相邻安全调用归入 `ToolBatch(concurrent=True)`，不安全的单开一批。
- **流式执行器** `StreamingExecutor.submit`：`asyncio.create_task` 立即启动并记录顺序；`collect_results` 按序 `gather(return_exceptions=True)`，异常包成 `ToolResult(is_error=True)`。
- **直连执行** `_execute_single_tool_direct`：未知工具→`is_unknown`；未启用→disabled；`deny`→权限错误；通过后 `params_model.model_validate(arguments)` 再 `await tool.execute(params)`；成功后 `_snapshot_for_recovery`。
- **可交互执行** `_execute_tool`：`decision.effect=="ask"` 处阻塞——`loop.create_future()`，`yield PermissionRequest(...)` 交还调用方，`await future`。`DENY`→拒绝；`ALLOW_ALWAYS`→`append_local_rule` 持久化 + `add_session_allow`；`ALLOW`→继续。

### 7.5 run() 与 run_to_completion() 的区别

`run_to_completion(task, conversation=None, event_callback=None) -> str` 是非流式/最终文本入口：

1. 返回 `str`（最后一段 assistant 文本）而非事件迭代器。
2. 事件经 `event_callback(dict)` 上报字典（`usage`/`stream_text`/`tool_use`）。
3. 工具串行执行，无 StreamingExecutor；用 `_execute_tool_noninteractive`——`ask` 且非 BYPASS 直接返回 "non-interactive agent cannot prompt user"。
4. 不产出 RetryEvent/ToolResultEvent/TurnComplete/LoopComplete/CompactNotification/PermissionRequest 等 UI 事件。
5. 无 hook post_receive、无 deferred_tool_calls、无 consecutive_unknown 熔断；完成条件是 `not response.tool_calls`。

### 7.6 停止条件汇总

无 tool_calls（→LoopComplete）、ExitPlanMode 被调（→TurnComplete+LoopComplete）、连续 ≥3 未知工具（→ErrorEvent）、超过 max_iterations（→ErrorEvent）。底层 `StopReason` 由 `StreamEnd.stop_reason` 携带（Anthropic 用 `final.stop_reason`，OpenAI 系固定 `"end_turn"`）。

---

## 8. 工具系统

### 8.1 Tool 基类与参数声明机制（`tools/base.py`）

```python
SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".tox", ".mypy_cache"}
MAX_OUTPUT_CHARS = 10000
ToolCategory = Literal["read", "write", "command"]
```

`ToolResult`（`output: str`，`is_error: bool=False`）是 `execute()` 的返回类型。

`Tool(ABC)` 抽象基类：类属性 `name` / `description` / `params_model: type[BaseModel]` / `category="read"` / `is_concurrency_safe=False` / `is_system_tool=False` / `should_defer=False`。

- `is_read_only` = `category == "read"`。
- `get_schema()` = `params_model.model_json_schema()` 去掉 `title` 后包装成 `{"name", "description", "input_schema"}`。
- `async execute(params: BaseModel) -> ToolResult` 抽象方法。

**关键机制**：工具参数 schema 完全由 Pydantic v2 模型字段驱动（`Field`/类型注解/默认值）。`is_concurrency_safe` 标记可并发（只读工具为 True）；`should_defer` 标记延迟加载（默认不进模型可见工具列表，需 `ToolSearch` 发现）。

`base.py` 还定义了流事件 dataclass：`TextDelta` / `ToolCallStart` / `ToolCallDelta` / `ToolCallComplete` / `ThinkingDelta` / `ThinkingComplete` / `StreamEnd`（`StreamEnd` 含 stop_reason/input/output/cache_read/cache_creation），组成 `StreamEvent` 联合类型。

### 8.2 逐工具说明

**Bash**（`bash.py`，category=command）：参数 `command: str`、`timeout: int=120`（上限 600）。超时用 `asyncio.wait_for(proc.communicate(), timeout)`；`create_subprocess_shell(..., stderr=STDOUT)` 合并流；OS 沙箱注入时先 `sandbox.wrap()`。退出码语义：`_COMMAND_ERROR_THRESHOLDS` 对 `grep/egrep/fgrep/rg/diff/find/test/[` 设阈值 2（exit 1 不算错），`_extract_last_command_name` 取管道末段+跳过 `VAR=VALUE` 前缀，生成 `_exit_code_hint`（如 `"Exit code 1 (no matches found)"`）。注意非零退出码只追加提示、`is_error` 仍为 False（仅超时/异常才 True）；空输出→`"(no output)"`。

**ReadFile**（category=read，is_concurrency_safe=True）：参数 `file_path`、`offset=0`（0-based）、`limit=2000`。走 `FileCache` 命中/回填；`FileStateCache.record()` 记录"已读"；加行号 `f"{i+offset+1}\t{line}"`（1-based）。

**WriteFile**（write）：参数 `file_path`、`content`。描述强制"覆盖前必须先 ReadFile"；`file_history.track_edit`；存在文件则 `FileStateCache.check()` 双重门禁；`parent.mkdir(parents=True)`；`write_text`；`FileCache.invalidate` + `FileStateCache.update`。

**EditFile**（write）：参数 `file_path`、`old_string`（须唯一）、`new_string`。`content.count(old_string)`：0→"not found"、>1→"must be unique"、唯一则 `replace(...,1)`。回写后 `build_diff` 生成结构化 diff，输出 `"Updated {path} with N addition(s) and M removal(s)"` + 完整 diff。

**Glob**（read，concurrency_safe）：参数 `pattern`、`path="."`。`pathlib.glob` + 过滤 `SKIP_DIRS`；按 mtime 倒序、转相对路径。

**Grep**（read，concurrency_safe）：参数 `pattern`（正则）、`path="."`、`include=""`。`re.compile` 异常报 invalid regex；`include` 自动补 `**/` 前缀；`enumerate(splitlines(), 1)` 行号；输出 `file:line:content`；读失败静默跳过。

**build_diff**（`diff.py`，纯函数非 Tool）：`DiffResult(text, additions, removals)`；`_CONTEXT_LINES=3`、`_MAX_DIFF_LINES=200`；两端找公共前缀/后缀行直接切出增删（非 Myers），前后各 3 行上下文，超 200 行截断。

**AskUserQuestion**（read，is_system_tool，should_defer=True）：参数 `questions: list[QuestionItem{type,name,message,options}]`（type: text/radio/select/checkbox）。`execute` 构造 `AskUserEvent(questions, future)` 存 `_pending_event`，`await asyncio.wait_for(future, 300)` 挂起；TUI 弹窗回填 future；超时→"5 分钟未响应"。

**SendMessage**（command）：参数 `to`（名字/agent id/`"*"` 广播）、`message`、`summary`、`message_type=text`、`metadata`。`VALID_MESSAGE_TYPES={text,shutdown_request,shutdown_response}`；text 必须给 summary（5-10 词）。走 `mailbox.write/broadcast`，发完 `_wake_pane` 唤醒 pane。

**ExitPlanMode**（无参数）：断言处于 plan mode 且计划文件已写，返回"提交计划、结束本轮"指引。

**EnterWorktree**（command，should_defer）：参数 `name`（可选，`/` 分段，≤64，缺省 `wt-{token_hex(4)}`）。`validate_slug` → `manager.create` + `manager.enter`。

**ExitWorktree**（command，should_defer）：参数 `action`（keep/remove）、`discard_changes`。有未提交改动且未 discard 时拒绝。

**任务四件套**（依赖 `TeamManager.get_task_store`）：`TaskCreate{title,description,assignee,blocks,blocked_by}`、`TaskGet{task_id}`、`TaskList{status,assignee}`（图标 ○/◐/●/✕）、`TaskUpdate{task_id,status,assignee,description,add_blocks,add_blocked_by}`（VALID_STATUSES 校验）。

**InstallSkill**（write，is_system_tool）：参数 `url`。`parse_skill_url` → `install_skill` → `loader.reload()` → `_on_installed` 回调。

**LoadSkill**（is_system_tool）：参数 `name`。`loader.get(name)` → `agent.activate_skill(name, prompt_body)` → 返回 `"# Skill: {name}\n\n<body>"`。

### 8.3 工具注册表（`create_default_registry`）

`ToolRegistry`：有序 dict `_tools[name]=Tool`（注册顺序即 schema 顺序）+ `_disabled` + `_discovered`。方法：`register/get/list_tools/is_enabled/enable/disable/enable_all/mark_discovered/is_discovered/get_deferred_tool_names/search_deferred/find_deferred_by_names/get_all_schemas`。

- `get_all_schemas(protocol)`：跳过禁用、跳过 `should_defer` 且未发现者；`openai/openai-compat` 转成 `{"type":"function","function":...}` 结构，否则 Anthropic 三段结构。
- `search_deferred`:query 命中 name +10、description +5、拆词命中 name +3 / description +1，按分取前 max_results。

`create_default_registry` 只注册 6 个基础工具（一个共享 `FileStateCache` 注入 ReadFile/WriteFile/EditFile）：

| 顺序 | 工具 | category | 注入依赖 |
|---|---|---|---|
| 1 | ReadFile | read | file_cache, file_state_cache |
| 2 | WriteFile | write | file_cache, file_history, file_state_cache |
| 3 | EditFile | write | file_cache, file_history, file_state_cache |
| 4 | Bash | command | —（可注入 work_dir/sandbox） |
| 5 | Glob | read | — |
| 6 | Grep | read | — |

其余工具由上层装配：`ToolSearch/AskUserQuestion/ExitPlanMode/LoadSkill/InstallSkill/EnterWorktree/ExitWorktree/SyntheticOutput` 在 app.py/__main__.py/remote.py `register`；`Agent/TeamCreate/TeamDelete` 由 app.py/__main__.py 创建注册；`TaskCreate/Get/List/Update` + `SendMessage` 由 `tool_filter.build_teammate_tools()` 在孵化队友时实例化进队友专属注册表；MCP 工具由 `mcp/manager.py` 动态注册。

### 8.4 agent_tool.py（subagent 核心，约 680 行）

参数 `prompt`、`description`、`subagent_type`、`model`、`run_in_background=False`、`name`、`isolation`、`team_name`（传入则孵化为长期队友，否则一次性阻塞子 agent）。

常量：`PERMISSION_MODE_MAP`（default→DEFAULT / acceptEdits→ACCEPT_EDITS / bypassPermissions→BYPASS）、`FORK_QUERY_SOURCE="agent:builtin:fork"`、`TEAMMATE_ADDENDUM`（队友专属指令：必须用 SendMessage、在隔离 worktree 用相对路径）。

`execute()` 三分支：`team_name` → `_execute_as_teammate`；定义 `isolation=="worktree"` → `_execute_with_worktree`；否则普通 subagent/fork。

**普通 subagent/fork**：定义获取（有 subagent_type 用 `agent_loader.get`；无则 fork——校验 enable_fork、禁止二次 fork、`build_forked_messages`、构造 `AgentDef(agent_type="fork", permission_mode="bypassPermissions")`）；`_select_llm`；后台判定（fork 强制后台）；工具集（fork 用 `clone_registry_for_fork` 并把 Agent 工具标 `FORK_QUERY_SOURCE`，非 fork 用 `resolve_agent_tools`）；`PermissionChecker(PathSandbox(parent.work_dir), mode=pm)`；创建子 Agent（复制 protocol/work_dir/context_window/hook_engine）；fork 继承 `clone_replacement_state`（保 prompt cache 前缀一致）；`trace_manager.create/update/complete`；后台走 `task_manager.launch` 返回 task_id，前台 `await run_to_completion`。

**`_execute_as_teammate`**：`get_team` 不存在报错；命名去重（base_name 冲突加 -2/-3）；定义/fork；`worktree_manager.create(f"team-{team}/{mate}", "HEAD")`；`_select_llm`；`detect_backend`；`trace_manager.create` 拿 agent_id；`build_teammate_tools`（含 Task 四件套 + SendMessage）；`PermissionChecker(PathSandbox(wt.path), BYPASS)`；`AgentNameRegistry.register` + `TeammateInfo` + `register_member`；按后端 spawn（tmux/iterm2 → `_spawn_pane_teammate`，否则 `task_manager.launch`）。

**`_select_llm` / `_create_client_for_model`**：model 覆盖或定义 model（`"inherit"` 则继承父）；快捷名映射 haiku/sonnet/opus 到具体 claude 型号，用父 provider 的 protocol/base_url/api_key 构造新 client。

**verification agent**：内置 `verification.md`（background:true，disallowedTools=[Agent,EditFile,WriteFile,NotebookEdit]，只读，必须实际跑 build/test/lint，输出 `VERDICT: PASS/FAIL/PARTIAL`）；由 `AgentLoader(enable_verification=config.enable_verification_agent)` 控制是否加载；通过 `Agent(subagent_type="Verification")` 唤起。

### 8.5 team_create / team_delete 在工具层触发 team

**TeamCreate**（参数 `team_name`、`description`）：`detect_backend` → `create_team(lead_agent_id=parent.agent_id)` → 若 `enable_coordinator_mode`：保存 `_full_registry` 快照（仅在"未限制→限制"切换点保存一次）→ `apply_coordinator_filter` 收窄工具 → `coordinator_mode=True`。返回 Backend/Config 路径 + 提示 `Agent(team_name=...)` 孵化队友。

**TeamDelete**（参数 `team_name`）：`delete_team`；若 coordinator_mode 且删完所有团队，恢复 `_full_registry` + `coordinator_mode=False`。

### 8.6 tool_search —— 动态工具检索

`ToolSearch`（`should_defer=False` 自身永可见）：参数 `query`、`max_results=5`。`query` 以 `select:` 开头则按逗号拆名精确加载（`find_deferred_by_names`）；否则关键字打分检索（`search_deferred`）。有结果则逐个 `registry.mark_discovered(name)`——把该延迟工具从"延迟池"提升进下一轮 `get_all_schemas()` 可见集合。当前 `should_defer=True` 的工具：`AskUserQuestion`、`EnterWorktree`、`ExitWorktree`（以及 MCP 包装工具）。

### 8.7 file_state_cache 与 synthetic_output

**FileStateCache（读后编辑门禁）**：`dict[绝对路径 → (content, mtime_ns)]`。`record`（ReadFile 成功后写入）；`check` 双重门禁——Gate1 未读→"先读再改"、Gate2 `st_mtime_ns` 不一致→"文件已改、重读再改"（文件被删则放行）；`update`（编辑成功后回读刷新）。由 `create_default_registry` 注入 ReadFile/WriteFile/EditFile 三者共享，强制"先读后写/改"闭环。

**SyntheticOutput（结构化输出）**：参数 `output: dict|list|str`；`name="SyntheticOutput"`、is_system_tool、is_concurrency_safe。可选注入 `json_schema` 校验（按 type/required 断言）；输出 `json.dumps(indent=2)`。是后台子 agent 与 coordinator 模式下收口结构化结果的通道（白名单 `ASYNC_AGENT_ALLOWED_TOOLS`/`COORDINATOR_MODE_ALLOWED_TOOLS` 均含它）。

---

## 9. 系统提示词与上下文管理

覆盖 `context/manager.py`、`prompts.py`、`cache.py`、`filehistory/history.py`。

### 9.1 上下文管理（context/manager.py）

两层职责：Layer 1 大型工具结果落盘（`apply_tool_result_budget`），Layer 2 全对话摘要 `auto_compact`。

核心常量：`SINGLE_RESULT_CHAR_LIMIT=50_000`、`AGGREGATE_CHAR_LIMIT=200_000`、`PREVIEW_CHARS=2_000`、`SUMMARY_OUTPUT_RESERVE=20_000`、`AUTO_COMPACT_SAFETY_MARGIN=13_000`、`MANUAL_COMPACT_SAFETY_MARGIN=3_000`、`KEEP_RECENT_TOKENS=10_000`、`MIN_KEEP_MESSAGES=5`、`KEEP_MAX_TOKENS=40_000`、`MIN_SUMMARIZE_PREFIX_TOKENS=2_000`、`SESSION_SUBDIR=".codeagent/session/tool-results"`。

**上下文窗口预算**：本模块没有显式的"输入/输出成比例切分"；唯一输出预留是 `SUMMARY_OUTPUT_RESERVE=20_000`（供摘要 LLM 调用）。`compute_compact_threshold(context_window, manual) = context_window − 20_000 − margin`（auto margin 13_000、manual 3_000）。`should_auto_compact`：`last_input_tokens >= 软阈值`。

token 计数来自 `ConversationManager.current_tokens()` + `UsageAnchor`：`baseline_tokens = input + cache_read + cache_creation + output`（各分量相加=真实 prompt 大小），`anchor_count` 记录当时 history 长度；有锚点 = `baseline + estimate_tokens(history[anchor_count:])`，无锚点退化为全量字符估算（`_CHARS_PER_TOKEN=3.5`）。

**auto_compact 触发与算法**：
1. 取 `current_tokens()`；manual 跳过阈值检查；低于软阈值 return None；≥硬阈值强制压缩；软硬之间走熔断器 `CompactCircuitBreaker(max_failures=3)`。
2. `keep_start = _compute_keep_start_index()`；前缀 `to_summarize = history[:keep_start]`，尾部 `keep_tail` 保留原文。
3. 前缀 <2000 token 则不压；`build_messages()` 序列化前缀；构造摘要会话（`SUMMARY_PROMPT` TEXT-ONLY 禁工具，要求 `<analysis>` + `<summary>`）。
4. 重试最多 3 次：遇 "prompt too long" 用 `_group_messages_by_turn` 按轮切分、丢最前 1/5 轮重试；3 次耗尽 `record_failure` 返回失败。
5. `extract_summary` 取 `<summary>` 文本；`build_recovery_attachment` + `build_compact_messages` + keep_tail 重建；`replace_history`（清锚点/env/ltm 标志）；`cleanup_tool_results`；`record_success` 返回 `CompactEvent`，由 session 层持久化为 compact_boundary。

**Layer 1 `apply_tool_result_budget`**：对每个 tool_result 四路分派；Pass1 单条 >50K 字符落盘（`_is_spill_readback` 防对落盘文件 ReadFile 回读再落盘；`persist_tool_result` 用 `os.open(O_EXCL)` 写 `{id}.txt`；`make_persisted_preview` 生成 `<persisted-output>` 占位）；Pass2 单条消息聚合 >200K 按长度降序逐个落盘至 ≤200K。

**ContentReplacementState（稳定 tool_result 以命中 prompt cache）**：`seen_ids(set)` + `replacements(dict id→稳定替换文本)`。价值：client 在 system/tools 尾部 + 最后一条 user 消息末打 `cache_control:ephemeral`，Anthropic 逐字节比对；replacements 记住"该 id 已替换为这段文本"，下轮原样应用保持稳定，命中 token 只付 10%。持久化到 `replacement_records.jsonl`，resume 时 `load_replacement_records` + `reconstruct_replacement_state`（收集当前 tool_use_id 合并）。

**LRU**：全库无任何 LRU。近似"近期保留"三处：压缩保留尾部原文、`RecoveryState.snapshot_files` 按时间倒序、filehistory `MAX_SNAPSHOTS=100` 滑窗。

**消息历史截断**：`_compute_keep_start_index` 从尾向前累加 token，`kept_tokens>=10_000` 或 `kept_count>=5` 先满足即停，突破 40_000 也停；`_align_keep_start_to_tool_pair` 回退到配对 assistant 防拆散 tool_use/tool_result。

### 9.2 系统提示词（prompts.py）

`PromptSection(name, priority, content)`；`PromptBuilder.add/build` 按 priority 升序 sort + `"\n\n"` join。

`build_system_prompt` 顺序：
- 静态 Section（硬编码常量）：Identity(p0)、System(p10，权限语义/hook/注入预警)、DoingTasks(p20)、ExecutingActions(p30，破坏性操作需确认清单)、UsingTools(p40，专用工具优先/并行/Agent/Team/ToolSearch)、ToneStyle(p50)、TextOutput(p60)。
- 运行时动态：`environment_section`(p70) ← `detect_environment`（读 SHELL、`git -C rev-parse --is-inside-work-tree` + `--abbrev-ref HEAD` subprocess timeout=5、platform.system/machine、日期）；`CustomInstructions`(p80)、`Skills`(p90)、`Memory`(p95) —— 仅非空加入。
- `hook_prompts` 在 build() 后字符串追加 " # Hook Injected Context "（无 priority）。
- `coordinator_mode=True` 直接 return `get_coordinator_system_prompt(agent_catalog)`。

工具 schema 不在 prompts.py，由调用方作 `tools` 参数传（`registry.get_all_schemas`）。`build_environment_context` 是另一注入点（注入 history 第一条 user）。Plan 模式有 `_PLAN_MODE_FULL_REMINDER`（5 阶段）/SPARSE/EXIT/REENTRY，`build_plan_mode_reminder` 每 5 轮补一次全量。

### 9.3 cache.py

`FileCache`：`dict[path→content]` + 锁；get/put/invalidate/clear；无 TTL/上限/LRU，仅显式失效。注入 ReadFile/WriteFile/EditFile：ReadFile 命中则用、miss 读盘 put；Write/Edit 写后 invalidate。

### 9.4 filehistory（文件历史/撤销）

目录 `{base}/.codeagent/file-history/{session_id}`。`track_edit(path)` 在写盘前读旧字节备份为 `sha256(path)[:16]@v{version}`（备份改动前内容）；`make_snapshot(msg_index, user_text)` 每轮用户消息后建检查点，超 100 截尾。`rewind(snapshot_index)` 逐 backup 与当前字节比对，不同才写回/重建/删除，返回 changed 列表。`/rewind` 三选项：1 恢复文件+截断对话、2 只截断对话、3 只恢复文件。

### 9.5 context window 四层 fallback（在 config.py/client.py/validator.py）

`ProviderConfig.get_context_window()`：显式 `context_window>0` → `_fetched_context_window`（anthropic 协议拉 `/v1/models/{model}` 的 max_input_tokens，超时 3s）→ `validator.lookup_model_context_window` 子串映射表 → 默认 claude 200K / 其余 128K。解析结果喂 `compute_compact_threshold`。

---

## 10. 权限系统（`permissions/`）

对外出口 `permissions/__init__.py` 导出：`Decision`、`PermissionChecker`、`DangerousCommandDetector`、`DecisionEffect`、`PermissionMode`、`mode_decide`、`Rule`、`RuleEngine`、`extract_content`、`parse_rule`、`PathSandbox`。

### 10.1 权限模式（`modes.py`）

`PermissionMode(str, Enum)` 四个成员；`DecisionEffect = Literal["allow","deny","ask"]` 贯穿全系统。模块级 `_MODE_MATRIX: dict[PermissionMode, dict[ToolCategory, DecisionEffect]]` 查表：

| 模式 | read | write | command |
|---|---|---|---|
| `default` | allow | ask | ask |
| `acceptEdits` | allow | allow | ask |
| `plan` | allow | ask | ask |
| `bypassPermissions` | allow | allow | allow |

`mode_decide(mode, category)` 直接查表。`plan` 额外在 `check()` Layer 0 只允许计划编辑类工具。`Agent.set_permission_mode()` 同步更新 `permission_checker.mode`。

### 10.2 危险命令检测（`dangerous.py`）

**黑名单 `_DANGEROUS_PATTERNS`**（8 条正则 + 中文原因）：`rm -rf /`、`mkfs.`、`dd if= of=/dev/`、`chmod -R 777 /`、fork bomb `:(){:|:&};:`、`curl|sh`、`wget|sh`、`> /dev/sd`。

**白名单 `_SAFE_COMMANDS`**：只读命令集合（ls/pwd/echo/cat/head/tail/wc/find/which/uname/df/du/file/stat/sort/uniq/grep/diff 等）及复合前缀（`git status/log/diff/show/branch/...`、`go version`、`node -v`、`pip list` 等）。

`is_safe_command(command)`：strip 后空则 False；含 `|` `;` `&&` `>` `$(` 反引号则 False；精确等于或 `startswith(safe + " ")` 则 True。`DangerousCommandDetector.detect()` 顺序 match 返回 `(is_dangerous, reason)`；仅对 `category=="command"` 生效，命中即 deny。

### 10.3 规则引擎（`rules.py`）

规则格式（YAML）：`- rule: "Bash(git push*)"` + `effect: ask|deny|allow`。`parse_rule` 用 `^(\w+)\((.+)\)$` 解析出 tool_name + pattern（fnmatch 通配）。`Rule.matches()` = 工具名相等且 `fnmatch(content, pattern)`。

`extract_content(tool_name, arguments)`：`_CONTENT_FIELDS` 映射（Bash→command、ReadFile/WriteFile/EditFile→file_path、Glob/Grep→pattern）。

`RuleEngine(user_rules_path, project_rules_path, local_rules_path)`：三层 `[user, project, local]`，`evaluate` 依序遍历，层内 `reversed`（越靠后越优先），命中即短路。**优先级：用户级 > 项目级 > 本地级**。`append_local_rule` 读→append→`yaml.dump` 写回本地文件（"总是允许"落点）。

### 10.4 路径沙箱（`permissions/sandbox.py`）

`PathSandbox(project_root, extra_allowed=None, deny_write=None)`：`_allowed_roots=[root, tempdir]` + extra_allowed；`_deny_write` 默认 `.codeagent/config.yaml`、`.codeagent/permissions.local.yaml`、`.codeagent/skills/`。`check(path)`：expanduser→绝对路径→`resolve(strict=True)` 解析符号链接（不存在的向上找最近祖先投影）→ **禁写优先** → 遍历 allowed_roots 判断 → 否则 `(False, "超出沙箱范围")`。在 `check()` Layer 2 仅 read/write 生效。

### 10.5 PermissionChecker 总编排（`checker.py`）

`Decision(effect, reason)`；`check(tool, arguments)` 分层短路：

- **Layer 0 Plan 例外**：PLAN 模式且 tool ∈ `{Agent, ToolSearch, AskUserQuestion, ExitPlanMode}` → allow；WriteFile/EditFile 且 `_is_plan_file` → allow。
- **Layer 1 安全只读命令**：`is_safe_command` → allow。
- **Layer 1b 危险黑名单**：`detect` 命中 → deny。
- **Layer 1c OS 沙箱自动放行**：`sandbox_enabled` 且 command 时，拆子命令逐条 `rule_engine.evaluate`。
- **Layer 2 路径沙箱**：read/write 且 content，`sandbox.check` 失败（且非 BYPASS）→ ask。
- **Layer 3 规则引擎**：allow/deny 对应返回。
- **Layer 4b 会话级放行**：`_session_allowed`（内存，`"Tool:pattern"`）。
- **Layer 4 模式兜底**：`mode_decide`。
- **Layer 5 HITL**：默认 ask。

### 10.6 权限对话框（`permission_dialog.py`）

`InlinePermissionWidget`：三选项 Yes(ALLOW) / "don't ask again for this pattern"(ALLOW_ALWAYS) / No(DENY)，方向键+回车+ESC。挂接 `app.py`：`_handle_permission_request` mount + 禁用输入框；`on_inline_permission_widget_responded` `req.future.set_result` 唤醒。`ALLOW_ALWAYS` 时 `pattern = content[:60]+"*"`（超长）否则 `content+"*"`，`append_local_rule` 持久化 + `add_session_allow` 内存立即生效。

---

## 11. 沙箱（OS 级隔离，`sandbox/`）

`create_sandbox()`：Darwin→`SeatbeltSandbox`、Linux→`BwrapSandbox`、其他→None。

**Linux bwrap（`bwrap.py`）**：`wrap` 拼 `bwrap --unshare-user --unshare-pid --ro-bind / /`；每个 allow_write 加 `--bind <p> <p>`；每个 deny_write 加 `--ro-bind`（后声明只读覆盖）；`not network_enabled` 加 `--unshare-net`；加 `--proc /proc --dev /dev -- bash -c <command>`。`available()` = `shutil.which("bwrap")`。

**macOS Seatbelt（`seatbelt.py`）**：`_build_profile` 生成 SBPL `(version 1)(deny default)` + 放行 process-exec/fork/sysctl/file-read*（subpath "/"）+ 逐 allow_write `(allow file-write*)` + 逐 deny_write `(deny file-write* ...)`（目录 subpath、文件 literal）+ network 开关。`wrap` 返回 `/usr/bin/sandbox-exec -p <profile> bash -c <command>`。

**配置项接线**：`SandboxAppConfig(enabled, auto_allow, network_enabled)`（校验默认全 False，多层合并只开不关）。`app.py _select_provider`：`sandbox_auto_allow = enabled and auto_allow`（两者皆真才置 `checker.sandbox_enabled`）；enabled 时 `create_sandbox()` + 构造 `SandboxConfig(allow_write=[work_dir,"/tmp"], deny_write=[config.yaml, permissions.local.yaml], ...)` 挂到 Bash。`bash.py execute`：sandbox available 则 `sandbox.wrap`。`/sandbox` 命令：on-auto（沙箱+自动放行）、on（沙箱+常规确认）、off（关闭）。

> 注意：OS 沙箱 `deny_write` 仅 config.yaml + permissions.local.yaml 两项，而 `PathSandbox._DEFAULT_DENY_WRITE` 额外含 `.codeagent/skills/`，两处禁写范围有差异。

---

## 12. MCP 集成（`mcp/`）

### 12.1 配置两种形态

`MCPServerConfig(name, command=None, args=[], url=None, headers={}, env={})`，`is_stdio = command is not None`。形态 A（stdio 本地子进程）设 `command`；形态 B（远程 URL）设 `url`，用 `mcp.client.streamable_http` 的 Streamable HTTP 传输（非 SSE）。`resolve_env_vars` 替换 `${VAR}`；`build_child_env` 复制 PATH 后展开声明式 env。

### 12.2 MCPManager（`manager.py`）

`_configs` + `_clients` 两个 dict。`connect_all()` 返回 `ConnectResult(tools, servers, errors)`，对每个配置 `MCPClient.connect` → 建 `ServerInfo` → `list_tools` 逐个包 `MCPToolWrapper`，异常捕获进 errors 不中断启动。`register_all_tools(registry)` 把工具注册进主注册表。`get_client` 惰性（不存在新建、掉线重建）。`shutdown` 逐个 close。

### 12.3 MCPClient（`client.py`）

`connect()` 用 `AsyncExitStack` 管理资源，按 `is_stdio` 选 `stdio_client` 或 `streamable_http_client`，`ClientSession(read, write)` + `session.initialize()` 协商。`list_tools`/`call_tool` 透传。stdio 的 stderr 重定向到 devnull；HTTP 的 headers 逐个展开 `${VAR}`。`instructions` 来自 `InitializeResult`。

### 12.4 MCPToolWrapper（`tool_wrapper.py`）

继承 `Tool`：`name = f"mcp_{server}_{tool}"`（单下划线）、`category="command"`、`is_concurrency_safe=False`、**`should_defer=True`**（MCP 工具默认延迟，等 ToolSearch 发现）。`_build_params_model` 用 `pydantic.create_model` 从 JSON Schema 动态生成参数模型（required 用 `(py_type, ...)`，非 required 用 `(py_type|None, None)`；类型映射 string→str、integer→int、number→float、boolean→bool、object→dict、array→list）。`execute`：掉线先重连 → `call_tool` → `_extract_text` 把 TextContent/ImageContent/EmbeddedResource 拼纯文本 → `ToolResult(is_error=result.isError)`。

> 实现差异：包装器命名单下划线 `mcp_{server}_{tool}`，而 `/mcp` 状态命令与 MCP 指令回退逻辑用双下划线 `mcp__{server}__` 前缀过滤——回退路径可能匹配不到工具（正常由服务器 instructions 覆盖）。

---

## 13. 记忆系统（`memory/`）

### 13.1 自动记忆（`auto_memory.py`）

存储格式：独立 `.md` + YAML frontmatter + `MEMORY.md` 索引。路径 `get_auto_mem_path`→`<root>/.codeagent/memory/`（可 `CODEAGENT_REMOTE_MEMORY_DIR` 覆盖）、`get_user_auto_mem_path`→`~/.codeagent/memory/`。类型 `VALID_TYPES={user,feedback,project,reference}`，user/feedback→用户级、project/reference→项目级。

`MemoryFile(path,name,description,type)`；`parse_frontmatter` 逐行找冒号（只认 name/description/type）；`truncate_entrypoint_content` 超 200 行/25KB 截断。

`build_memory_prompt`：行为指令（两位置路由、先选 type 再写、两步保存、索引行 ≤150 字符、去重）+ 各目录 `MEMORY.md` 索引。`MemoryManager.extract()` 9 步：取增量历史 → 转 `[user]:`/`[assistant]:` → 生成去重段 → 构造提取提示（要求 MEMORY_NAME/TYPE/DESC/BODY 块，无可存写 NONE）→ 裸 LLM 流式调用 → 更新游标 → 切块提取 → 路由目录写文件（实际 frontmatter 为 `metadata.type` 嵌套，但 parse 逐行匹配仍能识别）→ 更新 `MEMORY.md` 索引 + `- [name](name.md) — desc`。

触发时机在 `agent.py`：`MEMORY_EXTRACTION_INTERVAL=1`，每完成一轮对话 `ensure_future(_extract_memories)`（`_extracting` 锁 + `_pending_extraction` 合并防并发）。注入：`inject_long_term_memory(instructions, memory_content)` 包 `# autoMemory` + `# codeagentMd` + `# currentDate` 进 `<system-reminder>` 插 history[1]，compact 后重注入。

### 13.2 记忆固化（`consolidation.py`）

门控 `maybe_run()`：时间门（距上次 <24h 跳过）→ 扫描节流（<10min）→ 会话门（`list_sessions_since` 会话数 <5 跳过）→ 文件锁 `.consolidate-lock`（mtime<1h 且持有进程存活则拒绝）。通过则后台 `_run` fork 一个子 Agent（注册 Read/Write/Edit/Glob/Grep/Bash，`PermissionChecker(mode="bypass")`，max_iterations=15）执行四阶段 prompt（Orient→Gather→Consolidate→Prune and index），约束只读命令（ls/find/grep/cat/stat/wc/head/tail）。

### 13.3 召回（`recall.py`）

`MemoryHeader` 扫描（上限 200、前 30 行 frontmatter、按 mtime 最新优先）。`find_relevant_memories` 用独立 LLM selector 从 manifest 选最多 5 个文件名（`SELECTOR_SYSTEM_PROMPT` 要求只输出 `{"selected_memories":[...]}`）。`_extract_json_object` 容忍 markdown 围栏 + 白名单过滤。注入：`App._prefetch_relevant_memories` 用独立 client `asyncio.wait_for(..., 8.0)` 并行 prefetch，工具执行后 `add_system_reminder(render_reminder)`.失败静默返回空（best-effort 不阻塞）。

### 13.4 会话记忆（`session.py`）

`SESSIONS_DIR=".codeagent/sessions"`，每会话 `{id}.jsonl` + `{id}.meta`。`RecordType` 枚举：SYSTEM_PROMPT/USER/ASSISTANT/TOOL_RESULT/COMPRESSION/COMPACT_BOUNDARY。`SessionMeta(id,title,summary,message_count,total_tokens,created_at,last_active)`：title=首条 user 前 50 字符，summary 由 `generate_session_summary`（取最后 10 条历史一句话）后台生成。`SessionManager`：create/list（last_active 倒序）/resume（从最后一个 COMPACT_BOUNDARY 重放）/delete/cleanup(30 天)。

### 13.5 指令加载（`instructions.py`）

`MAX_INCLUDE_DEPTH=5`；`_parse_include` 支持 `@include path` 与 `@./path @../path @~/path @/abs`；`process_includes` 围栏代码块内不展开、循环检测、深度限制。`load_instructions(project_root)` 发现顺序（低→高）：`~/.codeagent/CODEAGENT.md` + `~/.codeagent/AGENTS.md` → 项目目录链每层 CODEAGENT.md + AGENTS.md → `<root>/.codeagent/INSTRUCTIONS.md` → `<root>/CODEAGENT.local.md`；全局文件去重；输出 `Contents of {label}:` 用 `---` 连接。

> 注意：代码**不读 CLAUDE.md**，只读 CODEAGENT.md / AGENTS.md / INSTRUCTIONS.md / CODEAGENT.local.md。通过 `inject_long_term_memory` 包 `# codeagentMd` 注入，不直接进 system prompt。

### 13.6 /memory 命令

`/memory [list | clear | edit]`：list 显示两目录 `[type] name — desc`；clear 删两目录所有 .md；edit 提示路径。只读摘要/清空/提示路径，不触发 extract/recall/consolidation。

---

## 14. Skill（`skills/`）

### 14.1 Skill 格式（`parser.py`）

`parse_frontmatter(raw)`：`lstrip()` 后须 `---` 开头，`find("---", 3)` 求闭合，`yaml.safe_load` 为 dict；正文=第二个 `---` 之后 `.lstrip("\n")`。`_validate_meta`：name、description 必填；name 匹配 `^[a-z][a-z0-9\-]*$`；mode ∈ {inline,fork}（默认 inline）；context ∈ {full,recent,none}（默认 full）；model 可选。

`SkillDef(name, description, prompt_body, mode, model, context, source_path, is_directory)`。`substitute_arguments(prompt_body, args)`：含 `$ARGUMENTS` 则 replace，否则 args 非空 append `"\n\n## User Request\n\n" + args`。

> 注意：**scripts/assets/references 目录约定未在代码中实现**——loader 只找 `skill.yaml`（+`prompt.md`）或 `SKILL.md`，不枚举不执行其它子目录；执行语义由 SKILL.md 正文自然语言指令驱动。

### 14.2 Skill 加载（`loader.py`）

`SkillLoader(work_dir)`；`PROJECT_SKILLS_DIR=".codeagent/skills"`、`USER_SKILLS_DIR="~/.codeagent/skills"`。`load_all()` 顺序 项目 → 用户 → 内置，按名字去重（先见者优先）。`_scan_directory`：平铺 `.md` 走 `parse_skill_file`；目录先试 `skill.yaml`（对齐 Go 版）回退 `SKILL.md`。热加载：`get(name)` 每次重解析 source_path，`reload()`=再 `load_all()`，`needs_reload()` 比较目录 mtime。

注入：`get_catalog()` → `agent.set_skill_catalog()` → `build_environment_context` 追加（含"call LoadSkill to activate"）；`LoadSkill` 返回 `# Skill: {name}` 正文（普通消息回流，非写死 system prompt）；`register_skill_commands` 注册 `/<name>` 斜杠命令。

### 14.3 Skill 执行（`executor.py`）

`SkillExecutor(agent, client, protocol)`，**执行=提示词注入或派生子代理，不含脚本进程执行**。`execute_inline`：`substitute_arguments` → `agent.activate_skill(name, prompt)`；`execute_fork`：新建 ConversationManager，按 `_build_fork_context(skill.context)` 灌历史（none=[]、recent=最后 5 条非 tool_result、full=每条截 200 字符汇总成 user 消息），new Agent 现场跑完返回拼接文本。

### 14.4 Skill 安装（`install.py` + `tools/install_skill.py`）

安全常量：`MAX_FILE_SIZE=1MiB`、`MAX_TOTAL_SIZE=8MiB`、`MAX_FILE_COUNT=64`、`MAX_RECURSION_DEPTH=4`、`HTTP_TIMEOUT=30s`。`parse_skill_url` 支持 skills.sh / github tree / raw.githubusercontent.com 三类 → 统一 `SkillSource{owner,repo,ref,subpath,name}`。`_list_contents` 走 GitHub Contents API、`_fetch_blob` 优先内联 base64 回退 download_url、`_walk_and_download` 防路径穿越 + 大小/数量/深度上限。`install_skill`：`tempfile.mkdtemp` staging 同文件系统保证 rename 原子 → 下载 → 校验 manifest → 删旧目录 → `rename`。`InstallSkillTool` 执行后 `loader.reload()` + `_on_installed` 回调。

---

## 15. Hook（`hooks/`）

### 15.1 Hook 模型（`models.py`）

`Action{type, command, message, url, method="POST", body, headers, prompt, timeout=30}`，type ∈ command/prompt/http/agent。`ActionResult{output, success}`。`Hook{id, event, action, condition, reject=False, once=False, async_exec=False, executed=False}`。`HookContext{event_name, tool_name, tool_args, file_path, message, error}`，`get_field` 支持 `tool`/`event`/`args.<key>`，`expand` 替换 `$EVENT/$TOOL_NAME/$FILE_PATH/$MESSAGE/$ERROR/$TOOL_ARGS.<key>`。`ToolRejectedError(tool, reason, hook_id)`。

### 15.2 引擎/事件/条件/执行器

事件 `LifecycleEvent(StrEnum)`：session_start/end、turn_start/end、pre_tool_use/post_tool_use、pre_send/post_receive、startup/shutdown/error/compact/permission_request/file_change/command_execute。实际派发：startup/shutdown（app）、session/turn/pre_send/post_receive（agent）、pre/post_tool_use（agent 工具路径）；error/compact/permission_request/file_change/command_execute 仅定义未见调用。

`HookEngine.find_matching_hooks`（event 匹配 + should_run + condition.evaluate）；`run_hooks` 先 mark_executed，`async_exec` 用 `ensure_future` 并行否则串行 await；prompt 类成功输出进 `_prompt_messages`，结果进 `_notifications`；`run_pre_tool_hooks` 若 `reject` 立即返回 `ToolRejectedError`（reason=stdout）。

条件 `Condition(field, op, value)`：`==`、`!=`、`=~`（re.search）、`~=`（fnmatch）；`ConditionGroup` and/or；禁止混用 `&&`/`||`。

执行器 `execute_action` → `_EXECUTOR_MAP`：`execute_command`（`ctx.expand` 后 `create_subprocess_shell`，wait_for 超时 kill，success=退出码 0；**不向 stdin 写数据**）、`execute_prompt`（恒 success）、`execute_http`（urllib，响应截 500 字符，success=2xx）、`execute_agent`（stub）。

**stdout 消费（关键：无 stdin JSON 协议）**：命令用 `expand()` 内联变量替换（非 stdin 传 JSON），stdout/stderr 合并纯文本、不 JSON 解码。三类：(1) 上下文注入——prompt 类输出进 `# Hook Injected Context`，notification 经 `add_system_reminder` + yield HookEvent；(2) 阻塞——仅 pre_tool_use + reject，先于权限检查；(3) 无基于 stdout 的决策解析。

### 15.3 Hook 加载（`loader.py` + config）

`load_hooks` 校验：entry 为 mapping；event 必填且 ∈ LifecycleEvent；action type ∈ {command,prompt,http,agent} 且各必填子字段；`reject` 只能配 pre_tool_use；`async` 不能配 pre_tool_use；`if`→`parse_condition`；`timeout` 取 action.timeout（默认 30）；id 缺省 `f"{event}_{i}"`。

YAML 示例（reject/async/once/if/id 在顶层，timeout 在 action 下）：

```yaml
hooks:
  - id: pre-bash-check
    event: pre_tool_use
    if: "tool == Bash"
    reject: true
    action:
      type: command
      command: "policy-check --tool $TOOL_NAME --file $FILE_PATH"
      timeout: 10
  - id: inject-context
    event: session_start
    action:
      type: prompt
      message: "当前事件 $EVENT"
```

---

## 16. Subagent（`agents/`）

### 16.1 定义格式与 parser

每个 subagent 是一个 `.md` 文件：frontmatter 描述元数据，正文 = 发给 subagent 的 system prompt。`AgentDef`（`parser.py`）字段：agent_type(name)、when_to_use(description)、system_prompt(正文)、tools(白名单)、disallowed_tools(disallowedTools)、model(默认 "inherit")、max_turns(maxTurns 默认 200)、permission_mode(默认 "default")、background、isolation("" 或 "worktree")。

`parse_agent_file`：`parse_frontmatter`（须 `---` 开头，yaml 为 dict）→ `_validate_agent_meta`（name/description 必填；permissionMode ∈ {default, acceptEdits, bypassPermissions, ""}；maxTurns 正整数；isolation ∈ {"", "worktree"}）→ 正文 `process_includes` 展开 `@include`。

### 16.2 内置 subagent 与工具裁剪

四个内置（`agents/builtins/`）：**Explore**（只读搜索，disallowedTools=[EditFile,WriteFile]，model:haiku）、**general-purpose**（全工具）、**Plan**（只读规划，disallowedTools=[Agent,EditFile,WriteFile,NotebookEdit]，maxTurns:15）、**Verification**（background:true，只读，输出 `VERDICT: PASS/FAIL/PARTIAL`）。

`tool_filter.resolve_agent_tools` 分层裁剪：第 0 层 `mcp__` 前缀工具分离放行 → 第 1 层 pop 全局禁用 `ALL_AGENT_DISALLOWED_TOOLS`（TaskOutput/ExitPlanMode/EnterPlanMode/Agent/AskUserQuestion/TaskStop/Workflow）→ 第 2 层自定义 agent 再 pop 同七项 → 第 3 层 background 只留 `ASYNC_AGENT_ALLOWED_TOOLS` → 第 4 层 pop disallowed_tools、tools 非空只留白名单。另有 `clone_registry_for_fork`（复制全量 + Agent 工具标 FORK_QUERY_SOURCE）、`build_teammate_tools`、`apply_coordinator_filter`。

### 16.3 AgentLoader

`PROJECT_AGENTS_DIR=".codeagent/agents"`、`USER_AGENTS_DIR="~/.codeagent/agents"`。`load_all()` 优先级 project > user > builtin，按 agent_type 去重先到先得。`get()` 支持热重载（重解析失败回退缓存）。结果经 `AgentTool(agent_loader=...)` 注册进 registry。

### 16.4 TaskManager

`BackgroundTask(id, name, agent, task, status, result, cancel, progress)`。`launch()`：`task_id=uuid4().hex[:8]`，`asyncio.create_task`（无并发上限），返回 id。`_run_background` 跑 `run_to_completion`，成功→completed、CancelledError→cancelled、异常→failed；结束收尾 token 转 progress、`_notify_queue.put`。`poll_completed` 非阻塞排空。结果通知父 agent：`_process_task_notifications` → `inject_task_notifications` 生成 `<task-notification>` 块注入 conversation。

### 16.5 TraceManager

`TraceNode(agent_id, parent_id, trace_id, agent_type, input/output_tokens, tool_call_count, start/end_time, status)`。`create/update/complete/get_tree`。埋点在 agent_tool.execute 每次 spawn 前后。`/trace` 命令递归渲染父子树。

### 16.6 fork

`FORK_BOILERPLATE`（硬规则：不得再 fork、不提问、直接工具、报告 <500 字符以 "Scope:" 开头）。`build_forked_messages`：检测历史含 boilerplate 标记则禁止嵌套 → 新 ConversationManager + `copy.deepcopy(history)` → 末条 assistant 有 pending tool_uses 则补 `content="interrupted"` 的 ToolResultBlock 闭合 → add boilerplate+task。隔离：独立会话深拷贝、`clone_registry_for_fork`、Agent 工具 `query_source=FORK_QUERY_SOURCE` 双重防嵌套、强制后台、bypassPermissions。共享：work_dir/hook_engine/context_window/protocol、trace 继承、`clone_replacement_state` 保 prompt cache 前缀一致。

---

## 17. Worktree（`worktree/`）

`WorktreeManager(worktree_dir=<repo>/.codeagent/worktrees)`：active dict + `asyncio.Lock`；`_run_git` 带 `GIT_TERMINAL_PROMPT=0`、timeout 60。

- **create(name, base_branch="HEAD")**：持锁 → `validate_slug` → `flatten_slug`（`/`→`+`）→ `wt_path` + `branch="worktree-"+flat_slug` → 先 `read_worktree_head_sha` 快速复用否则 `git worktree add -B branch wt_path base_branch` → `perform_post_creation_setup` → 写入 active。
- **enter/exit**：`enter()` 记录 original_cwd/branch/head 构造 WorktreeSession 并 save，**不真正 os.chdir**——真正的 cwd 切换靠装配层把子 agent 构造为 `work_dir=wt.path`。`exit()` 有改动且未 discard 则抛错，`_remove_worktree`（remove --force → branch -D → active.pop）。
- **perform_post_creation_setup** 四步：复制本地配置（settings.json/.env）→ 设 git hooks（.husky 或 core.hooksPath）→ `_create_symlinks`（`symlink_directories` 生效点：root 存在且 wt 下不存在则 `os.symlink` 共享）→ `_copy_ignored_files`（.worktreeinclude 模式 + `git ls-files --others --ignored` + fnmatch 复制）。
- **changes.py**：`count_worktree_changes`（uncommitted=`git status --porcelain`、new_commits=`git rev-list --count`）。
- **cleanup.py**：`EPHEMERAL_PATTERNS`、`cleanup_stale_worktrees` 跳过非 ephemeral/当前 session/有改动/有未推送项后回收。
- **slug.py**：`validate_slug`（≤64、按 `/` 分段、`^[a-zA-Z0-9._-]+$`）、`flatten_slug`。
- **integration.py**：`generate_worktree_name()="agent-a"+token_hex(4)[:7]`、`build_worktree_notice`。

隔离装配链 `agent_tool._execute_with_worktree`：`generate_worktree_name` → `manager.create` → `build_worktree_notice` → `resolve_agent_tools` → `PathSandbox(wt.path)` → `AgentClass(work_dir=wt.path)` → `run_to_completion` → `auto_cleanup`（有改动保留并拼 "[Worktree preserved at ...]"）。team 场景用 `team-{team}/{mate}` 命名。

---

## 18. Teams（多智能体，`teams/`）

### 18.1 数据模型（`models.py`）

`BackendType(str, Enum)`：TMUX / ITERM2 / IN_PROCESS。

`TeammateInfo(name, agent_id, agent_type, model, worktree_path, backend_type, is_active, progress)`：`progress` 只存内存不落盘（内部含 `threading.Lock`，`to_dict()` 显式排除）。`AgentTeam(name, lead_agent_id, members, config_path, description)` + `save/load`（写 `config.json`）。

一个运行期 Team = `AgentTeam` + `SharedTaskStore`（tasks.json）+ `Mailbox`（mailbox 目录）+ spawn 句柄/pane 映射，由 `TeamManager` 的 `_teams/_task_stores/_mailboxes/_inprocess_handles/_pane_ids/_teammate_team_map` 六张 dict 协同持有。

工具函数：`_sanitize_name`（小写、非 `[a-zA-Z0-9_-]`→`-`）、`resolve_team_dir`=`~/.codeagent/teams/<slug>`、`unique_team_name`（冲突加 -2/-3）。

### 18.2 创建流程

`TeamCreateTool.execute` → `detect_backend` → `create_team(lead_agent_id=parent.agent_id)`（建目录、写 config.json、空任务板、邮箱目录，**不 spawn 任何进程**）→ 可选 coordinator mode。

真正生成队友在 `AgentTool._execute_as_teammate`（8 步）：加载 agent 定义（或 fork）→ 建隔离 worktree `team-{team}/{mate}` → 选 LLM → 检测后端 → `trace_manager.create` 拿 agent_id → `build_teammate_tools` → 构造子 Agent（instructions=system_prompt+TEAMMATE_ADDENDUM，PathSandbox(wt.path)，BYPASS）→ 注册 `AgentNameRegistry` + `TeammateInfo` + `register_member` → 按后端 spawn。

**backend_detect 注意**：`detect_backend()` 硬编码恒返 `IN_PROCESS`（参数被忽略）；`detect_pane_backend()` 已实现真正的 tmux/iterm2 检测（TMUX env → iTerm2 → tmux installed → 回退 in-process）但未接入 TeamManager。

### 18.3 协调器（`coordinator.py`）

`get_coordinator_system_prompt(agent_catalog)` 是一份大字符串契约：协调者只拆解/派发/综合；工具契约（Agent/SendMessage/TaskStop/SyntheticOutput/TeamCreate/TeamDelete）；工作流四阶段 Research(worker 并行)→Synthesis(自己)→Implementation(worker)→Verification(**必须另起 Verification worker，禁止实现者自测**)；并发纪律（只读可并行、同一组文件一次一个）；写 prompt 纪律（worker 看不到 Leader 对话，须自包含，禁反例 "Based on your findings..."）；失败处理（继续同一 worker）。

**coordinator_mode 只调度不写代码**靠工具白名单实现（非自觉）：`apply_coordinator_filter` 只保留 `COORDINATOR_MODE_ALLOWED_TOOLS` = {Agent, SendMessage, TaskCreate/Get/List/Update, TaskStop, SyntheticOutput, TeamCreate, TeamDelete, ReadFile, Glob, Grep, Bash} + MCP。**无 EditFile/WriteFile** → Lead 能读/跑命令/派活但不能直接写代码。进入在 TeamCreate（快照 `_full_registry` 后替换），退出在 TeamDelete（删完所有 team 才恢复全量工具）。

`get_coordinator_user_context(worker_tools)` 返回 `{"workerToolsContext": ...}` 描述 worker 可用工具。

### 18.4 邮箱（`mailbox.py`）

`MailboxMessage(id, from_agent, to_agent, content, summary, message_type="text", timestamp, read, metadata)`。`Mailbox(base_dir)`：单文件邮箱——每 agent 一个 `{agent_id}.json`（JSON 数组）+ `.lock` 文件锁。`_with_lock`：`os.open(O_CREAT|O_EXCL)` 原子建锁，FileExistsError 且 stale(>10s) 则 unlink，随机退避 5-100ms，最多 10 次。`write/read/consume/broadcast`：read 不标记已读、consume 标记已读（"取出即消费"）。

消息回流两条回路：**回路 A**（后台任务完成 → `<task-notification>` user 消息，`TaskManager._notify_queue` → `poll_completed` → `inject_task_notifications`）；**回路 B**（队友 idle → `set_member_idle` 给 lead 邮箱写 idle 通知 → `drain_lead_mailbox` → `<team-notification>` system reminder）。

### 18.5 shared_task / progress / transcript / registry

- **SharedTaskStore**（`shared_task.py`）：单 JSON 文件 `{next_id, tasks[]}`，`create/get/list_tasks/update`（先 `_load()` 保证多进程可见，`add_blocks/add_blocked_by` 去重追加）。
- **TeammateProgress**（`progress.py`）：`record_tool_use`（保留最近 5 条活动）、`record_tokens`（覆盖）、`activity_summary`、`format_tokens`（k/M）；100 个 spinner 动词。
- **transcript.py**：`save/load_transcript` 用 `_serialize_conversation` 把 ConversationManager 转 JSON（含 tool_uses/tool_results）。
- **registry.py**：`AgentNameRegistry` 线程安全单例，name↔agent_id 映射，`resolve(name_or_id)`。

### 18.6 spawn 后端

| | in-process | tmux | iterm2 |
|---|---|---|---|
| 拉起 | 当前事件循环 asyncio.Task | `tmux new-window -d` | `it2 split-pane` |
| 独立进程 | 否 | 是（codeagent CLI） | 是 |
| 通信 | 文件系统 Mailbox（500ms 轮询） | Mailbox（环境变量定位） | Mailbox |
| 唤醒 | 邮箱轮询 | `send_keys_to_pane` 空回车 | 未实现 |
| 进度 | `TeammateProgress` 回调实时 | 无 | 无 |

`spawn_tmux_teammate` 生成 CLI 命令：`CODEAGENT_TEAM_NAME=... CODEAGENT_MAILBOX_DIR=... codeagent -p --work-dir <wt> '{prompt}'`（环境变量定位邮箱，单引号转义）。`send_keys_to_pane`/`kill_pane` 走 `tmux send-keys`/`kill-pane`。`spawn_inprocess_teammate` 实现长驻循环（邮箱轮询续活 + shutdown 握手）但**当前无调用点**；实际 in-process 队友走 `TaskManager.launch` 单次 `run_to_completion`。

### 18.7 teammate_tree（TUI）

`TeammateTree(Widget)`：reactive `teammates: list[TeammateProgress]` + `leader_tokens`。渲染 Leader 行 + 每个队友 `├─/└─ @name · activity_summary · N tools · tokens`（状态 completed/failed/idle/running 着色）。app.py 在流式期间每 0.5s `set_interval` 拉 `get_all_teammate_progress` 刷新，流结束移除。

### 18.8 Team 生命周期

创建(TeamCreate→create_team) → 派活(Agent(team_name=...)→_execute_as_teammate 建 worktree+spawn，后续 SendMessage/共享任务板派单) → 队友完成(→set_member_idle + 通知) → Lead 汇总(读 `<task-notification>`/`<team-notification>`，all_idle() 判收工) → 删除(TeamDelete→delete_team：要求全员 idle，逐成员 unregister/cancel/kill_pane/清理 worktree/删 mailbox/删目录)。App 关闭 `_cleanup` 遍历删除所有 team。

---

## 19. 命令系统（斜杠命令，`commands/`）

### 19.1 parser

`parse_command(text) -> (name, args, is_command)`：非 `/` 开头返回 `("","",False)`；`/` 后空是空命令；否则小写命令名 + 剩余参数。

### 19.2 registry

`CommandType(str, Enum)`：LOCAL（本地执行）/ LOCAL_UI（需 UI 特殊处理）/ PROMPT（handler 拼提示词注入 Agent）。`Command(name, description, type, handler, aliases, usage, arg_prompt, hidden)`。`CommandContext(args, agent, conversation, session, session_manager, memory_manager, ui, config)`——`ui` 是 `UIController` 协议（add_system_message/send_user_message/set_plan_mode/get_token_count/refresh_status），CodeAgentApp 与 RemoteServer 都实现它。`CommandRegistry.register/find/list_commands`（冲突检查、别名映射）。

### 19.3 loader（用户自定义命令）

`load_dir` 扫描 `.md`，文件名拼命名空间（`git/log.md`→`git:log`）；frontmatter 取 description/aliases/argument-hint；`_make_prompt_handler` 处理 `$ARGUMENTS` 占位；`load_user_commands` 合并 `~/.codeagent/commands/`（全局）+ `<work_dir>/.codeagent/commands/`（项目级，后者覆盖）。

> 注意：`load_user_commands` 已实现但**未接入启动流程**（app.py/remote.py 只注册内置命令）。

### 19.4 completion

`complete(registry, prefix)` 按前缀匹配命令名/别名，返回 `(display, value)` 前 8 条。`CompletionPopup` 用 Rich markup 高亮当前项，`Tab` 补全、`@` 文件补全（`scan_files_for_at` 跳过 SKIP_DIRS）。

### 19.5 内置命令清单

`ALL_COMMANDS` 注册 12 条 + app.py 动态注册 worktree/tasks/trace + skill 命令：

| 命令 | 类型 | 别名 | 作用 |
|---|---|---|---|
| /help | LOCAL | h, ? | 列命令 / 查单项详情 |
| /compact | LOCAL | c | manual_compact + 持久化 compact_boundary |
| /clear | LOCAL_UI | — | 关 session、重建会话/FileHistory、清空 |
| /status | LOCAL | s | 模式/session/token 占用/工具数/记忆/版本 |
| /session | LOCAL | — | list / resume / new / delete |
| /rewind | LOCAL | — | 文件历史快照回退（1 代码+对话 / 2 对话 / 3 代码） |
| /plan | LOCAL_UI | p | 切只读 Plan 模式并注入计划提示 |
| /permission | LOCAL | — | mode / rules / add / reset |
| /sandbox | LOCAL | — | 1=沙箱+自动放行 / 2=沙箱 / 3=关闭 |
| /skill | LOCAL | skills | list / info / reload |
| /mcp | LOCAL | — | 显示 MCP 服务器与工具数 |
| /memory | LOCAL | — | list / clear / edit |
| /worktree | LOCAL | wt | create/list/enter/exit/status |
| /tasks | LOCAL | task | 列后台任务/info/cancel |
| /trace | LOCAL | tree | 渲染 Agent 父子树 |
| /<skill-name> | PROMPT | — | 触发某个 skill |

`/review`（PROMPT，代码审查提示词）已实现但未注册到 ALL_COMMANDS、无 import，属于未启用代码。

---

## 20. 远程 / 浏览器模式与 TUI

### 20.1 远程模式（`remote.py` + `web_content.py`）

`RemoteServer(providers, mcp_servers, hook_engine)`：WebSocket 连接池 `_connections`（广播）、`_pending_perms: dict[perm_id, Future]`。`run()`：`_init_agent` + `_init_mcp` → `websockets.serve(_ws_handler, addr, port, process_request=_process_http_request, max_size=4MB)` → `await asyncio.Future()` 永久阻塞。默认 `0.0.0.0:18888`。

HTTP：`/`→200 返回 `web_content.INDEX_HTML`；`/ws`→None 继续升级；其它 404。

WebSocket 客户端→服务器消息：`user_message`（create_task 处理）、`permission_response`、`cancel`（set 取消事件）、`ping`（回 pong）。

`_handle_user_message`：`async for event in agent.run(...)` 逐事件广播。事件→消息映射：StreamText→`stream_text`、ThinkingText→`thinking_text`、ToolUseEvent→`tool_use`、ToolResultEvent→`tool_result`、PermissionRequest→`permission_request`（id=`perm_<ns>`，future 存 `_pending_perms`）、TurnComplete/LoopComplete/Usage/Error/Compact/Retry/HookEvent→对应 JSON。权限回环：浏览器点 Allow/Deny/Allow Always → `permission_response` → `future.set_result`。

`web_content.py`：单页 `INDEX_HTML`（Tokyonight 配色 + 内联 JS + 外部 `marked` 库）。`handleMessage` 按 type 分派；`renderMarkdown` 用 `marked.parse`；thinking 折叠（`` ```thinking ... ``` `` 正则拆块）；tool_use 折叠（▶ + 工具名 + ⏳ → ✓/✗ N.Ns）；权限/ask_user 弹窗；斜杠菜单（`/` 过滤 + 上下选择）；每 10s ping 保活、断线 3s 重连。

> 实现差异：前端 JS 保留 `replay_user/replay_assistant/ask_user_response` 等消息但与后端未接通（Go 版遗留）；remote 的 LOCAL_UI 命令只有 clear/compact 真正实现。

### 20.2 driver.py：NoAltScreenDriver

跳过 Textual 的备用屏（alternate screen）：`start_application_mode` 先 `sys.stdout.write("\n" * rows)` 把已有内容顶进 scrollback；`write` 剥掉 `\x1b[?1049h` / `\x1b[?1049l`。非 Windows 用 LinuxDriver 基类、Windows 用 WindowsDriver。

### 20.3 TUI（`app.py`）

`CodeAgentApp(App)`；控件树：title-bar(ASCII 猫 banner) / [provider-select] / chat-area(VerticalScroll) / input-area{ chat-input(ChatInput/TextArea) + status-bar{ mode-label, teammates-label, model-label } + CompletionPopup }。

输入链路：`ChatInput.action_submit` → `Submitted(text)` → `_dispatch_command`（`parse_command` 非命令走 `_send_message`，命令走 `command_registry.find` + handler）。

`_send_message` 流式核心：`_refresh_skills_if_needed` → 展开 `@path` 引用（≤10KB）→ 异步 `_prefetch_relevant_memories`（8s 超时）→ mount 用户行 → `conversation.add_user_message` → `async for event in agent.run(...)` 逐事件渲染：StreamText 累积 + live 更新、ThinkingText 只滚动（TUI 不展示思考文本，用 braille spinner + 随机动词表示）、ToolUseEvent 固化文本后 mount `ToolCallBlock`（EditFile 非错误自动展开，否则默认折叠）、ToolResultEvent `set_result`、PermissionRequest mount `InlinePermissionWidget`、TurnComplete 落盘 session + ≥2 个可折叠工具聚合为 `ToolGroupSummary`、CompactNotification system 消息、ErrorEvent 显示错误、LoopComplete 挂完成标签 + plan 模式下挂审批弹窗。

折叠：`ToolCallBlock` 默认折叠（`✓/✗ 标题 (Ns)`），EditFile 自动展开显示 diff（+ 绿 / - 红）；`ctrl+o` 批量切换。`Agent`（子代理）用 `SubAgentBlock`。

弹窗：`InlineAskUserWidget`（多问题、Tab 导航、多选、Other 自由输入）、`InlinePlanWidget`（YOLO/Manual approve/Feedback 三选项）、`InlineResumeWidget`（会话搜索恢复）。

---

## 21. 附录：配置示例 + 自建清单

### 21.1 完整 config.yaml 示例（合并了本项目的实际部署配置）

```yaml
# ~/.codeagent/config.yaml 或 <project>/.codeagent/config.yaml
providers:
  - name: deepseek
    protocol: openai-compat        # anthropic | openai | openai-compat
    base_url: https://api.0d000721.cv/v1
    api_key: "sk-..."              # 留空则读 OPENAI_API_KEY / ANTHROPIC_API_KEY
    model: deepseek-v4-pro
    thinking: false
    # context_window: 128000       # 可不写，走四层回退
    # max_output_tokens: 8192

permission_mode: default            # default | acceptEdits | plan | bypassPermissions

mcp_servers:
  # stdio 型
  # - name: context7
  #   command: npx
  #   args: ["-y", "@upstash/context7-mcp"]
  #   env: {}
  # HTTP 型
  # - name: my-http
  #   url: https://example.com/mcp
  #   headers: { Authorization: "Bearer ${MY_TOKEN}" }

hooks: []                            # 见第 15 章
enable_fork: false
enable_verification_agent: false
enable_coordinator_mode: false
teammate_mode: in-process

worktree:
  symlink_directories: [node_modules, .venv, vendor]
  stale_cleanup_interval: 3600
  stale_cutoff_hours: 24

sandbox:
  enabled: false
  auto_allow: false
  network_enabled: false
```

权限规则文件 `~/.codeagent/permissions.yaml`、`<project>/.codeagent/permissions.yaml`、`<project>/.codeagent/permissions.local.yaml`：

```yaml
- rule: "Bash(git push*)"
  effect: ask
- rule: "WriteFile(*.log)"
  effect: deny
```

### 21.2 关键目录布局（运行时生成）

```
~/.codeagent/            config.yaml, permissions.yaml, memory/, agents/, skills/, commands/, teams/, history
<project>/.codeagent/    config.yaml, permissions.yaml, permissions.local.yaml, agents/, skills/, commands/,
                       memory/, sessions/, file-history/, worktrees/, session/tool-results/, plans/, debug.log
```

### 21.3 自建清单（照此从零搭建同类工具）

**最小闭环（先跑通）**：
1. 三种 LLM 客户端 + 统一 `StreamEvent`（参考第 5 章 `client.py`）。
2. `ConversationManager`（消息块 + token 锚点，第 6 章）。
3. Pydantic 驱动的 `Tool` 基类 + 6 个基础工具（第 8 章）。
4. `Agent` 事件循环（第 7 章）——先做「单轮：LLM 流式 → 解析 tool_use → 执行 → tool_result 回填 → 下一轮」。
5. 一个输入/渲染层（TUI 或 Web，二选一）。

**第二轮（可用性）**：
6. `PermissionChecker` 分层判决 + 危险命令黑名单 + 规则引擎（第 10 章）。
7. 上下文管理：工具结果落盘 + `auto_compact`（第 9 章）。
8. 系统提示词 `PromptBuilder` 按 priority 拼接（第 9 章）。
9. 会话持久化（jsonl）与 resume（第 13 章 session.py）。

**第三轮（增强）**：
10. 记忆：auto_memory（LLM 提取）→ 召回 selector → 固化（第 13 章）。
11. Skill：SKILL.md 解析 + inline/fork 执行 + 安装（第 14 章）。
12. Hook：command/prompt/http 执行器 + 条件匹配（第 15 章）。
13. Subagent：AgentDef + 工具白名单裁剪 + TaskManager + fork（第 16 章）。
14. MCP：stdio/HTTP 客户端 + 动态参数模型包装（第 12 章）。

**第四轮（规模化）**：
15. Worktree 任务隔离（第 17 章）。
16. Teams：mailbox 通信 + 三种 spawn 后端 + coordinator_mode（第 18 章）。
17. 斜杠命令系统 + 动态 skill 命令（第 19 章）。

### 21.4 本机部署命令（已完成）

```bash
cd /Users/guozi/Desktop/deepseek/codeagent
uv sync                                  # 建 .venv + 装依赖 + 装 codeagent 包
ln -sf "$(pwd)/.venv/bin/codeagent" ~/.local/bin/codeagent   # 全局可用
codeagent --help                           # 验证
codeagent                                   # 交互 TUI
codeagent -p "提示词"                        # 非交互
codeagent --remote                          # 浏览器 http://localhost:18888
```

---

> 全文完。
