# deep_agents 阶段总结与下一阶段计划

> 依据：
> - `notebooks/201/deep_agents.py`
> - `notebooks/201/docs/deep_agents_学习路线.md`
> - `notebooks/201/docs/deep_agents_检测薄弱点与标准答案.md`
> - `notebooks/201/docs/deep_agents_backend_速查.md`
> - 上游 `langchain-ai/langgraph-101` 当前 README 与 `agents/deep_agent/` 结构

---

## 一、当前阶段判断

当前已经不是 deep_agents 的入门阶段，而是完成了 **A→E 全路线的
第一次贯通**。

`deep_agents.py` 已经覆盖以下主题：

- Harness：用 `create_deep_agent()` 创建基础 Agent
- 自定义工具：封装 `tavily_search`
- Backends：State / Filesystem / Composite / Store
- 子 Agent：`research_subagent` 与协调 Agent
- Middleware：`@wrap_tool_call` logging 示例
- HITL：`interrupt_on` 与 `Command(resume=...)` 示例
- 长期记忆：`StoreBackend`、多类型记忆、用户作用域记忆
- AGENTS.md：常驻指令
- Skills：LinkedIn 与 Twitter/X 两个按需加载技能
- final agent：研究、写报告、生成社交内容的总装示例

但当前成果更像 **教学脚本 + 复盘资料**，还不是上游仓库里那种
可以通过 LangGraph Studio 直接运行的完整 `agents/deep_agent/`。

上游 `langgraph-101` 的 Deep Agent 形态包含：

- `agents/deep_agent/agent.py`
- `agents/deep_agent/AGENTS.md`
- `agents/deep_agent/skills/linkedin-post/SKILL.md`
- `agents/deep_agent/skills/twitter-post/SKILL.md`
- `langgraph.json` 注册

本地当前还没有这些根级结构，因此下一阶段不应继续横向堆新概念，
而应优先把关键机制验证扎实，并沉淀成可运行 Agent。

---

## 二、已完成内容

### 1. 基础 Agent 与搜索工具

已完成：

- 使用 `create_deep_agent()` 创建基础研究助手
- 通过 `utils.models` 统一导入 `model`
- 封装 `tavily_search` 工具
- 对缺失 `TAVILY_API_KEY` 做显式报错

当前状态：

- 概念已理解
- 代码可作为教学示例继续保留
- 工具 docstring 还可以补充 `Returns:`，提高 schema 质量

### 2. Backends 第一轮学习

已覆盖：

- `StateBackend`
- `FilesystemBackend`
- `StoreBackend`
- `CompositeBackend`
- `virtual_mode=True`
- `checkpointer`、`thread_id`、`namespace` 的区别

已有沉淀：

- `deep_agents_backend_速查.md`
- `deep_agents_检测薄弱点与标准答案.md`

当前状态：

- 概念大体已掌握
- 已通过 final agent 跨 thread 实验证明“路径前缀 → backend 路由”
  的判断规则：`/memories/` 命中 `StoreBackend`，普通文件与通过
  `files` 注入的 AGENTS.md / SKILL.md 在新 thread 中不可见

### 3. 子 Agent 编排

已完成：

- 定义 `research_subagent`
- 用协调 Agent 通过 `task()` 委派研究任务
- 形成“协调者负责规划与综合，子 Agent 负责搜索”的结构

当前状态：

- 和之前 `multi_agent` / `research_agent` 的 supervisor 思路已经能对上
- 这一块不是当前主要风险点

### 4. Middleware 初步实践

已完成：

- 使用 `@wrap_tool_call` 编写 `log_tool_calls`
- 打印工具名、参数和完成状态
- 使用 `ClearToolUsesEdit` 演示上下文编辑
- 对比 `ToolMessage` 清理前后的状态变化

当前状态：

- logging middleware 与上下文管理对照实验均已跑通

### 5. HITL 示例

已写出并验证：

- `interrupt_on` 配置
- `approve` / `edit` / `reject` 决策类型
- `Command(resume={"decisions": ...})` 恢复执行

当前状态：

- 已形成可运行实验
- 已能打印 `write_file` 的 interrupt payload
- 已分别验证 approve、reject、edit 三种决策
- 已验证必须使用同一个 `thread_id` / `config` 恢复执行

### 6. 长期记忆与作用域记忆

已写出：

- `/memories/` 路由到 `StoreBackend`
- semantic / episodic / procedural 三类记忆
- `/memories/user/` 与 `/memories/shared/` 的作用域设计
- Alice / Bob 用户隔离示例

当前状态：

