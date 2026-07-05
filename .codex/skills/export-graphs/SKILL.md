---
name: export-graphs
description: Use when (re)generating the LangGraph topology PNGs for a learning module in this repo (e.g. "刷新图", "导出/重画流程图 PNG", "regenerate the graph diagrams", "改完图后更新 png"). Runs a bundled, deterministic export engine that rebuilds graph topology from stub nodes — zero LLM calls, zero API cost — and falls back to .mmd source when offline.
---

# 图可视化导出 (export-graphs)

把编译后的 LangGraph 图导出成 PNG 流程图，刷新各模块 `docs/image/*.png`、`*_graph.png`。这是**脚本型** skill：真正干活的是捆绑脚本 `scripts/export_graphs.py`，本文件只负责告诉你何时用、怎么调。

## 核心原理（务必遵守，否则会烧钱）

`draw_mermaid_png()` 只需要图的**拓扑**（节点 + 边），**不执行任何节点**。所以导图**绝不能**直接 import 学习脚本本身（`email_agent.py` / `multi_agent.py` 等会在顶层 `invoke()`，触发 LLM 调用 + 联网下数据）。正确做法是用「**桩节点重建拓扑**」的 builder 模块——节点函数全是占位空实现，只保留 `add_node` / `add_edge` / 条件路由结构。参考已验证的范例 `notebooks/201/docs/export_graphs.py`。

联网渲染走 mermaid.ink，失败时引擎自动回退导出 `.mmd` 源码，离线也能用。

## 用法

引擎用 `${CLAUDE_SKILL_DIR}` 定位，与安装层级无关：

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/export_graphs.py <builder.py> [out_dir] [--xray]
```

引擎导入 `<builder.py>`（执行其顶层代码，由 builder 自己注入 sys.path），再按优先级发现要导出的编译图：

1. `build_exports()` 函数 → 返回 `{文件名: graph 或 (graph, xray)}`（**推荐**，可精确控制文件名与 xray）
2. `EXPORTS` 字典 → 同上
3. 模块级编译图变量 → 变量名即文件名

`out_dir` 缺省为 builder 同级的 `image/`。

## 工作步骤

1. **确认目标模块**与要刷新的图。
2. **判断 builder 是否已存在**：
   - 该模块已有桩重建脚本（如 `201/docs/export_graphs.py`）→ 直接跑它，或给它补一个 `build_exports()` 后用本引擎驱动。
   - 没有 → 仿照 `201/docs/export_graphs.py` 写一个桩 builder：拷贝原脚本的 `State` / 工具 / `add_node`·`add_edge`·条件路由拓扑，节点函数换成空实现（`def node(state): return {}`），**不要保留任何 `invoke()`**。子图（如 `email_agent` 挂到 hitl 上）导出时记得 `xray=True` 才会展开。
3. 在 builder 末尾暴露图，推荐用 `build_exports()`：
   ```python
   def build_exports():
       agent = build_agent()
       return {
           "01_agent_react": build_agent(),
           "03_email_hitl": (build_hitl(agent), True),   # (graph, xray)
       }
   ```
4. 跑引擎导出，确认输出：PNG 成功打印 `[OK]`，离线则打印 `[FALLBACK]` 并落 `.mmd`。
5. 若被技术总结文档 `![..](image/..png)` 引用，确认文件名对得上。

## 注意

- 本 skill **零 API 费用、可离线**（回退 .mmd），与会烧 DashScope 额度的学习脚本完全不同，可放心多次运行。
- 不要为了导图去运行原始学习脚本。
