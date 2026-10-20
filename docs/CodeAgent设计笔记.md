> 本文是自研终端 Coding Agent「MewCode / CodeAgent」的设计笔记，覆盖从系统提示词设计、上下文压缩、权限模型、MCP 协议接入，到 Skill 系统、多 Agent 团队协作与 Git WorkTree 隔离的完整设计思路。

## 一、文档体系设定

prec

```
回答做什么：背景、目标、功能需求、边界、验收标准
```

plan

```
回答怎么做
	架构 组件划分 接口定义   技术决策
```

task

```
文件清单 有序任务列表 每步验证方式
```

checklist   行为检查 端到端场景

## 二、系统提示词的设计

#### 设定

1. 角色设定
2. 行为准则 (如何和用户沟通)
3. 工具使用准则 (并行执行 不要默认用bash)
4. 代码质量规范 (agent默认使用自己聪明加很多注释说明自己理解代码 加入抽象层 证明自己聪明 加错误处理)
5. 安全便捷 (软约束  和权限系统不一样 )
6. 任务执行模式 (分析任务类型 是bug修复还是功能迭代还是重构项目)
7. 输出风格

系统提示词根据场景不断迭代和边界 case 打磨  是一个不断演化 活的系统

#### 来源

1. 静态设定 上面七个
2. 环境上下文 (工作目录 操作系统 时间 git状态)
3. 工具描述
4. 项目指令文件
5. 自动记忆
6. system reminder 动态上下文
7. 对话历史

不同来源的prompt需要放入不同的 system message / tools 字段

### system reminder

有的是突然出现的 必须知道的提示词、特殊信息标记  应该放在 message 字段中 但是需要xml包裹  告诉模型这不是用户说的话，是补充指令 经典场景 比如

```
mcp server的上线下线
可用skill
agent的类型
```

我们不可以直接 修改system prompt这样会让cache失效

### 功能效果

1. system  prompt稳定性 :   cache命中 便宜
2. output控制   减少输出
3. 调用效率的提升 : 并行调用工具  少轮次对话

## 三、权限控制与威胁模型

### 威胁模型

1. prompt注入
2. 越权操作
3. 数据泄露

#### 防线

1. 危险命令黑名单
2. 沙箱操作  操作限制的文件夹以内
3. 权限规则语法 (本地级别  项目级别  用户级别)
4. 权限模式
5. hitl 最终用户确定

## 四、MCP 协议

### Mewcode 作为Host

### server

提供tools 包括名称参数json定义

提供resources 可读数据源

提供prompt  agent调用的时候传入参数 server 生成一个提示词文本  agent利用文本生成sql  类似skill

### client

提供roots 工作边界

sampling  让server反过来请求host调用llm

elicatation 允许用户 追问额外信息

### 实现方法

#### stdio

host 把 mcp server 当作子进程启动  通过管道读写信息  可以访问任何远程服务  管道只负责host-server的通信状况

#### streamable

 http mcp server 是一个 HTTP 服务  必要时用sse做流式传输 server可能在本地或者远端

