---
name: cards-from-summary
description: Use when turning a 技术总结 markdown doc into a Xiaohongshu/公众号 infographic card series in this repo (e.g. "把这份技术总结做成图文卡片", "生成小红书卡片", "make image cards from the summary"). Drives the baoyu-image-cards pipeline with this repo's locked preset (sketch-notes / macaron / 中文卡通) and output layout under notebooks/<series>/image-cards/<topic>/.
---

# 技术总结→图文卡片 (cards-from-summary)

把一份 `_技术总结.md`（或任意技术干货 md）转成**小红书 / 公众号信息图卡片系列**，复刻 `notebooks/101/image-cards/langgraph-middleware/` 已跑通的产物结构与视觉风格。

## 本仓库锁定的预设（来自 langgraph-middleware 那套）

- **策略**：`B 信息密集型`（技术干货，价值优先、结构清晰）
- **风格**：`sketch-notes`（手绘教育信息图，卡通手绘感）
- **配色**：`macaron`（柔和马卡龙）
- **布局**：`dense / flow`（高密度知识卡 + 流程图）
- **图片数量**：默认 `6`（封面 ×1 + 内容 ×4 + 结尾 ×1），可按内容增减到 1–10
- **语言**：`中文`
- 卡片三段式：`cover`（钩子标题）→ `content`（核心要点，每张一个主题）→ `ending`（要点回顾 + 一句话总结）

## 输出目录结构（必须照此布局）

```
notebooks/<系列>/image-cards/<topic>/
├── source-<topic>.md      # 源内容（技术总结的精炼/拷贝）
├── analysis.md            # 内容分析：内容分类 / 核心要点 / 爆款潜力 / 推荐方案
├── outline.md             # frontmatter(策略/风格/配色/布局/数量/语言) + P1..Pn 卡片脚本
├── prompts/0X-*.md        # 每张卡片的生图 prompt
└── 0X-*.png               # 生成的卡片图
```

`<topic>` 用 kebab-case，如 `langgraph-multi-agent`；`<系列>` 取技术总结所在系列（101/201）。

## 工作步骤

1. **确认输入**：哪份技术总结 md、`<topic>` 名、卡片数量（默认 6）。
2. **委托 baoyu 链路**：调用 `baoyu-image-cards` 技能完成实际分析→outline→生图，但把上面的「锁定预设」「输出目录结构」作为硬约束传入，确保风格与目录与既有 middleware 那套保持一致。
3. **analysis.md**：按样板四段——`内容分类` / `核心要点（适合卡片化）` / `爆款·收藏潜力` / `推荐方案`。
4. **outline.md**：YAML frontmatter（`strategy/name/style/palette/layout/image_count/language` + `elements`）+ 每张卡片 `## PX 标题` 含 `Type / Hook|Message / Points / Visual / Layout`。
5. **生图**：sequential 逐张生成；多张已定稿时才用并行批量。
6. 产物全部落到上面的目录结构下。

## 注意

- 卡片是**二次传播物料**，不是技术文档：要点要提炼、可视化（流程图/钩子位置图/对比图）优先，别整段搬运代码。
- 若源技术总结还没生成，先提示用户用 `/tech-summary`，或直接以脚本为源。
- 实际生图依赖 baoyu-image-cards 的后端配置（API key 等），由该技能处理；本技能只负责「锁定风格 + 规整目录 + 串起流程」。
