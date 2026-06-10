# LangGraph 学习计划与时间估算

> 背景：多年 Java 开发经验，有 Azure OpenAI、Spring AI 等相关项目经验。
> 整理日期：2026-06-10

## 结论：全职 1–2 周，业余时间 3–4 周左右可以"学完能用"

当前已完成约 **60–70%** 的官方 [langgraph-101](https://github.com/langchain-ai/langgraph-101) 课程，剩下的核心内容不多。

## 当前进度（对照官方 langgraph-101 仓库）

| 模块 | 内容 | 状态 |
|------|------|------|
| 101 基础 | 模型、工具、记忆、流式输出 | ✅ 已完成（01–08 + 技术总结） |
| 102 Middleware | 中间件、human-in-the-loop、护栏 | ✅ 已完成（含总结） |
| 201 email_agent | 有状态的邮件分诊智能体 | ✅ 已完成（含总结） |
| 201 multi_agent | Supervisor 多智能体 + 子智能体 | 🔶 进行中（发票子智能体刚调通） |
| 201 research_agent | 并行子研究员的深度研究智能体 | ❌ 未开始 |
| 201 deepagents | AGENTS.md、skills、长期记忆、HITL | ❌ 未开始 |

## 为什么可以快：Spring AI → LangChain/LangGraph 概念映射

Spring AI + Azure OpenAI 经验意味着概念层面几乎零成本，只需要建立映射：

| Spring AI | LangChain / LangGraph |
|-----------|----------------------|
| `ChatClient` | `init_chat_model` / model 调用 |
| `Advisors` | **middleware**（已学完） |
| `@Tool` / Function Calling | `@tool` 装饰器 |
| `ChatMemory` | **checkpointer / store** |

真正需要消化的是 LangGraph 独有的部分（约占总学习量的 40%）：

- **StateGraph 的图模型**：节点 / 边 / 状态归并（reducer）
- **Persistence / Checkpoint** 机制
- **Interrupt**（human-in-the-loop 的底层实现）
- **Subgraph**（子图组合）

这些在 Spring AI 中没有对应物。

## 建议的时间分配

### 第一阶段：收尾当前仓库（2–3 天，业余约 1 周）

- 完成 `multi_agent`（正在做的发票 supervisor）
- `research_agent`：学并行 fan-out（`Send` API）、map-reduce 模式
- `deepagents`：2025 年后官方主推的方向，值得认真过

### 第二阶段：官方文档核心概念补漏（2–3 天）

- [docs.langchain.com 的 Learn 板块](https://docs.langchain.com/oss/python/learn)
- 重点：Persistence、Streaming、Context Engineering、Graph API vs Functional API
- 已有的练习覆盖了大部分，这一步主要是把"会照着写"变成"理解为什么"

### 第三阶段：一个落地 demo（3–5 天）

- 从官方教程里挑一个贴近工作的：**SQL agent with human-in-the-loop** 或 **RAG agent**，从零写一遍而不是抄
- 如果团队是 Java 栈，可以顺便验证 LangGraph Platform / 部署方式，评估和 Spring 服务的共存方案（比如 LangGraph 做编排服务、Java 做业务网关）

### 可选：LangChain Academy 视频课

[Introduction to LangGraph](https://academy.langchain.com/courses/intro-to-langgraph)（Module 0–6，含部署）。视频课节奏偏慢，建议只挑：

- **Module 4**：map-reduce / subgraph
- **Module 6**：部署

其余用现有的代码练习代替，可省约 1 周时间。

## 一句话总结

**别再扩展"学"的范围，把 201 剩下两个 notebook 做完，然后直接做一个贴近业务的 demo，两周内可以结束战斗。**

最大的成本不是 LangGraph 概念，而是 Python 生态的熟练度（asyncio、typing、包管理），这个只能靠写。

## 参考资料

- [langchain-ai/langgraph-101 (GitHub)](https://github.com/langchain-ai/langgraph-101)
- [Learn — Docs by LangChain](https://docs.langchain.com/oss/python/learn)
- [Foundation: Introduction to LangGraph — LangChain Academy](https://academy.langchain.com/courses/intro-to-langgraph)
- [LangGraph Essentials — LangChain Academy](https://academy.langchain.com/courses/langgraph-essentials-python)