- 概念复盘已经做过
- 生产化风险也已经识别：`user_id` 不能由客户端随便传入
- 仍需用实操补强路径路由判断

### 7. AGENTS.md 与 Skills

已完成：

- 在脚本中构造 `/AGENTS.md`
- 构造 LinkedIn skill
- 构造 Twitter/X skill
- 通过 `memory=["/AGENTS.md"]` 与 `skills=["/skills/"]` 加载

当前状态：

- 已理解“目录常驻、正文按需”的 progressive disclosure
- 但示例中第二次换新 thread 且没有重新传 `files`，正好暴露出
  skills 生命周期问题，需要显式做成验证实验

### 8. final agent 首轮总装

已完成：

- 创建 `final_agent`
- 传入 `AGENTS.md` 与两个 skills
- 执行“研究 LangChain Deep Agents + 写报告 + 写 LinkedIn 帖子”
- 打印虚拟文件系统内容

当前状态：

- 已完成首轮贯通
- 已为 final agent 单独配置 `/memories/` → `StoreBackend` 路由
- 已完成新 thread 不传 `files` 的验证实验：
  `/memories/research_notes.md` 可跨 thread 读取，`/final_report.md`、
  `/AGENTS.md`、`/skills/linkedin-post/SKILL.md` 均不可见
- 已为 `StoreBackend` 补充显式 `namespace`，不再依赖默认命名空间行为

---

## 三、关键问题与风险

### P0：final agent 的长期记忆路由不完整（已完成）

当前 `final_agent` 复用了前面用于 `/workspace/` 的
`composite_backend`：

```python
CompositeBackend(
    default=StateBackend(),
    routes={
        "/workspace/": FilesystemBackend(...),
    },
)
```

但 `AGENTS.md` 要求把关键要点保存到：

```text
/memories/research_notes.md
```

这会导致一个问题：

- `/memories/research_notes.md` 没有命中 `/workspace/`
- 因此会落到 default 的 `StateBackend`
- 结果它只是 thread 内状态，不是真正跨 thread 的长期记忆

处理结果：

- 已在 part09 final agent 中新增独立 `final_backend`
- 已显式增加 `/memories/` → `StoreBackend()` 路由
- 已使用独立 `final_store = InMemoryStore()`，避免与前面教学段落共用
  `store`

验收结果：

> 新 thread 能读取 `/memories/research_notes.md`，说明该路径已经进入
> `StoreBackend`，不再落到默认 `StateBackend`。

### P0：skills 生命周期需要显式验证（已完成）

当前 `skill_agent` 第一次运行时传入了：

```python
"files": skill_files
```

第二次运行换了新 `thread_id`，但没有再次传入 `files`。

根据当前复盘结论：

- `/AGENTS.md` 是通过 `files` 注入 state 的
- `/skills/.../SKILL.md` 也是通过 `files` 注入 state 的
- 新 thread 不重新传 `files`，这些文件就不存在

验证结果：

- 第一次运行通过 `files` 注入 `/AGENTS.md` 与 `/skills/.../SKILL.md`
- 第二次运行使用新的 `thread_id`，且不再传 `files`
- 新 thread 中 `/AGENTS.md`、`/skills/linkedin-post/SKILL.md`、
  `/final_report.md` 均读取失败
- 同一轮验证中 `/memories/research_notes.md` 读取成功

结论：

> `skills=["/skills/"]` 只是告诉 deep agents 从哪里发现 skill 文件，
> 不等于给 `/skills/` 配置持久化 backend。当前 routes 只有
> `/memories/`，因此只有 `/memories/...` 能跨 thread 存活。

### P1：HITL 完整链路已跑通（已完成）

HITL 的关键链路是：

1. 配置 `interrupt_on`
2. 使用 checkpointer
3. invoke 时传入 `thread_id`
4. 捕获 interrupt payload
5. 使用同一个 config 执行 `Command(resume=...)`

验收结果：

- approve：中断后批准 `write_file`，文件成功创建
- reject：中断后拒绝 `write_file`，文件未创建，Agent 能向用户说明结果
- edit：中断后修改 `write_file` 的 `file_path` 与 `content`，最终写入
  `/edited_test.md`
- 三种决策均使用同一个 `config` / `thread_id` 执行
  `Command(resume=...)`

结论：

> HITL 的核心不是“让 Agent 问一句用户”，而是将工具调用挂起，
> 由人工审核工具名与参数后，再用同一个 checkpoint 线程恢复执行。

### P1：Studio 可运行形态（暂时废弃）

当前本地项目是 notebook/script 学习结构。

如果要对齐上游 `langgraph-101`，原计划下一步应补：

