---
name: tech-summary
description: Use when generating a Chinese 技术总结 (technical summary) markdown doc from a LangGraph learning module .py in this repo (e.g. "给 multi_agent.py 写技术总结", "generate tech summary", "总结这个脚本的知识点"). Produces a doc matching the established email_agent_技术总结.md format — 引言 + 目录 + 全局架构总览 + 分部分知识点 + mermaid 架构图 + 总结要点.
---

# 代码→技术总结 (tech-summary)

读一个学习模块 `.py`，产出一份与 `notebooks/201/docs/email_agent_技术总结.md` **同构**的中文技术总结。读者是正在学 LangGraph 的开发者，目标是「看文档就能复盘整个脚本的知识点与设计意图」。

## 先确认

1. **目标脚本**：哪个 `.py`（如 `notebooks/201/multi_agent.py`）。
2. **输出位置**：沿用该系列已有约定——
   - `101/` 系列 → 与脚本同目录，命名 `<原名>_技术总结.md`（参考 `101_langchain_langgraph_技术总结.md`、`102_middleware_技术总结.md`）。
   - `201/` 系列 → 放 `201/docs/`，命名 `<原名>_技术总结.md`（参考 `docs/email_agent_技术总结.md`）。
   - 不确定时按以上规则推断，并在动手前告知用户最终路径。

## 必须复刻的文档骨架（来自 email_agent_技术总结.md）

1. **标题**：`# <文件名>.py 技术知识点总结`
2. **引言 blockquote**：一句话概括脚本主线 + 「全文共 N 个部分，层层叠加/并列」之类的结构说明。
3. **目录**：用锚点链接列出「全局架构总览 → 各部分 → 总结」。
4. **全局架构总览**：
   - 一段 `mermaid flowchart` 展示各部分关系（递进就 `-->` 串联，并列就分支）。
   - 「贯穿全文的核心组件」表格：`| 组件 | 代码位置（第 X 行） | 作用 |`。
   - 关键 `State` 设计代码块 + reducer 说明。
5. **每个 `print("---0X---")` 分段 = 一个 `## 第 0X 部分：xxx`**，内部固定含：
   - `> 对应代码：第 a-b 行`
   - `### 知识点`：**编号列表**，每条点出 API/设计 + 关键行号 + 为什么这么做（踩坑/意图）。
   - 一段 `mermaid` 架构图或业务流程图。
   - 若该部分有导出的 PNG（`docs/image/0X_*.png` 等），用 `![..](image/..png)` 引用；没有就省略。
   - 视情况加 `### 业务流程` / 对比表（`| 维度 | 方案A | 方案B |`）。
6. **`## 总结：设计主线与工程要点`**：
   - 「演进主线」`mermaid flowchart LR` 串起各部分。
   - 「最值得记住的 N 个工程要点」编号列表。
7. **`## 附：用 LangGraph 导出真实流程图`**（若脚本/目录有导图脚本）：给出运行命令与 `draw_mermaid_png()` 核心 API。

## 写作要求

- **全中文**，技术名词（`add_messages` / `interrupt` / `checkpointer` / `create_agent` 等）保留英文原样。
- **行号要真实**：基于当前脚本内容标注，不要照搬样板里的行号。
- 解释「**为什么**」而非仅「是什么」——样板里大量「兜底 / 伏笔 / 从纠正中学习」式的设计意图说明，是这份文档的灵魂，要保留这种深度。
- mermaid 图要能真实反映脚本里的 node/edge/条件路由拓扑。

## 工作步骤

1. 完整读目标 `.py`，按 `print("---0X---")` 切分部分。
2. 逐部分提炼知识点、行号、设计意图，画对应 mermaid 图。
3. 按上面骨架组装，写到约定路径。
4. 若发现脚本有 bug 或可疑写法（如样板里点出的 `Path()` 漏 `__file__`、import 路径不一致），在对应部分如实标注，不要粉饰。

## 完成后

如该模块的总结值得做成图文卡片，可提醒用户用 `/cards-from-summary`。
