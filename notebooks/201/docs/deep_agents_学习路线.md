# deep_agents 学习路线与分阶段规划

> 对象：`notebooks/201/deep_agents.ipynb`（官方教程，使用 `deepagents` 框架）
> 目的：分阶段啃完，**避免重蹈 research_agent 那种「代码撸完、整个人懵逼」**。
> 配套：本仓库 `docs/LangChain-LangGraph-学习方法与心得.md`（四步闭环法 + 低层↔高层对照表）。

---

## 一、它和 research_agent 的「懵逼来源」不一样

先建立判断，这决定了怎么学：

- **research_agent 的懵逼 = 深度**：一张缠绕的图，`Command` / reducer / 嵌套子图 / 并行拧在一起，**一个东西很绕**。
- **deep_agents 的懵逼 = 广度**：`create_deep_agent()` 一个函数就能跑，但背后**塞了一堆概念**（backends / middleware / memory 路由 / skills）。危险是「我传了 6 个参数它就跑了，但每个参数干嘛我说不清」。

> 应对手法不同：deep_agents 不需要死磕图机制，而需要**一次只啃一个概念岛，别想一口气把 4 个硬概念全装进脑子**。

---

## 二、内容地图（按难度标注）

| Part | 内容 | 难度 | 性质 |
| --- | --- | --- | --- |
| 0 | 安装 / 模型初始化（需 Anthropic + Tavily key） | 🟢 | 配置 |
| 1 | `create_deep_agent()` 跑起第一个 Agent（自带文件系统/规划/子Agent） | 🟢 | **能跑通的快乐** |
| 2 | 加自定义工具（`@tool` + Tavily 搜索） | 🟢 | 已会（research_agent 见过） |
| 3 | **Backends**：状态存哪、4 种后端、路径路由、沙箱 `virtual_mode` | 🔴 | **硬概念岛 ①** |
| 4 | 加研究子 Agent（`subagents=` / `task()`） | 🟢 | 已会（= supervisor 派活） |
| 5 | **Middleware 深入**：自动上下文管理、`@wrap_tool_call` 装饰器组合 | 🔴🔴 | **最密的硬概念岛 ②** |
| 6 | HITL（`interrupt_on` / approve-edit-reject / `Command(resume)`） | 🟡 | research_agent Part 3 同源 |
| 7 | **长期记忆**：CompositeBackend 多路由、namespace 隔离、3 类记忆 | 🔴 | **硬概念岛 ③（代码最多）** |
| 8 | AGENTS.md & Skills（渐进式披露、自我改写指令、`skills=`） | 🟡 | 新颖但不绕 |
| 9 | 完整研究 Agent（总装，无新概念） | 🟢 | 收尾 |
| 10 | Next Steps（纯文字） | 🟢 | 链接 |

> 一句话：🟢 部分（0,1,2,4,9）能很快乐地跑通；真正花时间的是 **3、5、7 三个红色概念岛**。

### 难度/新颖度排序

**真正硬 / 新的概念：**
1. **Part 3 Backends** —— 路径路由、namespace 隔离、`virtual_mode` 沙箱
2. **Part 5 Middleware** —— 自动上下文管理、装饰器组合、卸载策略取舍（最密）
3. **Part 7 长期记忆** —— 多路由 CompositeBackend、namespace lambda 做用户隔离
4. **Part 8 Skills** —— 渐进式披露、可自我改写的 AGENTS.md

**轻松 / 直接的用法：** Part 1（基础 `create_deep_agent`）、Part 2（`@tool`）、Part 4（子 Agent 委派）、Part 6（HITL 中断/恢复）。

---

## 三、分阶段时间表（必须分阶段，别一口闷）

按「闭环学习法」（要复述 + 改造，不是跑通就走）估算，**总计约 11–14 小时**，建议拆成 **5 个 session**，每个 session 结束都有一个「能跑通 + 能讲清」的落地物：

| 阶段 | 覆盖 Part | 目标产物 | 预估 |
| --- | --- | --- | --- |
| **A. 先尝甜头** | 0,1,2,4 | 一个能联网搜索 + 会派子 Agent 的研究 Agent，跑通并能讲清每个参数 | 2–3h |
| **B. 啃后端** | 3 | 能说清「StateBackend vs StoreBackend vs Composite」分别把文件存哪 | 2–2.5h |
| **C. 啃中间件** | 5 | 能讲清「自动上下文管理」三招（卸载输入/卸载结果/对话摘要）+ 写一个自定义 logging middleware | 2.5–3h |
| **D. 记忆 + HITL** | 6,7 | 能跑通「按 user 隔离的长期记忆」+ 中断审批流 | 3–3.5h |
| **E. 收尾** | 8,9 | Skills 机制 + 完整 Agent 总装跑一遍 | 1.5–2h |

> 节奏建议：**一天最多推进一个红色阶段（B/C/D）**。红色概念岛硬塞会直接复刻 research_agent 的懵逼。

---

## 四、针对 deep_agents 的「防懵逼」三条铁律

1. **每个参数都回链底层**：`create_deep_agent()` 每传一个参数（`subagents=` / `backend=` / `middleware=`），就问一句「这玩意儿 research_agent 里是怎么手搓的？」——用 `docs/LangChain-LangGraph-学习方法与心得.md` 第十节的「低层↔高层对照表」边学边查。
2. **一次一个概念岛**：Part 3、5、7 之间**互相独立**，别交叉学。当天只啃一个红的，啃完用四步法复述 + 改造再走。
3. **改造验证**：每个 Part 别只跑官方 demo——去掉一个 middleware、换一种 backend、改一个 namespace，**预测结果再跑**。这是 deep_agents 里检验「真懂」的唯一硬标准。

---

## 五、结论

> **必须分阶段**，按 A→E 走，约 11–14 小时 / 5 个 session。
> 阶段 A（2–3h）就能拿到一个完整能用的 Agent，先建立成就感，
> 再逐个攻克 Part 3、5、7 三个硬概念岛。
> 这样不会再出现「代码撸完整个人是懵的」。

### 前置条件提醒
- 需要 **Anthropic API key**（模型）与 **Tavily API key**（联网搜索，Part 2 起真正使用）。
- 建议先确认这两个 key 已就绪，再开始阶段 A，避免卡在环境上。
