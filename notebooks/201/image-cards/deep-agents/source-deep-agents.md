# deep_agents.py 技术知识总结

> 本文档基于 `notebooks/201/deep_agents.py` 的完整教学脚本，提炼 Deep Agents
> 的核心概念、存储后端、子 Agent、Middleware、人在回路、长期记忆与 Skills
> 编排方式，用作图文卡片的源内容。

`deep_agents.py` 是一个面向 LangChain Deep Agents 的 201 级教学示例。
脚本不是单点功能演示，而是从「创建一个能用文件系统做研究的深度智能体」
逐步扩展到「具备工具、子 Agent、后端路由、人工审核、长期记忆与技能系统的
完整研究 Agent」。

---

## 一、核心技术栈

| 技术组件 | 作用 |
| --- | --- |
| `create_deep_agent` | 创建具备规划、文件读写、任务列表与子任务能力的 Deep Agent |
| `utils.models.model` | 项目统一模型入口，避免在业务代码中硬编码模型配置 |
| `@tool` | 将 Tavily 搜索函数封装为 Agent 可调用工具 |
| `TavilyClient` | 提供网络搜索能力，返回标题、URL 与摘要片段 |
| `MemorySaver` | 保存会话状态，让同一个 `thread_id` 可以恢复上下文 |
| `StateBackend` | 默认状态后端，适合临时会话内文件与状态 |
| `FilesystemBackend` | 把指定路径映射到真实磁盘目录，可持久化文件 |
| `StoreBackend` | 把路径映射到 LangGraph Store，适合长期记忆 |
| `CompositeBackend` | 按路径前缀组合多个后端，实现路由式存储 |
| `subagents` | 将专项任务委派给子 Agent，形成协调者-执行者结构 |
| `wrap_tool_call` | 在工具调用前后插入日志、统计或安全逻辑 |
| `ClearToolUsesEdit` | 清理旧工具结果，控制上下文长度 |
| `interrupt_on` | 对特定内置文件工具启用人工审核 |
| `Command(resume=...)` | 将人工决策注入中断点并继续执行 |
| `memory` / `skills` | 给 Agent 注入持久规则文档与可按需加载的技能 |

---

## 二、脚本整体结构

### 1. Harness：最小 Deep Agent

脚本首先用 `create_deep_agent(model=model, system_prompt=...)` 创建研究助理。
这个阶段展示 Deep Agent 默认具备的文件系统和任务规划能力，例如写入
`notes.md`、读取文件、返回虚拟文件系统中的内容。

关键点：

- Deep Agent 内置文件读写工具，不需要手动注册所有基础工具。
- 默认文件系统主要存在于 Agent 状态中，不等同于真实磁盘。
- 中文系统提示词要求 Agent 回答中文，并用反引号引用文件路径。

### 2. 自定义工具：Tavily 搜索

`tavily_search` 用 `@tool(parse_docstring=True)` 封装网络搜索：

- `_create_tavily_client()` 从环境变量读取 `TAVILY_API_KEY`。
- 未配置 key 时抛出 `RuntimeError`，避免进入匿名限流模式。
- 搜索结果被格式化为标题、URL、摘要组成的 Markdown 文本。

教学价值在于：Deep Agent 可以继续使用普通 LangChain 工具；工具 docstring
会成为 LLM 的工具 schema，因此必须清晰描述参数与返回值。

### 3. Backends：文件与状态存储

脚本演示三类后端：

- `StateBackend()`：默认临时状态，适合会话内文件。
- `FilesystemBackend(root_dir=..., virtual_mode=True)`：把 Agent 文件路径映射到真实磁盘。
- `StoreBackend(namespace=...)`：把路径映射到 LangGraph Store，实现长期记忆。

随后通过 `CompositeBackend` 把路径前缀路由到不同后端：

```text
default          -> StateBackend()
/workspace/*     -> FilesystemBackend()
/memories/*      -> StoreBackend()
```

这说明 Deep Agent 的文件系统不是单一存储，而是可以按业务语义分层。

### 4. 子 Agent：研究协调者与研究员

脚本定义 `research_subagent`：

- `name`: `research_subagent`
- `description`: 委派研究任务，一次只给一个主题
- `system_prompt`: 限制搜索次数、要求行内引用和来源部分
- `tools`: `[tavily_search]`

主 Agent 的系统提示词要求：

1. 用 `write_todos` 规划研究任务。
2. 用 `task()` 委派给研究子 Agent。
3. 不直接搜索，始终交给研究子 Agent。
4. 综合结果并写入 `/final_report.md`。

这个结构体现了 Deep Agents 的核心范式：主 Agent 负责规划和综合，子 Agent
负责专项执行。

### 5. Middleware：工具日志与上下文编辑

脚本用 `@wrap_tool_call` 定义 `log_tool_calls`：

- 工具调用前打印工具名和参数。
- 调用 `handler(request)` 执行真实工具。
- 工具完成后打印完成日志。

