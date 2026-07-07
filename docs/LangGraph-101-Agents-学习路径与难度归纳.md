# LangGraph 101 Agents 归纳

> 适用背景：已经基本完成 `notebooks/101/` 与 `notebooks/201/`，
> 接下来要系统学习官方 `agents/` 目录里的独立工程。
>
> 资料来源：本文基于 LangChain 官方
> [`langgraph-101`](https://github.com/langchain-ai/langgraph-101/tree/main)
> 仓库 `main` 分支在 2026-07-07 的公开内容整理。

---

## 一、整体定位

官方 `agents/` 目录不是另一套全新的教程，而是把 notebook 里的核心案例整理成可通过
`langgraph dev` 在 LangGraph Studio 里运行、调试和观察的独立 Agent 工程。

官方 README 对 `agents/` 的定位是：

- `agents/101/`：来自 101 notebook 的简单天气 / 个人助理 Agent。
- `agents/email_agent/`：邮件分流与回复 Agent。
- `agents/music_store/`：音乐商店多 Agent 系统，包含 supervisor 与子 Agent。
- `agents/researcher/`：并行子研究员模式的 Deep Research Agent。
- `agents/deep_agent/`：基于 DeepAgents 的研究 Agent，包含 `AGENTS.md`、skills、
  长期记忆与 HITL。

`langgraph.json` 实际注册了 9 个可运行入口：

| 运行入口 | 代码位置 | 类型 |
| --- | --- | --- |
| 101 Weather Agent | `agents/101/agent.py:agent` | 单 Agent |
| Music Store Catalog Subagent | `agents/music_store/music_agent.py:graph` | 子 Agent |
| Music Store Invoice Subagent | `agents/music_store/invoice_agent.py:graph` | 子 Agent |
| Music Store Supervisor | `agents/music_store/music_store_supervisor.py:supervisor` | 多 Agent Supervisor |
| Music Store Supervisor with Verification | `agents/music_store/music_store_supervisor_with_interrupt.py:graph` | 多 Agent + 身份校验 |
| Music Store Supervisor with Memory and Verification | `agents/music_store/memory_enabled_music_store_supervisor_with_interrupt.py:agent` | 多 Agent + HITL + 长期记忆 |
| Email Agent | `agents/email_agent/graph.py:graph` | 邮件工作流 Agent |
| Research Agent | `agents/researcher/graph.py:graph` | 手写 Deep Research 图 |
| Deep Agent | `agents/deep_agent/agent.py:agent` | DeepAgents 高层封装 |

> 注意：当前本地仓库尚未同步官方 `agents/` 目录；本文按官方仓库结构整理，
> 适合后续拉取官方代码后直接对照学习。

---

## 二、推荐学习顺序

核心原则：先看单 Agent，再看子 Agent，再看 Supervisor，最后看研究型 Agent。
这样能先建立 LangGraph 的状态图心智模型，再理解多 Agent 分工、HITL、Store 与
DeepAgents 封装。

| 顺序 | 学习对象 | 难度 | 建议耗时 | 为什么放在这里 |
| --- | --- | --- | --- | --- |
| 0 | `langgraph.json` | ★☆☆☆☆ | 0.5 小时 | 先知道 Studio 入口如何映射到 Python 对象。 |
| 1 | `agents/101/agent.py` | ★☆☆☆☆ | 0.5-1 小时 | 最小 `create_agent()` 示例，适合热身。 |
| 2 | `music_agent.py` | ★★☆☆☆ | 1.5-2.5 小时 | 第一次接触 `StateGraph` + 工具循环 + 数据库查询。 |
| 3 | `invoice_agent.py` | ★★☆☆☆ | 1-1.5 小时 | 学会从 `runtime.state` 读取业务上下文。 |
| 4 | `music_store_supervisor.py` | ★★★☆☆ | 1.5-2 小时 | 子 Agent 被包装成 tool，由 Supervisor 负责路由。 |
| 5 | `music_store_supervisor_with_interrupt.py` | ★★★☆☆ | 1.5-2.5 小时 | 加入身份校验、结构化输出与 `interrupt`。 |
| 6 | `memory_enabled_music_store_supervisor_with_interrupt.py` | ★★★★☆ | 2-3 小时 | 加入 `BaseStore` 长期记忆，是音乐商店案例的完整形态。 |
| 7 | `email_agent/graph.py` | ★★★★☆ | 2-3 小时 | 邮件分流 + 响应 Agent，业务流程比音乐商店更完整。 |
| 8 | `researcher/graph.py` | ★★★★★ | 4-6 小时 | 手写 Deep Research：并发、子图、压缩、最终报告生成。 |
| 9 | `deep_agent/agent.py` | ★★★★☆ | 2-4 小时 | 用 DeepAgents 封装同类能力，对比“手写图”和“高层框架”。 |

总耗时建议：18-26 小时。若每个案例都做“画图 + 复述 + 小改造”，建议按 4-6 天安排。

---

## 三、分项目归纳

### 0. `langgraph.json`

**学习目标**

理解 `langgraph dev` 如何发现和加载多个 graph，避免只盯着 Python 文件而忽略运行入口。

**关键知识点**

- `graphs` 字段把 Studio 中的名称映射到 `文件路径:对象名`。
- `env` 指向 `.env`，说明运行时统一从项目环境变量读取密钥。
- `dependencies: ["."]` 表示当前项目本身作为依赖安装 / 加载。

**建议动作**

先通读 `langgraph.json`，把每个入口对应到目录结构。后续学习时优先从注册入口进入，
而不是从文件名猜测哪个对象会被 Studio 加载。

---

### 1. `agents/101/agent.py`

**定位**

这是最小可运行的 `create_agent()` 示例：模型 + tools + system prompt。
它更像 notebook 之后的“Studio 版本热身题”。

**涉及知识点**

- `@tool` 工具定义与工具 docstring。
- `create_agent(model=..., tools=..., system_prompt=...)`。
- 外部 HTTP API 工具调用，如 Open-Meteo 天气接口。
- 简单用户偏好与推荐工具。
- 统一从 `utils.models` 导入 `model`。

**难度与耗时**

- 难度：★☆☆☆☆
- 建议耗时：0.5-1 小时

**学习重点**

不要把重点放在天气接口本身，而是观察工具如何被 schema 化后交给模型调用。
这个文件没有显式 `StateGraph`，适合作为 `create_agent()` 的入口案例。

**验收标准**

- 能解释 `@tool` 的函数签名和 docstring 为什么会影响模型工具调用。
- 能说清楚 `create_agent()` 替你隐藏了哪些 Agent 循环细节。
- 能手动加一个简单工具，例如“查询用户语言偏好”。

---

### 2. `agents/music_store/music_agent.py`

**定位**

音乐目录子 Agent，专门回答歌曲、专辑、艺术家、流派相关问题。
这是从 `create_agent()` 过渡到手写 `StateGraph` 的第一站。

**涉及知识点**

- `TypedDict` 定义 `InputState` / `State`。
- `Annotated[list[AnyMessage], add_messages]` 管理消息累积。
- `ToolNode` 执行 SQL 查询工具。
- `StateGraph` 的经典循环：
  `START -> music_assistant -> music_tool_node -> music_assistant -> END`。
- 条件边 `should_continue()` 根据 `tool_calls` 决定继续或结束。
- 从 `loaded_memory` 读取用户偏好，注入系统提示词。
- `SQLDatabase` 查询 Chinook 示例数据库。

**难度与耗时**

- 难度：★★☆☆☆
- 建议耗时：1.5-2.5 小时

**学习重点**

这里最重要的是循环骨架：模型节点只负责决定是否调用工具，`ToolNode` 负责真正执行工具，
工具结果回到消息列表后再交给模型继续推理。

**风险提醒**

官方教学代码里部分 SQL 使用 f-string 拼接，例如按 artist、genre、song title 查询。
这适合教学演示，但生产代码应改为参数化查询，避免 SQL 注入风险。

**验收标准**

- 能白纸画出 `music_assistant` 与 `music_tool_node` 的循环。
- 能解释 `add_messages` 为什么适合消息型 State。
- 能指出哪些状态是输入态，哪些状态是在图运行过程中补充的上下文。

---

### 3. `agents/music_store/invoice_agent.py`

**定位**

发票信息子 Agent，专门回答用户历史订单、发票、支持员工等问题。
它展示了“业务身份信息不从消息里传，而从 state 里读”的模式。

**涉及知识点**

- `create_agent()` 配合 `state_schema=State`。
- 工具函数通过 `ToolRuntime` 读取 `runtime.state.get("customer_id")`。
- 工具 schema 与自然语言查询之间的边界。
- 数据库 join 查询：Invoice、InvoiceLine、Customer、Employee。
- 子 Agent 只处理自己职责范围内的问题。

**难度与耗时**

- 难度：★★☆☆☆
- 建议耗时：1-1.5 小时

**学习重点**

这个 Agent 的核心不是 SQL，而是状态边界：用户消息中不一定包含 `customer_id`，
但 Supervisor 可以把已验证的 `customer_id` 作为 state 注入子 Agent。

**验收标准**

- 能解释为什么工具不应该要求用户重复提供 `customer_id`。
- 能说清 `ToolRuntime` 与普通工具参数的区别。
- 能指出子 Agent prompt 如何限制它只回答 invoice 范围问题。

---

### 4. `agents/music_store/music_store_supervisor.py`

**定位**

音乐商店多 Agent 的 Supervisor。它不直接查数据库，而是把
`music_agent` 与 `invoice_agent` 包装成两个工具，由大模型决定调用哪个子 Agent。

**涉及知识点**

- Supervisor / subagent 架构。
- “把子图当工具”暴露给上层 Agent。
- `HumanMessage(content=query)` 构造子 Agent 输入。
- 从上层 `runtime.state` 取 `customer_id` / `loaded_memory`，再传给子 Agent。
- Supervisor prompt 负责边界控制与结果汇总。

**难度与耗时**

- 难度：★★★☆☆
- 建议耗时：1.5-2 小时

**学习重点**

这里要开始区分“路由决策”和“专业处理”：Supervisor 做计划和委派，子 Agent 做局部任务。
这比一个大 Agent 带所有工具更容易维护，也更容易调试。

**验收标准**

- 能解释为什么 invoice 和 music catalog 要拆成两个子 Agent。
- 能画出用户消息从 Supervisor 到子 Agent 再回到 Supervisor 的路径。
- 能说明 Supervisor 最终为什么要汇总子 Agent 的回答，而不是直接透传。

---

### 5. `agents/music_store/music_store_supervisor_with_interrupt.py`

**定位**

在音乐商店 Supervisor 之前增加身份校验流程。
当用户未提供 customer ID、email 或 phone 时，图会通过 `interrupt()` 暂停，等待人工输入。

**涉及知识点**

- Pydantic `BaseModel` + `Field(description=...)` 做结构化抽取。
- `model.with_structured_output(schema=UserInput)`。
- `verify_info` 节点负责提取与验证用户身份。
- `interrupt("Please provide input.")` 暂停图执行。
- 条件边 `should_interrupt()` 返回 `"continue"` 或 `"interrupt"`。
- `human_input` 节点将人工补充内容重新加入消息流。

**难度与耗时**

- 难度：★★★☆☆
- 建议耗时：1.5-2.5 小时

**学习重点**

这个文件是理解 HITL 的关键。不要只看“问用户要信息”这件事，
要看图如何暂停、恢复、再次进入 `verify_info`，直到 `customer_id` 可用后才进入 Supervisor。

**验收标准**

- 能画出 `verify_info -> human_input -> verify_info` 的回路。
- 能解释 `interrupt()` 与普通 `input()` 的区别。
- 能说明为什么身份校验要放在 Supervisor 前面。

---

### 6. `agents/music_store/memory_enabled_music_store_supervisor_with_interrupt.py`

**定位**

音乐商店案例的完整版本：身份校验 + 长期记忆 + Supervisor + 子 Agent。
它把用户音乐偏好保存到 LangGraph Store，下次会话可读取并用于推荐。

**涉及知识点**

- `BaseStore` 作为长期记忆接口。
- Store namespace 设计：如 `("memory_profile", user_id)`。
- `load_memory(state, store)` 在进入 Supervisor 前加载用户偏好。
- `create_memory(state, store)` 在对话结束后更新用户画像。
- Pydantic `UserProfile` 作为长期记忆结构。
- Store 与 checkpointer 的职责差异：
  Store 存跨会话长期记忆，checkpointer 存单线程运行状态。

**难度与耗时**

- 难度：★★★★☆
- 建议耗时：2-3 小时

**学习重点**

这里要把“记忆”拆成两件事：

- 运行时状态：本轮图执行中传递的 `customer_id`、`loaded_memory`、`messages`。
- 长期记忆：跨线程、跨会话保存的用户音乐偏好。

**验收标准**

- 能解释为什么 `load_memory` 在 Supervisor 前执行。
- 能解释为什么 `create_memory` 在 Supervisor 后执行。
- 能说清 `namespace` 与 `key` 如何定位一条用户记忆。
- 能做一个小改造：新增 `favorite_artists` 字段并完成读写。

---

### 7. `agents/email_agent/graph.py`

**定位**

邮件处理 Agent，包含两个层次：

1. Triage Router：把邮件分类为 `ignore` / `notify` / `respond`。
2. Response Agent：对需要回复的邮件调用工具写邮件、查日历或安排会议。

**涉及知识点**

- `RouterSchema` 结构化输出分类。
- `Literal["ignore", "respond", "notify"]` 限制分类空间。
- `Command(goto=..., update=...)` 在节点内直接决定下一步。
- `MessagesState` 作为内置消息状态。
- 工具绑定：`model.bind_tools(tools, tool_choice="any", parallel_tool_calls=False)`。
- 自定义 `Done` 工具作为任务完成信号。
- 嵌套图：triage 外层工作流调用 response agent 子图。

**难度与耗时**

- 难度：★★★★☆
- 建议耗时：2-3 小时

**学习重点**

这个案例比音乐商店更像真实业务流：先判断是否值得处理，再进入响应流程。
重点观察 `Command` 如何同时表达“状态更新”和“下一跳路由”。

**验收标准**

- 能解释 `ignore`、`notify`、`respond` 三种分类各自如何结束或进入子图。
- 能画出 response agent 的 tool loop。
- 能说明 `Done` 工具为什么可以作为终止信号。

---

### 8. `agents/researcher/graph.py`

**定位**

手写版 Deep Research Agent。它显式实现了用户澄清、研究 brief 生成、
Supervisor 规划、并行 researcher 子图、研究压缩与最终报告生成。

**涉及知识点**

- 多层 `StateGraph`：主图、Supervisor 子图、Researcher 子图。
- `Command[Literal[...]]` 控制节点跳转。
- 用户澄清与 `interrupt`。
- 结构化输出模型：`ClarifyWithUser`、`ResearchQuestion` 等。
- Supervisor 调用 `ConductResearch` 分发研究任务。
- `asyncio.gather()` 并行执行多个 researcher 子图。
- researcher 工具循环与最大迭代次数控制。
- 压缩研究结果，减少最终报告生成上下文压力。
- 最终报告生成与重试逻辑。

**难度与耗时**

- 难度：★★★★★
- 建议耗时：4-6 小时

**学习重点**

这是最值得精读的复杂图。学习时不要从头到尾线性读，
应先画出三层结构：

- 主图：澄清 -> 写 brief -> research supervisor -> final report。
- Supervisor 子图：规划 -> 执行工具 / 分发 researcher -> 继续或结束。
- Researcher 子图：研究 -> 工具执行 -> 压缩结果。

**验收标准**

- 能说清每个循环的终止条件。
- 能解释 `MAX_RESEARCHER_ITERATIONS`、`MAX_REACT_TOOL_CALLS`、
  `MAX_CONCURRENT_RESEARCH_UNITS` 分别防什么问题。
- 能解释为什么需要 `compress_research`，而不是把所有原始搜索结果直接交给最终报告节点。
- 能把并发数改成 1，并预测运行行为变化。

---

### 9. `agents/deep_agent/agent.py`

**定位**

DeepAgents 版本的研究 Agent。它不再手写全部 `StateGraph`，
而是用 `create_deep_agent()` 组合 AGENTS.md、skills、subagents、backend、
长期记忆和 HITL。

**涉及知识点**

- `create_deep_agent()` 高层封装。
- `AGENTS.md` 定义 Agent 身份、工作流与规则。
- skills 目录提供按需加载能力，如 LinkedIn post、Twitter/X post。
- `CompositeBackend` 组合文件系统与 Store。
- `FilesystemBackend(root_dir=..., virtual_mode=True)` 提供虚拟文件系统。
- `StoreBackend()` 负责 `/memories/` 路径下的长期记忆。
- `subagents=[research_subagent]` 委派研究任务。
- `interrupt_on={"write_file": True, "edit_file": True}` 对文件写入做 HITL 审批。

**难度与耗时**

- 难度：★★★★☆
- 建议耗时：2-4 小时

**学习重点**

这个案例适合放在 `researcher/graph.py` 后面学。先看手写版，知道复杂研究 Agent
底层需要哪些部件；再看 DeepAgents，才能理解它帮你封装了什么。

**验收标准**

- 能对比 `researcher/graph.py` 和 `deep_agent/agent.py` 的抽象层级差异。
- 能解释 `AGENTS.md`、skills、backend、subagents 分别解决什么问题。
- 能说明为什么文件写入要通过 `interrupt_on` 加人工审批。

---

## 四、按知识点反向索引

| 知识点 | 推荐学习文件 |
| --- | --- |
| `create_agent()` 入门 | `agents/101/agent.py` |
| `@tool` 与工具 schema | `agents/101/agent.py`、`music_agent.py`、`invoice_agent.py` |
| `StateGraph` 基础循环 | `music_agent.py` |
| `ToolNode` | `music_agent.py` |
| `ToolRuntime` 读取 state | `invoice_agent.py`、`music_store_supervisor.py` |
| Supervisor / subagent | `music_store_supervisor.py` |
| 结构化输出 | `music_store_supervisor_with_interrupt.py`、`email_agent/graph.py` |
| `interrupt` / HITL | `music_store_supervisor_with_interrupt.py`、`researcher/graph.py` |
| 长期记忆 Store | `memory_enabled_music_store_supervisor_with_interrupt.py` |
| `Command(goto, update)` | `email_agent/graph.py`、`researcher/graph.py` |
| 嵌套图 | `email_agent/graph.py`、`researcher/graph.py` |
| 并行子任务 | `researcher/graph.py` |
| DeepAgents 高层封装 | `deep_agent/agent.py` |
| AGENTS.md / skills | `deep_agent/AGENTS.md`、`deep_agent/skills/` |

---

## 五、建议练习节奏

每个 Agent 都按同一套闭环学习：

1. 先看 `langgraph.json` 入口，确认实际加载对象。
2. 白纸画图，只画节点、边、循环和 END 条件。
3. 逐个节点回答：输入 state 是什么、输出 state 改了什么、下一步去哪。
4. 找出工具调用边界：模型决定工具调用，还是节点直接执行工具。
5. 做一个最小改造，再运行验证。

推荐改造题：

| 文件 | 改造题 |
| --- | --- |
| `agents/101/agent.py` | 新增一个用户偏好字段，例如 preferred_language。 |
| `music_agent.py` | 为 `get_songs_by_genre` 增加返回数量参数 `limit`。 |
| `invoice_agent.py` | 增加按 invoice ID 查询明细的工具。 |
| `music_store_supervisor.py` | 让 Supervisor 在回答末尾标明调用过哪个子 Agent。 |
| `music_store_supervisor_with_interrupt.py` | 增加“无法验证超过 2 次后转人工”的分支。 |
| `memory_enabled_music_store_supervisor_with_interrupt.py` | 给用户画像增加 favorite_artists。 |
| `email_agent/graph.py` | 增加 `archive` 分类或 `forward_email` 工具。 |
| `researcher/graph.py` | 把最大并发研究单元改为 1，观察结果与耗时变化。 |
| `deep_agent/agent.py` | 新增一个写“小红书笔记”的 skill。 |

---

## 六、学习完成后的判断标准

完成 `agents/` 学习不等于每个文件都跑过一遍。更可靠的判断标准是：

- 能不用看代码画出音乐商店完整图：身份校验、加载记忆、Supervisor、子 Agent、
  写回记忆。
- 能解释 `messages`、`customer_id`、`loaded_memory`、`store` 各自属于哪类状态。
- 能说清什么时候用 `create_agent()`，什么时候手写 `StateGraph`。
- 能解释 `interrupt` 是如何暂停并恢复图执行的。
- 能解释 Store 与 checkpointer 的区别。
- 能对比手写 `researcher/graph.py` 和 DeepAgents 版 `deep_agent/agent.py`：
  一个显式可控，一个封装度高、工程效率高。

如果这些都能讲清楚，说明你已经从“会运行官方示例”进入了“能设计自己的 LangGraph Agent”
的阶段。

---

## 七、参考链接

- 官方仓库主页：
  <https://github.com/langchain-ai/langgraph-101/tree/main>
- 官方 `agents/` 目录：
  <https://github.com/langchain-ai/langgraph-101/tree/main/agents>
- 官方 `langgraph.json`：
  <https://raw.githubusercontent.com/langchain-ai/langgraph-101/refs/heads/main/langgraph.json>
- LangGraph 文档：
  <https://docs.langchain.com/oss/python/langgraph>
- Deep Agents 文档：
  <https://docs.langchain.com/oss/python/deepagents>