- `agents/deep_agent/agent.py`
- `agents/deep_agent/AGENTS.md`
- `agents/deep_agent/skills/linkedin-post/SKILL.md`
- `agents/deep_agent/skills/twitter-post/SKILL.md`
- `langgraph.json`

这一步的意义原本是：

- 从“脚本学习”进入“可运行 Agent 工程”
- 可以用 LangGraph Studio 观察状态、工具调用、中断和 memory
- 更接近真实生产工作流

当前决策：

> 暂时废弃 Studio 版落地，不再作为下一阶段推进项。原因是本阶段目标
> 已经通过 notebook/script 完成核心机制验证，继续引入 LangGraph CLI、
> `langgraph.json`、LangSmith Studio 账号与本地 Agent Server 会扩大
> 工程范围，偏离当前“先钉死核心机制”的学习目标。

### P1：`StoreBackend` 已补显式 `namespace`（已完成）

当前基础 `/memories/` 路由已经从隐式命名空间改为显式命名空间：

```python
StoreBackend(
    namespace=lambda runtime: (
        "deep_agents",
        "basic_memory",
        "memories",
    )
)
```

验收结果：

> `StoreBackend` 不再依赖 deepagents 0.7.0 的默认 namespace 行为。

### P2：Middleware logging 与上下文管理对照已完成（已完成）

路线文档中 Middleware 是最密的硬概念岛。

已完成：

- 工具调用日志 middleware：已能打印 `tavily_search` 与 `write_file`
  的工具名和参数
- 上下文编辑实验：已能看到旧 `ToolMessage` 被替换为 `[cleared]`，
  最新工具结果被保留
- 对照结论：middleware 改的是进入模型前的 `messages`，不是 backend、
  store 或工具本身

仍可后续扩展：

- 对话摘要或上下文压缩实验
- 去掉 middleware 后再跑一次真实 Agent，对比完整 trace 差异

### P2：脚本工程质量需要清理

当前 `deep_agents.py` 是学习草稿形态，存在：

- 重复 import（已清理）
- 未使用 import（已清理）
- import 分组不规范（已清理）
- Tavily 搜索工具在全局初始化时强依赖 `TAVILY_API_KEY`（已改为工具调用时懒初始化）
- HITL 实验混入搜索工具与子 Agent 依赖（已收敛为纯文件写入审核实验）
- 大量注释代码与可运行代码混在一起
- 多个阶段共享变量，容易误用旧 backend / store / config

作为学习草稿可以接受；如果要长期维护，下一步应继续拆成更清晰的
教学段落或独立函数。

---

## 四、下一阶段学习目标

### 目标 1：修正长期记忆 mental model（已完成）

已完成的实验：

1. 为 final agent 创建新的 backend：

```python
CompositeBackend(
    default=StateBackend(),
    routes={
        "/memories/": StoreBackend(),
    },
)
```

2. 运行 final agent，让它写：

```text
/final_report.md
/memories/research_notes.md
```

3. 开新 thread，不传 `files`。
4. 验证：

- `/memories/research_notes.md` 仍能读到
- `/final_report.md` 读不到
- `/AGENTS.md` 和 SKILL.md 也读不到，除非重新传 `files`

学习目标：

> 路径前缀决定文件命运，与文件“身份”无关。

验收结论：

- `/memories/research_notes.md` → 命中 `StoreBackend`，新 thread 可读
- `/final_report.md` → 默认 `StateBackend`，新 thread 不可读
- `/AGENTS.md` 与 SKILL.md → 通过 `files` 注入当前 thread，
  新 thread 不重新传 `files` 时不可读

### 目标 2：补齐 HITL 实操（已完成）

已完成的实验：

1. 配置：

```python
interrupt_on={
    "write_file": True,
    "edit_file": True,
}
```

当前实验用 `True` 跑通，因此 interrupt payload 中会包含
`approve` / `edit` / `reject` / `respond`。如果要与本节只验证
approve / reject / edit 的目标严格对齐，后续可改成显式
`allowed_decisions` 配置。

2. 触发写文件操作。
3. 打印 interrupt payload：

- tool name
- args
- allowed decisions

4. 分别验证：

- approve：继续写入，文件创建成功
- reject：拒绝写入，文件未创建
- edit：修改工具参数后继续，最终写入 `/edited_test.md`

学习目标：

> HITL 的本质是“暂停执行 → 人审工具调用 → 用同一个 thread 恢复”。

验收结论：

- 已能打印 `write_file` 的 interrupt payload
- 已能看到原始工具参数 `/test.md` 与 `Hello World`
- 已能使用同一个 `config` / `thread_id` resume
- 已分别跑通 approve、reject、edit 三类决策

