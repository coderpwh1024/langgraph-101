# 内容分析：A Field Guide to Fable: Finding Your Unknowns

## 基本信息

- 来源：X Article，作者 Thariq (@trq212)，发布于 2026-07-03
- 原文链接：https://x.com/trq212/status/2073100352921215386
- 体裁：实践指南型博客（field guide），约 2342 词
- 领域：AI 辅助编程 / agentic coding 工作流方法论

## 主题与结构

核心论点：与 Claude Fable 5 协作时，工作质量的瓶颈在于使用者澄清"未知"（unknowns）的能力。文章借用"地图与疆域"（the map is not the territory）的隐喻，以及拉姆斯菲尔德式的四象限（已知的已知 / 已知的未知 / 未知的已知 / 未知的未知）来框定问题，然后按实现前、实现中、实现后三个阶段给出具体技巧，每个技巧附示例提示词。

结构：引言（地图与疆域）→ 认识你的未知（四象限）→ 帮 Claude 帮你 → 实现前（盲区排查、头脑风暴与原型、访谈、参考物、实现计划）→ 实现中（实现笔记）→ 实现后（提案与讲解、测验）→ 案例（Fable 发布视频）→ 结语。

## 语气与风格

第一人称经验分享，口吻务实、直接，偏工程师对工程师的交流。有少量口语化表达和幽默。目标读者为熟悉 AI 编程工具的开发者（与 EXTEND.md 的 technical 受众一致）。

## 术语表（本篇统一译法）

| 原文 | 译法 | 说明 |
| --- | --- | --- |
| unknowns | 未知 | 核心概念，首次出现标注英文 |
| Known Knowns / Known Unknowns / Unknown Knowns / Unknown Unknowns | 已知的已知 / 已知的未知 / 未知的已知 / 未知的未知 | 四象限固定译法 |
| the map is not the territory | 地图不等于疆域 | 经典隐喻，首次标注英文 |
| agentic coding | 智能体编程（agentic coding） | 保留英文 |
| blindspot pass | 盲区排查（blindspot pass） | 作者强调要用原词提示，必须保留英文 |
| artifact | 工件（artifact） | Claude 语境下的产物文件 |
| prompt | 提示词 | |
| implementation plan / notes | 实现计划 / 实现笔记 | |
| color grading | 调色（color grading） | |
| long-horizon task | 长周期任务 | |
| buy-in | 认同与支持 | 视上下文意译 |
| Claude Design / Claude Code / Fable / Remotion / Whisper / ffmpeg | 保留英文 | 产品与工具名 |

## 翻译难点

1. **原文笔误**：如 "The best agentic coders are good have relatively few unknowns"（语法冗余）、"the treal app"（the real app 之误）、"important for" 句子戛然而止——按作者意图译顺，不保留笔误。
2. **抓取残留**：部分链接锚文本丢失，正文中出现裸 URL（如 "I've made some https://... but be sure to come back"），按上下文补出自然的锚文本语义（该链接指向 prompts 集合页）。
3. **示例提示词**：是文章的实用主体，需译得可直接使用；同时 "blindspot pass"、"unknown unknowns" 等作者建议原样使用的触发词保留英文。
4. **隐喻密度高**：map/territory、potholes、forest through the trees 等，按意图意译。
5. **Markdown 保真**：图片、链接、标题层级（正文有 H1 级的 Pre/Post implementation 分节）原样保留；"During implementation" 在原文中是 H2，紧跟同级 H2 "Implementation notes"，按原样保留。
