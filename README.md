# ⚡ CodeAgent

一个运行在终端里的 AI 编程助手（terminal AI coding assistant），支持 Anthropic / OpenAI 兼容协议与 MCP，提供 **Web 演示界面** 和 **终端 TUI** 两种交互方式。

## 功能特性

- 🤖 Agent 主循环：流式输出、思考过程、多轮工具调用
- 🛠️ 内置工具：文件读写/编辑、Bash、Glob/Grep 搜索、子 Agent、Worktree 等
- 🌐 Web Remote 模式：浏览器里的现代化对话界面（工具卡片、权限弹窗、斜杠命令）
- 💻 终端 TUI 模式：基于 Textual 的全功能终端界面
- 🔌 MCP 协议：支持 stdio / HTTP / SSE 的 MCP 服务器接入
- 🧠 记忆系统：自动记忆、会话摘要、上下文压缩
- 👥 多 Agent：子任务派发、Team 协作、协调者模式
- 🔐 权限系统：四级权限模式、路径沙箱、危险命令检测

## 环境要求

- Python ≥ 3.11
- [uv](https://docs.astral.sh/uv/)（推荐）或 pip

## 安装

```bash
git clone https://github.com/g164765280-netizen/codeagent.git
cd codeagent

# 方式一：uv（推荐，自动建虚拟环境并装依赖）
uv sync

# 方式二：pip
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

## 配置

首次运行前，创建配置文件 `.codeagent/config.yaml`（项目级）或 `~/.codeagent/config.yaml`（全局）：

```yaml
providers:
  - name: deepseek
    protocol: openai-compat        # openai-compat / openai / anthropic
    base_url: https://api.deepseek.com/v1
    api_key: "sk-你的APIKey"
    model: deepseek-chat
    thinking: false

permission_mode: default            # default / acceptEdits / plan / bypassPermissions
mcp_servers: []
```

> 完整配置示例（含 MCP 服务器、HTTP transport）见 `.codeagent/config.yaml.example`。
> `api_key` 也可以留空，改从环境变量读取：`OPENAI_API_KEY` / `ANTHROPIC_API_KEY`。

## 启动方式

### 1. Web 演示模式（推荐用于演示）

```bash
python -m codeagent --remote
```

浏览器打开 **http://localhost:18888** —— 侧边栏 + 对话流 + 工具卡片 + 权限弹窗的现代 Web 界面。

### 2. 终端 TUI 模式

```bash
python -m codeagent
```

全功能终端界面：对话、工具调用、Teammate 树、斜杠命令补全。

### 3. 非交互管道模式

```bash
python -m codeagent -p "帮我看看 pyproject.toml 里的依赖"
python -m codeagent -p "..." --output-format stream-json   # NDJSON 事件流
```

### 常用选项

| 选项 | 说明 |
|------|------|
| `--mode acceptEdits` | 自动接受文件编辑，命令仍需确认 |
| `--mode plan` | 只读规划模式，不做任何修改 |
| `--mode bypassPermissions` | 跳过所有权限询问（慎用） |

## 常用斜杠命令

会话内输入 `/` 唤起命令菜单：

| 命令 | 作用 |
|------|------|
| `/help` | 帮助信息 |
| `/compact` | 压缩上下文 |
| `/clear` | 清空对话历史 |
| `/plan` | 切换 Plan 模式 |
| `/memory` | 记忆管理 |
| `/skill` | 管理 Skill 技能包 |
| `/mcp` | MCP 服务器状态 |
| `/session` | 会话管理 |
| `/status` | 状态信息 |

## 运行测试

```bash
python -m pytest tests/ -q
```

## 项目结构

```
codeagent/
├── __main__.py       # CLI 入口（--remote / -p / TUI）
├── app.py            # 终端 TUI 界面
├── remote.py         # Web 模式：WebSocket + HTTP 服务
├── web_content.py    # Web 前端页面
├── agent.py          # Agent 主循环与事件
├── client.py         # LLM 客户端（Anthropic / OpenAI 兼容）
├── config.py         # 配置加载
├── agents/           # 子 Agent 与任务管理
├── commands/         # 斜杠命令
├── memory/           # 记忆 / 会话 / 指令加载
├── permissions/      # 权限模式与沙箱
├── skills/           # Skill 技能系统
├── teams/            # 多 Agent 团队
├── tools/            # 内置工具集
└── worktree/         # Git worktree 隔离
```

## 文档

- [CodeAgent 实现文档](CodeAgent实现文档.md)
- [CodeAgent 设计理念](CodeAgent设计理念.md)
