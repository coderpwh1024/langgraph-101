# LangChain / LangGraph 官方生产级 Demo 调研

> 调研时间：2026-07-09  
> 范围：`langchain-ai` 官方 GitHub 组织、LangChain / LangGraph / LangSmith 官方文档与官方模板仓库。  
> 目标：筛选接近生产形态、覆盖 LangChain / LangGraph / Deep Agents / LangSmith 关键知识点的 demo、模板和 workshop。

## 一、结论

如果只选一条学习路线，建议按下面顺序推进：

1. [`langgraph-101`](https://github.com/langchain-ai/langgraph-101)：建立 LangChain、LangGraph、Deep Agents 的全局认知。
2. [`agents-from-scratch`](https://github.com/langchain-ai/agents-from-scratch)：通过 email assistant 学 agent、评估、HITL、memory。
3. [`langsmith-agent-lifecycle-workshop`](https://github.com/langchain-ai/langsmith-agent-lifecycle-workshop)：学习企业级 AI 工程生命周期。
4. [`social-media-agent`](https://github.com/langchain-ai/social-media-agent) 或 [`open-swe`](https://github.com/langchain-ai/open-swe)：研究真实业务 agent 的工程组织。
5. [`deployment-cookbook`](https://github.com/langchain-ai/deployment-cookbook) + [`agent-chat-ui`](https://github.com/langchain-ai/agent-chat-ui)：补齐前端、协议、部署和生产运行形态。

这几类仓库组合起来，基本覆盖：

- LangChain：模型、工具、agent harness、structured output、middleware、retrieval。
- LangGraph：状态图、节点、边、checkpoint、store、streaming、interrupt、HITL、memory、subgraph、多 agent。
- Deep Agents：planning、subagents、filesystem tools、skills、context management。
- LangSmith：tracing、evaluation、deployment、online evaluation、annotation/data flywheel。
- 生产工程：UI、认证、持久化、Agent Server、LangGraph Platform、CI/CD、前后端协议。

## 二、最值得看的官方仓库

| 优先级 | 仓库 | 适合学习 | 推荐理由 |
| --- | --- | --- | --- |
| 1 | [`langgraph-101`](https://github.com/langchain-ai/langgraph-101) | LangChain + LangGraph + Deep Agents 全景 | 官方教学主线。`101` 覆盖模型、工具、记忆、流式；`201` 覆盖 email agent、多智能体、research agent、DeepAgents、HITL、生产工作流；还能通过 `langgraph dev` 跑独立 agent。 |
| 2 | [`agents-from-scratch`](https://github.com/langchain-ai/agents-from-scratch) | 从零构建接近真实的 email assistant | 从 agent 基础一路到 evaluation、human-in-the-loop、memory、Gmail 集成和部署。代码在 `src/email_assistant`，比纯 notebook 更接近工程结构。 |
| 3 | [`langsmith-agent-lifecycle-workshop`](https://github.com/langchain-ai/langsmith-agent-lifecycle-workshop) | AI 工程生命周期 | 企业 workshop 风格：客服 agent、多智能体 supervisor、HITL、离线评估、线上评估、部署、数据飞轮。 |
| 4 | [`social-media-agent`](https://github.com/langchain-ai/social-media-agent) | 真实业务 agent | URL 输入生成 X / LinkedIn 内容，包含 HITL、认证、调度、Agent Inbox、Slack、GitHub、Supabase、LangGraph Server。 |
| 5 | [`open-swe`](https://github.com/langchain-ai/open-swe) | 生产级异步 coding agent 架构 | 官方开源 coding agent 形态：LangGraph + Deep Agents、云沙箱、Slack / Linear / GitHub 触发、子 agent、middleware、自动 PR。 |
| 6 | [`deployment-cookbook`](https://github.com/langchain-ai/deployment-cookbook) | 生产部署形态 | 专门讲生产运行 LangChain agents：streaming UI、subagents、thread history、Agent Streaming Protocol、Redis / Postgres / SQLite checkpoint 替换等。 |
| 7 | [`agent-chat-ui`](https://github.com/langchain-ai/agent-chat-ui) | 前端 + LangGraph agent 对接 | Next.js UI，可连接任意带 `messages` key 的 LangGraph server；包含 production setup、API proxy、认证说明。 |
| 8 | [`langgraph-fullstack-python`](https://github.com/langchain-ai/langgraph-fullstack-python) | 单部署全栈 Python chatbot | 一个 LangGraph deployment 同时托管 agent 和 UI，通过 `langgraph.json` 配置 graph + HTTP app，适合看最小全栈形态。 |

## 三、按知识点补充阅读

| 知识点 | 推荐仓库 | 重点 |
| --- | --- | --- |
| ReAct / 工具调用基础 | [`react-agent`](https://github.com/langchain-ai/react-agent) | 官方 LangGraph ReAct 模板，展示 reason-act-observe 循环和工具扩展。 |
| RAG 基础 | [`rag-from-scratch`](https://github.com/langchain-ai/rag-from-scratch) | 从 indexing、retrieval、generation 开始理解 RAG。 |
| 可生产化 RAG | [`retrieval-agent-template`](https://github.com/langchain-ai/retrieval-agent-template) | index graph + retrieval graph，支持 Elasticsearch、MongoDB Atlas、Pinecone，带 `user_id` 过滤。 |
| Web research + 结构化输出 | [`data-enrichment`](https://github.com/langchain-ai/data-enrichment) | 搜索、读取网页、抽取结构化 JSON、校验完整性。 |
| 长期记忆 | [`memory-template`](https://github.com/langchain-ai/memory-template)、[`memory-agent`](https://github.com/langchain-ai/memory-agent) | 用户级 memory、跨 thread 记忆、LangGraph Store。 |
| 多智能体 | [`langgraph-supervisor-py`](https://github.com/langchain-ai/langgraph-supervisor-py)、[`langgraph-swarm-py`](https://github.com/langchain-ai/langgraph-swarm-py) | supervisor、handoff、层级多 agent、swarm。注意官方现在更推荐直接用 tool-calling supervisor pattern。 |
| 大量工具选择 | [`langgraph-bigtool`](https://github.com/langchain-ai/langgraph-bigtool) | 用 LangGraph Store 检索工具，让 agent 面对大量工具时先找相关工具再调用。 |
| JS / Next.js 全栈 | [`langchain-nextjs-template`](https://github.com/langchain-ai/langchain-nextjs-template) | chat、structured output、agent、多步问题、RAG chain、RAG agent、流式 UI。 |

## 四、不建议作为新项目起点

| 仓库 | 原因 |
| --- | --- |
| [`rag-research-agent-template`](https://github.com/langchain-ai/rag-research-agent-template) | 已在 2026-03-11 archived，只适合参考旧模板结构。 |
| [`open-agent-platform`](https://github.com/langchain-ai/open-agent-platform) | README 标注 deprecated，官方建议改用 LangSmith Agent Builder。 |

## 五、推荐学习路径

### 1. 基础全景：`langgraph-101`

先跑 `notebooks/101/`：

- `101_langchain_langgraph.ipynb`：模型、工具、agent、memory、streaming。
- `102_middleware.ipynb`：middleware、human-in-the-loop、guardrails。

再看 `notebooks/201/`：

- `email_agent.ipynb`：完整 stateful email agent。
- `multi_agent.ipynb`：supervisor + specialized sub-agents。
- `research_agent.ipynb`：并行 sub-researchers。
- `deepagents.ipynb`：AGENTS.md、skills、backends、long-term memory、HITL。

最后用 `langgraph dev` 跑 `agents/` 目录下的独立 agent：

- `agents/email_agent/`
- `agents/music_store/`
- `agents/researcher/`
- `agents/deep_agent/`

### 2. Agent 工程化：`agents-from-scratch`

重点看四段递进：

- agent：email triage + response agent。
- evaluation：Pytest + LangSmith `evaluate`，覆盖 tool call、triage decision、LLM-as-judge。
- HITL：用 Agent Inbox 审核发邮件、排会议等高风险工具调用。
- memory：用 LangGraph Store 记录用户偏好，并根据反馈调整行为。

这个仓库适合反复研究 `src/email_assistant/`，因为它把 notebook 思路落到了可复用代码里。

### 3. 生产闭环：`langsmith-agent-lifecycle-workshop`

重点看三类内容：

- Agent Development：工具调用、多 agent、supervisor、HITL interrupt。
- Evaluation & Improvement：离线评估、LLM-as-judge、trace metrics、eval-driven development。
- Deployment & Continuous Improvement：LangSmith deployment、online evaluation、annotation queues、数据飞轮。

它的 `deployments/` 目录很值得看，里面包含多种可部署 graph 配置：

- database agent
- docs RAG agent
- SQL agent
- supervisor agent
- supervisor + HITL agent
- supervisor + HITL + SQL 完整系统

### 4. 真实业务应用：`social-media-agent` / `open-swe`

如果关注普通业务 agent，先看 `social-media-agent`：

- 内容抓取与总结。
- 多平台认证。
- human-in-the-loop 审核。
- 定时发布。
- Agent Inbox。
- Slack / GitHub / Supabase 等外部系统集成。

如果关注 coding agent，先看 `open-swe`：

- 异步任务执行。
- sandbox 隔离。
- 子 agent 协作。
- GitHub PR 自动创建。
- Slack / Linear / GitHub 入口。
- Deep Agents 与 LangGraph 的组合方式。

### 5. 产品化界面与部署：`agent-chat-ui` / `deployment-cookbook`

`agent-chat-ui` 适合看：

- Next.js 如何连接 LangGraph Server。
- 如何渲染 streaming message。
- 如何隐藏内部消息。
- 如何渲染 artifacts。
- 本地开发和生产代理认证的差异。

`deployment-cookbook` 适合看：

- Agent Streaming Protocol。
- thread history。
- SSE streaming。
- checkpointer 持久化。
- serverless / multi-instance 下 session 与 run 管理。
- 不同平台部署方式：LangSmith Deployment、Cloudflare、Next.js、SvelteKit、Deno、Nuxt。

## 六、选择建议

按目标选仓库：

| 目标 | 首选 |
| --- | --- |
| 系统学习 LangGraph | `langgraph-101` |
| 学会写真实 agent | `agents-from-scratch` |
| 学企业生产流程 | `langsmith-agent-lifecycle-workshop` |
| 学 RAG | `rag-from-scratch` + `retrieval-agent-template` |
| 学长期记忆 | `memory-template` + `memory-agent` |
| 学多智能体 | `langgraph-101` 的 `multi_agent` + `langgraph-supervisor-py` |
| 学前端接入 | `agent-chat-ui` |
| 学部署 | `deployment-cookbook` |
| 学复杂 coding agent | `open-swe` |
| 学真实业务 agent | `social-media-agent` |

## 七、工时周期与难度评估

### 评估假设

以下估算面向一名有 Python / TypeScript 基础、了解 LLM API 基本调用、
但尚未系统掌握 LangChain / LangGraph 的开发者。时间不包含真实线上账号审批、
公司安全评审、云资源采购、生产监控接入等组织流程。

评估分三档：

- 快速理解：读 README、跑核心 notebook 或浏览关键源码，形成整体认知。
- 本地跑通：配置 API key 和依赖，在本地跑通主要 demo 或核心 graph。
- 可改造为项目模板：能替换模型、工具、数据源、提示词、存储，并形成可复用工程骨架。

难度分五级：

| 难度 | 含义 |
| --- | --- |
| 1 | 入门，按 README 基本能跑。 |
| 2 | 需要理解 LangChain / LangGraph 基础概念。 |
| 3 | 需要理解状态、工具、流式、checkpoint、外部服务。 |
| 4 | 涉及多 agent、HITL、评估、部署或多系统集成。 |
| 5 | 接近生产系统，需要较强工程经验和架构判断。 |

### 仓库级工时评估

| 仓库 | 快速理解 | 本地跑通 | 改造为项目模板 | 难度 | 主要风险点 |
| --- | --- | --- | --- | --- | --- |
| `langgraph-101` | 0.5-1 天 | 1-2 天 | 3-5 天 | 2 | 内容覆盖面广，容易只跑 notebook 但没有抽象出可复用模式。 |
| `agents-from-scratch` | 1 天 | 2-4 天 | 5-8 天 | 3 | Gmail / calendar 集成、HITL、memory、评估链路需要分阶段消化。 |
| `langsmith-agent-lifecycle-workshop` | 1-2 天 | 3-5 天 | 1.5-2 周 | 4 | 覆盖评估、部署、数据飞轮，学习收益高但上下文较多。 |
| `social-media-agent` | 1-2 天 | 3-7 天 | 2-4 周 | 5 | 依赖外部平台认证、发布权限、Slack、Supabase、Agent Inbox 等。 |
| `open-swe` | 2-3 天 | 1-2 周 | 4-8 周 | 5 | coding agent 涉及沙箱、异步任务、GitHub PR、权限与安全边界。 |
| `deployment-cookbook` | 0.5-1 天 | 2-4 天 | 1-2 周 | 4 | 重点不在 agent 逻辑，而在协议、SSE、thread state、持久化和部署平台差异。 |
| `agent-chat-ui` | 0.5 天 | 1-2 天 | 3-7 天 | 3 | 生产化时要处理 API proxy、认证、LangGraph Server 地址与 assistant 配置。 |
| `langgraph-fullstack-python` | 0.5 天 | 1 天 | 2-4 天 | 2 | 适合最小全栈参考，但生产持久化、鉴权、复杂 UI 需要自行补。 |
| `react-agent` | 0.5 天 | 0.5-1 天 | 1-2 天 | 1 | 示例简单，适合学 ReAct，不适合直接代表生产架构。 |
| `rag-from-scratch` | 0.5-1 天 | 1-2 天 | 2-4 天 | 2 | 偏教学 notebook，生产化仍要补数据管道、权限、评估和更新机制。 |
| `retrieval-agent-template` | 0.5-1 天 | 2-4 天 | 5-10 天 | 3 | 向量库选择、索引 schema、用户隔离、召回质量调优是关键。 |
| `data-enrichment` | 0.5-1 天 | 1-3 天 | 4-7 天 | 3 | Web search / extraction 质量不稳定，需要校验、重试和来源追踪。 |
| `memory-template` / `memory-agent` | 0.5-1 天 | 1-2 天 | 3-6 天 | 3 | 记忆写入策略、命名空间设计、误记忆纠正比代码本身更难。 |
| `langgraph-supervisor-py` / `langgraph-swarm-py` | 0.5-1 天 | 1-3 天 | 5-10 天 | 4 | 多 agent 上下文边界、handoff 规则、消息历史裁剪需要反复调试。 |
| `langgraph-bigtool` | 0.5 天 | 1-2 天 | 3-7 天 | 3 | 工具元数据质量、工具检索召回、权限隔离会直接影响效果。 |
| `langchain-nextjs-template` | 0.5-1 天 | 1-2 天 | 3-7 天 | 3 | JS 侧 RAG、Supabase、流式输出和 Vercel 部署需要一起理解。 |

### 学习路线级工期

| 路线 | 目标 | 建议周期 | 产出 |
| --- | --- | --- | --- |
| 快速入门路线 | 理解 LangChain / LangGraph 基本关系，能写简单工具调用 agent。 | 2-3 天 | 跑通 `langgraph-101` 的 101 部分和 `react-agent`。 |
| 进阶应用路线 | 能实现一个带工具、状态、memory、HITL 的业务 agent。 | 1-2 周 | 基于 `agents-from-scratch` 改出自己的 email / CRM / 工单类 agent。 |
| RAG 专项路线 | 能实现可维护的 RAG agent，并理解索引、召回、生成、评估。 | 1 周 | 跑通 `rag-from-scratch`，再改造 `retrieval-agent-template`。 |
| 多智能体路线 | 能设计 supervisor / swarm / sub-agent 协作流程。 | 1-2 周 | 基于 `langgraph-101` 的 `multi_agent` 和 supervisor 示例做一个多角色业务流程。 |
| 生产部署路线 | 能把 agent 接入 UI、持久化线程、支持 streaming，并部署到目标平台。 | 1-2 周 | 跑通 `agent-chat-ui` + `deployment-cookbook` 中一个平台示例。 |
| 企业闭环路线 | 能做评估驱动开发、部署、线上评估、数据闭环。 | 2-3 周 | 完成 `langsmith-agent-lifecycle-workshop` 三个模块，并形成内部项目模板。 |
| 复杂产品路线 | 构建接近真实产品的业务 agent 或 coding agent。 | 4-8 周 | 深挖 `social-media-agent` 或 `open-swe`，完成定制化系统设计。 |

### 按投入产出排序

如果目标是尽快形成可复用能力，建议优先级如下：

1. `langgraph-101`：投入小，覆盖面最大。
2. `agents-from-scratch`：最适合从教学过渡到真实业务 agent。
3. `agent-chat-ui`：最快补齐产品界面短板。
4. `retrieval-agent-template`：RAG 是多数业务场景的高频需求。
5. `langsmith-agent-lifecycle-workshop`：投入较大，但能建立生产闭环意识。
6. `deployment-cookbook`：当准备上线时再重点看，收益最高。
7. `social-media-agent` / `open-swe`：适合做高级案例拆解，不建议作为第一批学习材料。

## 八、官方文档参考

- [LangChain overview](https://docs.langchain.com/oss/python/langchain/overview)
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)
- [LangSmith Deployment](https://docs.langchain.com/langsmith/deployment)
- [LangGraph Application Structure](https://docs.langchain.com/langsmith/application-structure)
- [LangGraph CLI](https://docs.langchain.com/langsmith/cli)
- [Memory overview](https://docs.langchain.com/oss/python/concepts/memory)
