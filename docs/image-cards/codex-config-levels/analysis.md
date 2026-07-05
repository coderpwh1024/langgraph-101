# 内容分析：Codex 官方配置 用户级 vs 项目级对比

> 源文件：source-codex-config-levels.md（docs/codex_官方配置_用户级与项目级对比.md）
> 分析日期：2026-07-05

## 内容类型分类

**干货知识 / 概念科普 + 对比辨析**。面向开发者的工具配置深度整理，
核心价值是"一图看懂 Codex 配置分层"，天然适合知识卡片化。

## 核心信息提炼

1. **四个物理层级**：CLI 覆盖 > 项目级（.codex/ + .agents/）> profile > 用户级 > 系统级 > 默认值
2. **两套目录体系**：配置/规则走 `.codex/`，技能走 `.agents/skills`（开放标准）
3. **信任边界**：`.codex/` 受 trusted 门槛管控；AGENTS.md 与 `.agents/skills/` 不受
4. **五种合并语义**（最大记忆点/传播点）：
   - config.toml：就近覆盖
   - AGENTS.md：顺序拼接（32 KiB 上限）
   - skills：不合并、同名并列
   - hooks：并集全加载
   - rules：取最严（forbidden > prompt > allow）
5. **两个"无项目级"配置**：plugins（marketplace 分发）、custom prompts（已废弃 → 迁 skills）
6. 十项配置逐项对比 + 总速查表

## 爆款标题潜力（Hook 分析）

- "Codex 配置到底放哪？一张图讲清用户级 vs 项目级"
- "5 种合并语义，90% 的人会踩坑"
- "为什么 skills 在 .agents/ 而不是 .codex/？"

冲突点/反直觉点（适合做钩子）：
- 项目配置**覆盖**用户配置（与很多工具方向相反）
- 同一对路径，冲突结果因配置项完全不同（5 种语义）
- rules 只能收紧不能放松

## 目标受众

使用 Codex CLI / Claude Code 等 AI 编程工具的中文开发者；
关注 AGENTS.md / skills 开放标准的团队负责人。

## 互动潜力

- **收藏**：速查表型内容，强收藏属性（主打）
- **分享**：团队内统一配置规范时会被转发
- **评论**：`.codex/` vs `.agents/` 的路径分裂是天然讨论点

## 视觉机会映射

| 内容 | 视觉形式 |
| --- | --- |
| 层级优先级链 | 纵向金字塔/阶梯图（flow） |
| 双目录树 | 左右对照目录树（comparison） |
| 五种合并语义 | 五个小图标 + 一句话卡（dense/list） |
| 信任边界 | 门/闸机隐喻插画 |
| 速查表 | 精简 5 行表格卡（dense） |

## 滑动叙事流（Swipe Flow）

封面钩子 → 全景分层图 → 目录树对照 → 逐项要点（config/AGENTS.md/skills）
→ 五种合并语义（高潮页）→ 避坑要点 → 结尾速查+CTA

## 推荐方案

- **策略**：B 信息密集型（教程/对比/清单类内容的最佳匹配）
- **风格**：sketch-notes（本仓库既有卡片系列的锁定风格，保持系列一致性）
- **配色**：macaron（sketch-notes 默认配色）
- **布局**：以 dense/comparison/flow 混排，封面结尾 sparse/balanced
- **预设**：sketch-card（sketch-notes × dense）
- **语言**：中文
- **图片数量**：8 张（封面 + 6 内容 + 结尾）

## 8 张卡片草案

1. 封面（sparse）：钩子标题"Codex 配置到底放哪？"
2. 分层总览（flow）：6 级优先级链
3. 双目录树（comparison）：~ 用户级 vs repo 项目级
4. config.toml + AGENTS.md（dense）：覆盖 vs 拼接、32 KiB、验证命令
5. Skills（dense）：.agents/skills 四级作用域 + SKILL.md 结构
6. 五种合并语义（list）：本系列高潮页/最强收藏点
7. 避坑要点（dense）：trusted 边界、rules 只紧不松、无项目级的两项
8. 结尾（balanced）：速查心法 + 官方文档指引 CTA
