# deep_agents 学习路线与分阶段规划

> 对象：`notebooks/201/deep_agents.ipynb`（官方教程，使用 `deepagents` 框架）
> 目的：分阶段啃完，**避免重蹈 research_agent 那种「代码撸完、整个人懵逼」**。
> 配套：本仓库 `docs/LangChain-LangGraph-学习方法与心得.md`（四步闭环法 + 低层↔高层对照表）。
> 当前状态：A→E 首轮已经完成，P0 / P1 / Middleware 关键机制已通过实验验收。

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
| 0 | 安装 / 模型初始化（需模型 key + Tavily key） | 🟢 | 配置，已完成 |
| 1 | `create_deep_agent()` 跑起第一个 Agent（自带文件系统/规划/子Agent） | 🟢 | 已完成 |
| 2 | 加自定义工具（`@tool` + Tavily 搜索） | 🟢 | 已完成 |
| 3 | **Backends**：状态存哪、4 种后端、路径路由、沙箱 `virtual_mode` | 🔴 | 已完成，路径路由已补实验 |
| 4 | 加研究子 Agent（`subagents=` / `task()`） | 🟢 | 已完成 |
| 5 | **Middleware 深入**：自动上下文管理、`@wrap_tool_call` 装饰器组合 | 🔴🔴 | 已完成，logging + context editing 已验收 |
| 6 | HITL（`interrupt_on` / approve-edit-reject / `Command(resume)`） | 🟡 | 已完成，approve / reject / edit 已验收 |
| 7 | **长期记忆**：CompositeBackend 多路由、namespace 隔离、3 类记忆 | 🔴 | 已完成，`StoreBackend namespace` 已显式化 |
| 8 | AGENTS.md & Skills（渐进式披露、自我改写指令、`skills=`） | 🟡 | 已完成，生命周期已验证 |
| 9 | 完整研究 Agent（总装，无新概念） | 🟢 | 已完成，final agent 首轮贯通 |
| 10 | Next Steps（纯文字） | 🟢 | Studio 版暂时废弃 |

> 一句话：🟢 部分（0,1,2,4,9）能很快乐地跑通；真正花时间的是 **3、5、7 三个红色概念岛**。

### 当前验收状态（2026-07-07）

| 事项 | 状态 | 验收结果 |
| --- | --- | --- |
| `/memories/` → `StoreBackend` 路由 | 已完成 | 新 thread 能读取 `/memories/research_notes.md` |
| skills / AGENTS.md 生命周期 | 已完成 | 新 thread 不传 `files` 时 `/AGENTS.md`、SKILL.md、`/final_report.md` 均不可见 |
| `StoreBackend namespace` | 已完成 | 已改为显式 namespace，不再依赖默认行为 |
| HITL approve / reject / edit / resume | 已完成 | 已打印 interrupt payload，并用同一 config resume |
| Middleware logging | 已完成 | 已打印 `tavily_search` / `write_file` 工具名与参数 |
| Middleware context editing | 已完成 | 旧 `ToolMessage` 被清为 `[cleared]`，最新工具结果保留 |
| Studio 版 `agents/deep_agent/` | 暂时废弃 | 暂不引入 LangGraph CLI / Studio 工程形态 |

### 难度/新颖度排序

**真正硬 / 新的概念：**
1. **Part 3 Backends** —— 路径路由、namespace 隔离、`virtual_mode` 沙箱
2. **Part 5 Middleware** —— 自动上下文管理、装饰器组合、卸载策略取舍（最密）
3. **Part 7 长期记忆** —— 多路由 CompositeBackend、namespace lambda 做用户隔离
4. **Part 8 Skills** —— 渐进式披露、可自我改写的 AGENTS.md

**轻松 / 直接的用法：** Part 1（基础 `create_deep_agent`）、Part 2（`@tool`）、Part 4（子 Agent 委派）、Part 6（HITL 中断/恢复）。

---

## 三、分阶段时间表（必须分阶段，别一口闷）

按「闭环学习法」（要复述 + 改造，不是跑通就走）估算，原计划
**总计约 11–14 小时**，拆成 **5 个 session**。当前 A→E 首轮已完成，
后续重点从“继续推进新概念”转为“复盘、整理、迁移”。

| 阶段 | 覆盖 Part | 目标产物 | 预估 |
| --- | --- | --- | --- |
| **A. 先尝甜头** | 0,1,2,4 | 一个能联网搜索 + 会派子 Agent 的研究 Agent，跑通并能讲清每个参数 | 已完成 |
| **B. 啃后端** | 3 | 能说清「StateBackend vs StoreBackend vs Composite」分别把文件存哪 | 已完成 |
| **C. 啃中间件** | 5 | 能讲清 context editing 改的是进入模型前的 `messages` | 已完成 |
| **D. 记忆 + HITL** | 6,7 | 能跑通长期记忆路由 + HITL approve / reject / edit / resume | 已完成 |
| **E. 收尾** | 8,9 | Skills 机制 + 完整 Agent 总装跑一遍 | 已完成 |

> 节奏建议：**一天最多推进一个红色阶段（B/C/D）**。红色概念岛硬塞会直接复刻 research_agent 的懵逼。

---

## 四、下一轮复习路线

下一轮不再横向堆新概念，重点是把已经跑通的机制讲清楚、拆干净、迁移出去。

| 顺序 | 事项 | 目标产物 |
| --- | --- | --- |
| 1 | 整理 `deep_agents.py` 中已验收实验的运行边界 | 默认只跑必要演示，慢调用用注释作为手动开关 |
| 2 | 生成 `deep_agents_技术总结.md` | 一份可复习、可迁移的中文技术总结 |
| 3 | 回看 `deep_agents_backend_速查.md` | 确认 Store / State / Composite / namespace 心智模型一致 |
| 4 | 如有需要，再恢复 Studio 版目标 | 先补齐 LangGraph CLI、`langgraph.json`、可导入 `agent` 入口 |

---

## 五、针对 deep_agents 的「防懵逼」三条铁律

1. **每个参数都回链底层**：`create_deep_agent()` 每传一个参数（`subagents=` / `backend=` / `middleware=`），就问一句「这玩意儿 research_agent 里是怎么手搓的？」——用 `docs/LangChain-LangGraph-学习方法与心得.md` 第十节的「低层↔高层对照表」边学边查。
2. **一次一个概念岛**：Part 3、5、7 之间**互相独立**，别交叉学。当天只啃一个红的，啃完用四步法复述 + 改造再走。
3. **改造验证**：每个 Part 别只跑官方 demo——去掉一个 middleware、换一种 backend、改一个 namespace，**预测结果再跑**。这是 deep_agents 里检验「真懂」的唯一硬标准。

---

## 六、结论

> A→E 首轮已经完成。当前不再需要继续横向扩概念，重点转向复盘和沉淀：
> 保留脚本中的教学开关，补齐技术总结，并反复确认路径路由、namespace、
> HITL resume、Middleware context editing 这四个关键心智模型。

### 前置条件提醒
- 当前项目统一从 `utils.models` 导入模型，密钥通过 `.env` 注入。
- `TAVILY_API_KEY` 只在调用 `tavily_search` 时需要；只跑本地 HITL 或
  context editing 演示时不应被 Tavily 阻塞。
