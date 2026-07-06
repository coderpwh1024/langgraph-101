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
- 残留风险集中在“路径前缀 → backend 路由”的条件反射还不够稳

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

当前状态：

- 只完成了自定义 logging middleware
- 尚未完成“自动上下文管理”的对照实验

### 5. HITL 示例

已写出：

- `interrupt_on` 配置
- `approve` / `edit` / `reject` 决策类型
- `Command(resume={"decisions": ...})` 恢复执行

当前状态：

- 代码块大多仍是注释状态
- 还没有形成稳定的可运行实验
- 需要验证“同一个 thread_id 恢复执行”的完整链路

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
- 但长期记忆路由仍需修正和验证

---

## 三、关键问题与风险

### P0：final agent 的长期记忆路由不完整

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

结论：

> final agent 必须显式增加 `/memories/` → `StoreBackend()` 路由。

### P0：skills 生命周期需要显式验证

当前 `skill_agent` 第一次运行时传入了：

```python
"files": skill_files
```

第二次运行换了新 `thread_id`，但没有再次传入 `files`。

根据当前复盘结论：

- `/AGENTS.md` 是通过 `files` 注入 state 的
- `/skills/.../SKILL.md` 也是通过 `files` 注入 state 的
- 新 thread 不重新传 `files`，这些文件就不存在

这不是 bug，而是非常适合做成教学实验：

> 同一个 thread 能继续读 state；新 thread 不传 files 时，skills 不会自动存在。

### P1：HITL 还没有完整跑通

HITL 的关键链路是：

1. 配置 `interrupt_on`
2. 使用 checkpointer
3. invoke 时传入 `thread_id`
4. 捕获 interrupt payload
5. 使用同一个 config 执行 `Command(resume=...)`

当前脚本已有代码雏形，但还缺少一次完整、稳定、可复现的实验。

### P1：还缺 Studio 可运行形态

当前本地项目是 notebook/script 学习结构。

如果要对齐上游 `langgraph-101`，下一步应补：

- `agents/deep_agent/agent.py`
- `agents/deep_agent/AGENTS.md`
- `agents/deep_agent/skills/linkedin-post/SKILL.md`
- `agents/deep_agent/skills/twitter-post/SKILL.md`
- `langgraph.json`

这一步的意义：

- 从“脚本学习”进入“可运行 Agent 工程”
- 可以用 LangGraph Studio 观察状态、工具调用、中断和 memory
- 更接近真实生产工作流

### P2：Middleware 只完成了 logging，缺少上下文管理对照

路线文档中 Middleware 是最密的硬概念岛。

当前只完成：

- 工具调用日志 middleware

还缺：

- 自动上下文管理的输入/输出卸载实验
- 对话摘要或上下文压缩实验
- middleware 前后状态差异对比

### P2：脚本工程质量需要清理

当前 `deep_agents.py` 是学习草稿形态，存在：

- 重复 import
- 未使用 import
- import 分组不规范
- 大量注释代码与可运行代码混在一起
- 多个阶段共享变量，容易误用旧 backend / store / config

作为学习草稿可以接受；如果要长期维护，应拆成更清晰的教学段落或独立函数。

---

## 四、下一阶段学习目标

### 目标 1：修正长期记忆 mental model

要完成的实验：

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

### 目标 2：补齐 HITL 实操

要完成的实验：

1. 配置：

```python
interrupt_on={
    "write_file": True,
    "edit_file": True,
}
```

2. 触发写文件操作。
3. 打印 interrupt payload：

- tool name
- args
- allowed decisions

4. 分别验证：

- approve：继续写入
- reject：拒绝写入，并观察 agent 如何响应
- edit：修改工具参数后继续

学习目标：

> HITL 的本质是“暂停执行 → 人审工具调用 → 用同一个 thread 恢复”。

### 目标 3：沉淀 Studio 版 Deep Agent

目标结构：

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

关键要求：

- `agent.py` 中只保留 Agent 定义，不写教学打印逻辑
- `AGENTS.md` 作为真实常驻指令文件
- skills 作为真实文件，而不是运行时 `files` 注入
- `/memories/` 使用 `StoreBackend`
- 文件写入使用 HITL
- 提示词与 docstring 保持中文为主

学习目标：

> 从 notebook/script 示例迁移到可运行 Agent 工程。

### 目标 4：补 Middleware 对照实验

要补的内容：

- logging middleware：观察工具调用
- 上下文卸载或摘要 middleware：观察 messages / files / todos 的变化
- 去掉 middleware 后再跑一次，对比差异

学习目标：

> 不只知道 middleware 能加，而是能说清它改变了哪一层信息流。

### 目标 5：更新复盘资料

建议更新：

- `deep_agents_学习路线.md`：标记 A→E 首轮已完成
- `deep_agents_检测薄弱点与标准答案.md`：加入新的跨 thread 验证题
- 新增或生成 `deep_agents_技术总结.md`

学习目标：

> 让阶段性学习成果可复习、可检测、可迁移。

---

## 五、优先级列表

| 优先级 | 事项 | 原因 | 验收标准 |
| --- | --- | --- | --- |
| P0 | 修正 `/memories/` → `StoreBackend` 路由 | 当前最大概念风险 | 新 thread 能读 `/memories/research_notes.md` |
| P0 | 验证新 thread 不传 `files` 时 skills 不存在 | 对应 AGENTS.md / skills 生命周期 | 能解释 `/AGENTS.md`、SKILL.md、`/final_report.md` 谁能跨 thread 存活 |
| P1 | 跑通 HITL approve / reject / edit / resume | Deep Agents 生产工作流核心能力 | 能打印 interrupt payload，并用同一 config resume |
| P1 | 搭建 `agents/deep_agent/` Studio 版 | 对齐官方项目形态 | `langgraph dev` 能加载 deep agent |
| P2 | 补 Middleware 上下文管理实验 | 路线中最密的硬概念岛 | 能对比 middleware 前后状态变化 |
| P2 | 清理 `deep_agents.py` import 与结构 | 降低复习和维护成本 | import 合规，阶段边界清晰 |
| P3 | 更新总结、路线、检测题 | 固化学习成果 | 文档能指导下一轮自测 |

---

## 六、建议执行顺序

推荐按以下顺序推进：

1. 先修 final agent 的 `/memories/` 路由。
2. 做跨 thread 验证实验。
3. 把这个实验结果补进薄弱点文档。
4. 跑通 HITL 完整链路。
5. 抽出 `agents/deep_agent/` Studio 版。
6. 最后再整理 `deep_agents.py` 和 Middleware 对照实验。

不要同时推进太多概念。下一阶段的核心不是“学更多”，而是把以下三件事钉死：

- `/memories/` 的 backend 路由
- skills / AGENTS.md 的生命周期
- HITL 的 interrupt / resume 流程

---

## 七、一句话总结

当前已经完成 deep_agents 的**首轮贯通**。

下一阶段的重点不是继续横向加新概念，而是优先把
`/memories/` 路由、skills 生命周期、HITL resume 三件事用实验验证清楚，
然后沉淀成一个可在 LangGraph Studio 中运行的完整 Deep Agent。
