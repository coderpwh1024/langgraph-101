# Hermes Agent 企业落地实战——ChatGPT 对话分类归纳

- **来源**：[ChatGPT 分享对话「Docker 安装问题解决」](https://chatgpt.com/share/6a473886-4390-83ee-87b6-ff038cf0d1ab)
- **完整对话**：共 127 组问答，全文见 [`../full_transcript.md`](../full_transcript.md)
- **归纳日期**：2026-07-06

## 内容主线

这是一段完整的企业 AI Agent 落地实战记录：从零开始用 Docker 部署 Nous Research 的 Hermes Agent，绕开官方 Nous Portal 授权改用自有中转站 API，先后接通 GitLab（代码检索与需求评审）和飞书机器人（企业内对话入口），沉淀出需求评审 Skill 体系与 SOUL.md 配置，最后完成性能优化、使用手册撰写和向领导汇报，定位为「企业 AI 研发协作平台 V1 内部试点版」（对外命名 HipobuyAgent）。

## 分类文档索引

| 序号 | 文档 | 对应问答 | 核心内容 |
| --- | --- | --- | --- |
| 01 | [Hermes Docker 部署与授权](01-hermes-docker部署与授权.md) | 第 1~30 问 | Nous Portal 账号的四大职能；BYOK 跳过官方授权（Custom endpoint + 自有 `OPENAI_API_KEY`/`OPENAI_BASE_URL`）；Setup Wizard 每屏选择；一个项目 = 一个容器 + 独立数据目录的多实例隔离；`hermes gateway` 常驻模式与 `-d` 无终端重启坑 |
| 02 | [GitLab 接入与代码同步](02-gitlab接入与代码同步.md) | 第 31~60 问 | 本地 clone / API / MCP 三方案对比与选型（本地代码为主力）；只读 Token 权限考量；浅克隆 + crontab 定时同步脚本；Webhook + MR 自动评审的双链路架构（人工分析走 Hermes、自动评审走 Webhook → Python → LLM API） |
| 03 | [飞书接入与需求评审 Skill](03-飞书接入与需求评审skill.md) | 第 61~82 问 | 飞书企业自建应用与多 AppID 隔离切换；WebSocket vs Webhook 通道选择；需求评审五层提示词约束；五大标准 SKILL.md（pm-review / code-review / architecture 等，含 frontmatter 格式演进）；HipobuyAgent 命名；四阶段落地路线 |
| 04 | [SOUL.md 配置、使用手册与汇报](04-soul配置-使用手册与汇报.md) | 第 83~105 问 | SOUL.md 的定位与推荐结构；修改未生效排查（含 SOLU.md 拼写坑与缓存重置）；去 Hermes 化身份覆盖；使用手册「模板 + 截图 + 摘要结论」写法（领导发 PDF、研发发 md）；飞书汇报话术模板与时机选择 |
| 05 | [性能优化与体验评估](05-性能优化与体验评估.md) | 第 106~127 问 | 慢的根因：多轮 `execute_code` 占总耗时 50%~70%；企业响应时间分级标准；优化优先级（聚合检索脚本 → SOUL.md 导航化 → 双评审模式 → SQLite 代码索引 → 立即反馈）；系统 V1 试点评分；工时评估拆分总工时（Person Hour）vs 交付周期（Elapsed Time） |

## 每篇文档的固定结构

每篇归纳均包含：**本篇概述 → 按知识点分小节（含对话原文中的命令 / 配置 / 提示词模板）→ 踩坑与解决 → 要点总结**。用户上传截图不可见的部分，文中以「（根据上下文推断）」标注。

## 全局要点速览

- **部署**：不用 Nous 订阅也能跑 Hermes，Custom endpoint + 自有 API Key（BYOK）即可，数据全部留在自己服务器。
- **架构**：一个项目一个容器、独立数据目录隔离；gateway 模式常驻，交互调试另开临时聊天容器共享数据目录。
- **代码接入**：企业场景下「本地 clone 为主 + API 元数据辅助」优于纯 API 或 MCP；配定时 pull 保持代码新鲜。
- **提示词资产**：需求评审五层约束 + 五个带 frontmatter 的 SKILL.md + SOUL.md 项目导航化，是整套系统的核心可复用资产。
- **性能**：优化重点不是换模型，而是减少工具调用轮次（聚合检索一次拿全）+ 立即反馈改善心理体验；平均响应控制在 1 分钟内、复杂需求 2 分钟内是理想目标。
- **汇报**：定位说「核心功能已完成，可进入研发内部试点，后续持续优化体验」，而不是「已经完成」或「还有很多问题」。
