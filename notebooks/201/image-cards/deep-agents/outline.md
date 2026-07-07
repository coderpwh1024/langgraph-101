---
strategy: b
name: Information-Dense
style: sketch-notes
palette: macaron
style_reason: "Deep Agents 涉及架构、后端、记忆与技能系统，手绘教育信息图能把复杂链路拆成亲和、可收藏的视觉笔记"
elements:
  background: paper-texture (warm cream #F5F0E8)
  decorations: [hand-drawn-lines, stars-sparkles, arrows-curvy, circle-mark, checkmarks]
  emphasis: underline + coral-red accent
  typography: handwritten
layout: dense / flow
image_count: 10
language: zh
---

## P1 Deep Agents 一套图看懂
**Type**: cover
**Hook**: "Deep Agents 不只是会调工具：它是一套研究型 Agent 工作系统"
**Points**: 规划 / 文件系统 / Backend / 子 Agent / Middleware / HITL / 长期记忆 / Skills
**Visual**: 卡通工程师站在一个巨大的 Agent 控制台前，控制台连接文件夹、搜索放大镜、记忆盒子和技能卡片
**Layout**: sparse

## P2 核心心智模型
**Type**: content
**Message**: 从普通 Agent 到 Deep Agent，差别在「长任务工作台」
**Points**: `create_deep_agent` / 内置文件工具 / `write_todos` / 虚拟文件系统 / 中文系统提示词 / 统一 `model`
**Visual**: 左侧普通聊天气泡，右侧 Deep Agent 工作台；工作台上有 Todo、Files、Tools 三个区域
**Layout**: comparison

## P3 工具扩展：让 Agent 能搜索
**Type**: content
**Message**: `@tool` 把外部能力变成 LLM 可调用动作
**Points**: `TAVILY_API_KEY` 检查 / `TavilyClient.search` / 标题+URL+摘要 / docstring 即工具说明 / 具体异常优先
**Visual**: 搜索放大镜连接到 3 张结果卡片，再回到 Agent 的研究笔记
**Layout**: flow

## P4 Backend 路由：文件到底存哪？
**Type**: content
**Message**: 同样是路径，背后可能是临时状态、真实磁盘或长期记忆
**Points**: 默认 `StateBackend` / `/workspace/*` -> `FilesystemBackend` / `/memories/*` -> `StoreBackend` / `CompositeBackend` 统一路由
**Visual**: 一个路由分流器，把 3 条路径箭头分别导向云状态、磁盘文件夹、记忆数据库
**Layout**: flow

## P5 子 Agent：协调者与研究员
**Type**: content
**Message**: 主 Agent 负责规划与综合，子 Agent 专注研究执行
**Points**: `research_subagent` / `task()` 委派 / 主 Agent 不直接搜索 / 搜索次数限制 / 行内引用与来源
**Visual**: 主协调员拿着任务板，把 3 个研究任务交给研究员小机器人，最后汇总到 `/final_report.md`
**Layout**: flow

## P6 Middleware：运行时治理层
**Type**: content
**Message**: 工具调用不是黑盒，可以被记录、包裹和裁剪
**Points**: `wrap_tool_call` / 打印工具名与参数 / `handler(request)` / 完成日志 / `ClearToolUsesEdit(trigger=1, keep=1)` 清理旧工具结果
**Visual**: 工具调用流水线：Request -> Logger -> Tool -> Done；旁边有剪刀剪掉旧工具结果
**Layout**: flow

## P7 HITL：写文件前先过人
**Type**: content
**Message**: `interrupt_on` 把高风险文件操作变成人工可审核动作
**Points**: `write_file` / `edit_file` / approve / edit / reject / `__interrupt__` / `Command(resume)` / 尊重审核后参数
**Visual**: Agent 准备写文件，被暂停牌拦住；人工审核台给出批准、编辑、拒绝三枚印章
**Layout**: flow

## P8 长期记忆：给记忆分层和分权
**Type**: content
**Message**: 记忆不是一坨文本，而是有类型、有作用域的存储设计
**Points**: `/memories/semantic` 事实 / `/episodic` 经历 / `/procedural` 规则 / `/user` 私有 / `/shared` 共享 / namespace 隔离
**Visual**: 五层抽屉式记忆柜，每个抽屉有标签和小图标，旁边有用户 Alice/Bob 权限对比
**Layout**: dense

## P9 AGENTS.md + Skills：可移植能力层
**Type**: content
**Message**: 规则常驻，技能按需加载，Agent 才能变成工作系统
**Points**: `/AGENTS.md` 工作流程 / `/skills/linkedin-post` / `/skills/twitter-post` / `memory=["/AGENTS.md"]` / `skills=["/skills/"]` / `files=skill_files`
**Visual**: 一本规则手册常驻在 Agent 旁边，两张技能卡片从工具箱弹出，分别生成 LinkedIn 与 X 内容
**Layout**: dense

## P10 结尾：完整研究 Agent 总览
**Type**: ending
**Message**: 一句话总结：Deep Agents = 长任务规划 + 文件系统 + 后端路由 + 子 Agent + 治理 + 记忆 + 技能
**Points**: ①规划任务 ②委派研究 ③写报告 ④存记忆 ⑤按技能生成内容 ⑥跨线程验证路径路由
**Visual**: 一张总览地图，从用户任务开始，经过 Agent 主控台、研究子 Agent、Backend、Memory、Skills，最终输出报告和社媒内容
**Layout**: mindmap