![image-20260729162313820](https://mdpicture.tos-cn-beijing.volces.com/md/image-20260729162313820_1785313401020.png)

## 五、上下文压缩

![image-20260730105407246](https://mdpicture.tos-cn-beijing.volces.com/md/image-20260730105407246_1785380047392.png)

### 1 内存压缩

对话历史保留预览和文件路径

如果每次更新预览的前缀 prompt cache会被更新  所以采取决策冻结方案

```
系统维护一个文档 记录工具的替换决策 一旦一个工具的结果在某一轮决定不替换的时候  决定会在会话期间永远不变  即使后来按照聚合限制他应该被替换 也不替换  因为会破坏前缀
```

 ![image-20260730113529193](https://mdpicture.tos-cn-beijing.volces.com/md/image-20260730113529193_1785382529294.png)

### 2全量摘要

#### 触发时间

 窗口剩余 20k 左右可以触发一次 readfile 的时候

#### 设计

```
主要请求和意图
关键技术概念 (讨论过的技术点)
文件和代码段(设计文件 和关键代码)
错误和修复
问题解决思路
所有的用户信息(优先原文保留:意图偏好语气)
待办任务
当前工作
可能的下一步
```

分为两阶段生成  先写草稿 最后只保留summary

禁止工具调用

#### 恢复

附加部分内容 :

```
最近访问文件
技能定义
工具列表
压缩边界信息
```

#### 熔断

如果因为网络或者 api 或者提示词太长超过失败三次 自动触发停止

或者当摘要太多的时候可以考虑先把信息按 api 轮次分组 丢弃最旧的几组 剩下的信息重试

紧急压缩机制 当用户正常对话发过去结果 上下文太大了 直接卡死了 可以考虑压缩重试

### 3compact

#### 1预防性压缩

接下来有一堆文件呢

#### 2话题切换

## 六、跨会话记忆与持久化

### 会话持久化

```
jsonl格式
```

恢复对话

1. 逐行解析
2. 验证消息链
3. 检查token
4. 时间提示

加入过期对话清理

### 项目指令文件

```
readme文档

根目录优先级最高

项目级可以gitignore忽略

个人偏好类型
```

```
include模块化指令控制
```

### 自动记忆

类比

- 用户偏好 : 个人编码习惯和风格要求
- 纠正反馈 :  根据输出的纠正 方法
- 项目知识 project: 具体技术信息
- 参考信息 reference 外部链接 和资料

## 七、Slash 命令框架

### 注册

声明自己是谁  能干什么 怎么用

command身份证 声明式注册

web框架 路由注册中心  读写锁并发安全保护

### 解析

拆出命令名和参数

解析拆分

### 执行

命令可以操作agent 修改对话  更新ui 读取配置

### 命令类别

- local 本地   /help /status
- local-ui   /clear   /plan
- prompt   /review  类似快捷方式的介绍 省去用户输入输出的prompt

### 集成ui循环

如何插入到事件循环

1. 输入分流器  拦截解析

2. 查找和执行

3. 位置命令 引导到help

   状态栏也要更新

![image-20260731153850250](https://mdpicture.tos-cn-beijing.volces.com/md/image-20260731153850250_1785483530394.png)

## 八、Skill 系统
把专家经验 操作流程和最佳实践打包成了可复用的能力

- 一致性 在不同的api  cli 软件上行为他提一直
- 知识固化
- 跨平台复用

和slash对比  续借prompt这一思路       skill的优化在于不仅仅是传输 prompt

- skill.md 装SOP流程
- tool.json 装工具 的schema
- reference  装工具实现代码  长文档 API参考 辅助脚本
- 加上  allowedtools 工具白名单  inline/fork 执行模式 和 argument参数机制

#### 文件结构

```
md文档
人可以直接阅读   系统可以直接用yaml frontmatter解析结构化数据  LLM可以直接理解promptbody的指令
```

### inline

默认方式  skill的 prompt注入到当前对话  和正常用户消息走agent loop skill可以看到之前上下文 执行结果保留到对话历史

### fork
新开一个独立的上下文执行 只返回结果回主对话

### argument

用户可以上传具体参数

### skill加载成命令

自动加载成slash command  调用/commit调用它

服用/prompt的命令类型 便利skill  在注册中新家一个prompt类型命令  加入skill标记

1闭包变量捕获     闭包循环调用skill

2热加载  每次执行发都重新解析文件  确保拿到最新内容

1. 轻量注册 : 启动只加载 frontmatter  不加载完整的prompt body 和专属工具   claude把清单 当作system reminder塞入user的信息层  每轮会多带一段token  下一轮就会生效
2. 按需加载 :  agent调用loadskill  首先 把skill.md完整的prompt body激活到agent的上下文  加载 tool.json 的专属工具注册到对话  返回一句简短的确认信息   skill 绑定到 env context 上

skill删除跟着/clear走  这个负责清空对话历史  重建session

### 目录式skill

![image-20260731163548169](https://mdpicture.tos-cn-beijing.volces.com/md/image-20260731163548169_1785486948255.png)

```
tool.json 负责注册 给环境中加入一个新工具
allowedtool 可见性 允许使用文件
这些特性让目录型skill 可以自带新的工具
整套能力可以打包移植
```

### allowedtools

最小权限原则：fail-fast 检查可以提前发现错误工具，不会让 agent 跑起来再失败

### 互相调用

1. 默认禁止嵌套  闭包   行为可预测
2. 允许  sop可能叠加冲突  成本爆炸 ![image-20260731164332871](https://mdpicture.tos-cn-beijing.volces.com/md/image-20260731164332871_1785487412983.png)

```
业务工具和系统工具
```

## 九、Hook 机制
针对 触发条件明确 执行动作固定的动作设定自动化动作

```
会话级事件
工具级事件
消息级事件
系统级事件
触发
```

#### 条件语法

```
权限规则匹配  正则表达式
```

动作执行:

​	执行cmd   注入修改prompt  发送http请求  启动子agent

## 十、多 Agent 协同

上下文污染 同时让agent做不同的两件事情

agent和tool 抽象同构

子 agent 是非交互式的设定  输入任务 通过llm和工具 得到结果返回

父子agent的嵌套护额姐  设定工具来做隐式限制

### 定义式

预定义角色 能力 行为规范  限定工具  空白上下文

### fork

继承上下文临时助手

### 上下文隔离

共享llm客户端  工具及  hook引擎 文件系统

隔离文件缓存  权限追踪 token计数

### 后台运行方式

1. 调用时指定
2. 自动超时
3. 手动切换

### 工具设定

1. 全局禁止列表 所有子agent都不能使用的工具
2. 自定义 agent 禁止使用custom agent 禁止工具
3. 后台agent 白名单
4. agent  定义的tools 禁止工具

### 内置agent设定

- explore
- plan
- general purpose
- verification

## 十一、Git WorkTree

在原文档的基础上开一个分支    和复制的区别

- 共享同一个git的仓库元数据

- 有自己的工作区文件

- 通常从某个分支的head创建

- 可以带入未提交改动

- git 分支不能被两个 worktree checkout



### 创建流程

1. 验证名称
2. 创建路径和分支名，加上 worktree 前缀
3. 性能优化 快速恢复

创建后设置 缺少部分依赖

1. 复制 setting.local.json
2. 复制worktreeinclude文件
3. 配置 core.hookspath
4. 软连接大目录

创建完后  我们不动进程级 cwd  把worktree路径记录在会话信息  每次工具调用自己显式取 cwd

```
如果直接切换了chdir  会导致 cwd是好几个 并发组件有时序问题   但是如果显式cwd 在后续agent调用工具是 直接传给子进程 或者文件操作的时候  这比直接修改全局状态更加可控
主 agent 调用多个工具 每次都会在session取得当前worktree
子agent开了新的worktree  有自己的session
工具调用栈深  每一层都有自己的session取
```

## 十二、多 Agent 团队

subagent 让主 agent 分派任务给子agent 实现独立上下文执行  Worktree 让每一个子agent拥有独立的文件系统 消除并行修改的冲突

串行处理修改成并行处理  首先多个agent能直接交流  自主协调

```
底层实现 走的共享文件邮箱加上500ms的轮询 消息会在收件人下一轮的agent loop开头被读到  队员之间直接寻址
```

### 其余框架实现

```
AuToGen:
	集中式的信息代理 无指定接收者  发到管线上  其余的agent根据  订阅兴趣 或者groupchatmessager来决定是否消费此条信息

CrewAi
	交互通过共享的任务输出  维护一个上下文表单 任务执行的时候进行变量替换 上下文拉取前置任务的输出  隐形交互   流程决定 顺序严格按照硬编码执行


LangGraph
	本质上函数调用贴图 交互完全由图的拓扑结构和条件边界
	共享一个集中的State字典
```

### 实现

```
协调能力以工具形式注入每个队员的工具集   llm根据共享信息列表和信息判断

原本subagent 通过 TaskManager 管理后台任务  我们Agent Team加入了一组协调工具  实现创建任务 同步进度 直接发信息多个功能

```

```
流程 plan 计划审批工作流
Agent名称注册表
判断依赖
	系统级别依赖 任务2依赖任务1完成
	文本约定  补充说明

lead派生队员 每个队员自动创建worktree  有自己的工作目录 派生方式取决于后端
```

```
队员的派生流程
```

1. 加载agent的定义
2. 创建WorkTree
3. 调用 buildTeammateTools 协调工具注入到基础工具集
4. 按后端分流  tmux iterm2走不同终端
5. 队员名字注册 agentNameRegistry
6. 构造TeammateInfo 注册到用户

```
往工具集中注入协调工具  在系统提示中追加一段团队通信的补充说明
LLM全程自己判断工具的调用 协调工具 任务状态处理  队员根据自己上下文选择任务接受  自己选择任务循环

收敛
	当任务标记成 completed  lead 合并回主分支  由LLM推理驱动  lead通过bash 执行git

清理 终止队员 删除worktree 清理任务文件和团队目录

补充空闲续写机制 让队员停下来 可以重复唤醒
```

```
任务分解策略
	文件边界分任务  合并冲突时  把任务分成串行
	控制每一个队员的任务数
	依赖关系明确 addBlockedBy建立系统级依赖
	留一个验证任务
```

```
冲突预防
	worktree隔离
	任务拆分
	LLM驱动 智能合并
```

### Coordinator Mode

```
当任务复杂的时候  lead上下文爆炸  又要协调也要调用工具 还要写代码

工具集首先收窄

修改提示词  任务重新拆解
	research 队员并行调查
	synthesis lead理解 撰写规格
	implementation  队员修改代码
	verfication  测试改动
```

## 附：面试考点梳理

### 1流式协议归一化

cursor会有多个adapter适配器处理完上下文然后分发给后台的LLM

本项目中在LLM Client层处理这个差异  对外只暴露一套抽象事件 :文字增量 工具调用开始

工具入参增量  工具调用结束  流结束

设定统一的接口调用LOOP 有分别的请求构造器和SSE解析器 来做协议适配 输出统一事件

### 2上下文预算(压缩)

#### 原因

1. 成本
2. 思考质量
3. 上下文焦虑

#### 实现

https://bojieli.github.io/ai-agent-book/book/chapter2/

思路:检索而非压缩  系统的prompt  tool definitions不变   压缩 tools result  衡量压缩时机

1. 大结果存磁盘  存储索引 写摘要
2. 噪声直接删除
3. 归档式摘要 生成结构化摘要 保留会话逻辑脉络
4. api压缩 在服务端溢出工具结果  本地信息不变  (当上下文溢出 缓存一定不命中的时候 )
5. LLM直接驱动
6. 子agent隔离

#### 原则

1. 信息价值非均匀分布
2. 语义完整性
3. 任务相关性
4. 压缩目的是理解

### 3对话历史一致

当压缩 或者用户esc时会导致破坏  历史的 tool_use 会变成孤儿调用，没有对应的 tool_result

当进程意外崩溃恢复会话的时候也可能出现不完整的对话轮次

补充对话检验逻辑

1. 当 jsonl 日志恢复对话
2. 上下文压缩
3. 用户中断之后

### 4五层权限拦截模型

### 5多Agent和WorkTree隔离

---

*笔记对应开源项目：[CodeAgent](https://github.com/g164765280-netizen/codeagent)。*