同时用 `ClearToolUsesEdit(trigger=1, keep=1)` 演示上下文编辑：

- 当工具结果过多时，清理较旧的工具消息。
- 保留最近的工具结果，减少上下文噪声。
- 适合搜索型 Agent，避免旧搜索结果长期污染模型上下文。

### 6. Human-in-the-Loop：文件写入审核

`agent_with_hitl` 通过 `interrupt_on` 对内置文件工具加人工审核：

```python
interrupt_on={
    "write_file": {"allowed_decisions": ["approve", "edit", "reject"]},
    "edit_file": {"allowed_decisions": ["approve", "edit", "reject"]},
}
```

运行时如果 Agent 尝试写文件，会返回 `__interrupt__`。调用方读取
`action_requests` 和 `review_configs` 后，可以用 `Command(resume=...)`
传回审核结果。

脚本重点演示 `edit` 决策：人工把 `/test.md` 改成 `/edited_test.md`，
并修改写入内容。系统提示词要求 Agent 必须尊重审核后的参数，不要改回原请求。

### 7. Long-term Memory：三类记忆与作用域

脚本进一步把 `/memories/` 路径接到 `StoreBackend`，让记忆跨线程保存。

基础长期记忆示例：

- 线程 1 写入 `/memories/findings.md`。
- 线程 2 读取同一路径。
- Agent 必须先查看记忆目录，而不是只依赖当前对话上下文。

高级结构化记忆示例把记忆拆成三类：

- `/memories/semantic/`：事实与知识。
- `/memories/episodic/`：过往经历。
- `/memories/procedural/`：规则与流程。

分级记忆示例继续拆分作用域：

- `/memories/user/`：当前用户私有。
- `/memories/shared/`：全体用户共享。

核心思想：路径前缀决定后端路由，也决定记忆的语义边界。

### 8. AGENTS.md 与 Skills

脚本构造一份虚拟 `/AGENTS.md`，作为研究助理的长期行为规范：

- 规划、研究、反思、综合、撰写、记录。
- 限制搜索次数。
- 合并引用来源。
- 遇到特定格式任务时检查可用技能。

随后构造两个虚拟技能：

- `/skills/linkedin-post/SKILL.md`
- `/skills/twitter-post/SKILL.md`

Agent 创建时注入：

```python
memory=["/AGENTS.md"]
skills=["/skills/"]
files=skill_files
```

这展示了 Deep Agent 的可扩展知识系统：`AGENTS.md` 提供全局规则，Skills
提供按任务触发的专门能力。

### 9. Complete Research Agent：完整研究工作流

最终 Agent 组合了前面的能力：

- `tavily_search` 作为研究工具。
- `/AGENTS.md` 作为固定行为规范。
- `/skills/` 作为可按需加载的内容创作能力。
- `/memories/` 通过 `StoreBackend` 持久保存研究笔记。
- Deep Agent 负责规划、搜索、写报告、调用技能生成社媒内容。

示例任务要求 Agent：

1. 研究 LangChain Deep Agents。
2. 写一份简要报告到 `/final_report.md`。
3. 保存关键研究要点到 `/memories/research_notes.md`。
4. 基于研究结果写 LinkedIn 帖子。

最后新线程尝试读取 `/memories/research_notes.md`、`/final_report.md`、
`/AGENTS.md` 和技能文件，用来对比哪些路径跨线程持久、哪些只属于当前文件注入。

---

## 三、整体架构图

```text
用户任务
  │
  ▼
Deep Agent 主协调者
  │
  ├─ write_todos：拆解任务
  ├─ task()：委派子 Agent
  ├─ built-in file tools：读写文件
  ├─ middleware：工具日志 / 上下文清理
  ├─ interrupt_on：人工审核写文件
  └─ skills：按需生成 LinkedIn / X 内容
  │
  ▼
CompositeBackend 路由
  ├─ 默认路径        -> StateBackend 临时状态
  ├─ /workspace/*   -> FilesystemBackend 真实磁盘
  └─ /memories/*    -> StoreBackend 长期记忆
```

---

## 四、关键要点回顾

1. **Deep Agent 是带文件系统和规划能力的高层 Agent**：比普通工具调用 Agent
   更适合长任务、研究任务和多步骤内容生产。
2. **Backend 决定文件语义**：同样是路径，可能落在临时状态、真实磁盘或长期记忆。
3. **子 Agent 让职责分离**：主 Agent 规划和综合，研究子 Agent 负责搜索执行。
4. **Middleware 负责运行时治理**：日志、工具调用监控、上下文裁剪都属于运行时控制面。
5. **HITL 把危险动作交还给人**：`interrupt_on` + `Command(resume)` 可批准、拒绝或编辑工具调用。
6. **长期记忆要显式建模**：语义记忆、情景记忆、程序记忆，以及用户私有/共享作用域应使用路径和 namespace 区分。
7. **AGENTS.md + Skills 是可移植能力层**：规则常驻，技能按需加载，让 Agent 更像可配置的工作系统。