### 目标 3：沉淀 Studio 版 Deep Agent（暂时废弃）

原目标结构：

```text
agents/
  deep_agent/
    agent.py
    AGENTS.md
    skills/
      linkedin-post/
        SKILL.md
      twitter-post/
        SKILL.md
langgraph.json
```

原关键要求：

- `agent.py` 中只保留 Agent 定义，不写教学打印逻辑
- `AGENTS.md` 作为真实常驻指令文件
- skills 作为真实文件，而不是运行时 `files` 注入
- `/memories/` 使用 `StoreBackend`
- 文件写入使用 HITL
- 提示词与 docstring 保持中文为主

学习目标：

> 从 notebook/script 示例迁移到可运行 Agent 工程。

当前决策：

> 本目标暂时废弃，不再进入下一轮执行。后续如果重新需要 Studio
> 调试能力，再单独恢复该目标，并先补齐 `langgraph-cli[inmem]`、
> `langgraph.json`、LangSmith 配置与可导入的 `agent` 入口。

### 目标 4：补 Middleware 对照实验（已完成）

已完成的内容：

- logging middleware：观察工具调用
- context editing：观察 `ToolMessage` 清理前后的变化
- 明确对照结论：middleware 影响的是进入模型前的 `messages`

学习目标：

> 不只知道 middleware 能加，而是能说清它改变了哪一层信息流。

验收结论：

- `log_tool_calls` 已打印 `tavily_search` 与 `write_file` 的调用参数
- `ClearToolUsesEdit(trigger=1, keep=1)` 已将旧工具结果清理为 `[cleared]`
- 最新工具结果保留，证明上下文编辑策略按预期生效

### 目标 5：更新复盘资料（部分完成）

建议更新：

- `deep_agents_学习路线.md`：已标记 A→E 首轮完成，并补充当前验收状态与下一轮复习路线
- `deep_agents_检测薄弱点与标准答案.md`：暂不改动，保留原检测题版本
- 新增或生成 `deep_agents_技术总结.md`

学习目标：

> 让阶段性学习成果可复习、可检测、可迁移。

---

## 五、优先级列表

| 优先级 | 事项 | 原因 | 验收标准 |
| --- | --- | --- | --- |
| P0（已完成） | 修正 `/memories/` → `StoreBackend` 路由 | 原最大概念风险 | 新 thread 已能读 `/memories/research_notes.md` |
| P0（已完成） | 验证新 thread 不传 `files` 时 skills 不存在 | 对应 AGENTS.md / skills 生命周期 | 已能解释 `/AGENTS.md`、SKILL.md、`/final_report.md` 谁能跨 thread 存活 |
| P1（已完成） | 跑通 HITL approve / reject / edit / resume | Deep Agents 生产工作流核心能力 | 已能打印 interrupt payload，并用同一 config resume |
| P1（暂时废弃） | 搭建 `agents/deep_agent/` Studio 版 | 需要引入 LangGraph CLI / Studio 工程形态，当前阶段暂不推进 | 不验收 |
| P1（已完成） | 为 `StoreBackend` 补显式 `namespace` | 消除 deepagents 0.7.0 弃用风险 | 已改为显式 namespace，不再依赖默认行为 |
| P2（已完成） | 补 Middleware 上下文管理实验 | 路线中最密的硬概念岛 | 已能对比旧 `ToolMessage` 清理前后状态变化 |
| P2（部分完成） | 清理 `deep_agents.py` import 与结构 | 降低复习和维护成本 | import 已清理，阶段结构仍待继续整理 |
| P3（部分完成） | 更新总结、路线、检测题 | 固化学习成果 | 学习路线已更新，技术总结待生成，检测题暂不改动 |

---

## 六、建议执行顺序

当前推荐按以下顺序继续推进：

1. 整理 `deep_agents.py` 中已验收实验的结构，降低复习成本。
2. 生成 `deep_agents_技术总结.md`，沉淀可复习、可迁移的技术总结。

不要同时推进太多概念。下一阶段的核心不是“学更多”，而是把以下剩余事项钉死：

- `deep_agents.py` 中已验收实验的结构化整理
- `deep_agents_技术总结.md` 的生成与校对

---

## 七、一句话总结

当前已经完成 deep_agents 的**首轮贯通**。

P0 的 `/memories/` 路由、skills / AGENTS.md 生命周期，P1 的 HITL
resume 与 `StoreBackend` namespace，以及 P2 的 Middleware 对照实验
已经通过实验验收。Studio 版 Deep Agent 暂时废弃，下一阶段重点转向
整理教学脚本并生成技术总结。
