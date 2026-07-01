---
strategy: b
name: Information-Dense
style: sketch-notes
palette: macaron
style_reason: "手绘教育风 + 卡通手绘感，把 HITL 中断流程变得亲和易懂，与 middleware 系列同风格"
elements:
  background: paper-texture (warm cream #F5F0E8)
  decorations: [hand-drawn-lines, stars-sparkles, arrows-curvy, circle-mark, pause-icon, lock-icon]
  emphasis: underline + coral-red accent
  typography: handwritten
layout: dense / flow
image_count: 6
language: zh
---

## P1 封面 Cover
**Type**: cover
**Hook**: "Deep Agents 人在回路 · 一张图看懂工具中断审批"
**Message**: 高风险动作前先暂停、等人工授权
**Visual**: 卡通机器人 Agent 伸手要按「写文件」按钮，一只人手竖起手掌⏸拦住，中间大大的暂停图标 + 小锁🔒
**Layout**: sparse

## P2 一句话本质 + 核心 API
**Type**: content
**Message**: 给不可逆动作加人工闸门；6 个核心 API 速记
**Points**: 本质=在「决定做」和「真正做」之间插确认 ; create_deep_agent / interrupt_on / checkpointer(MemorySaver) / thread_id / __interrupt__ / Command(resume)
**Visual**: 顶部一句本质金句(下划珊瑚红)，下方 6 个圆角彩色小卡片各配手绘图标
**Layout**: dense

## P3 触发闸门：拦在哪 + 两种写法
**Type**: content
**Message**: interrupt_on 命中即暂停，闸门在"执行前"
**Points**: 简写 {"write_file":True} = 默认决策 ; 详细 {"allowed_decisions":[approve/edit/reject]} = 精细控制 ; critical_operation 只能 approve
**Visual**: 一条横向管道 LLM决定→⛔闸门→执行，闸门卡在中间高亮；下方对比两种写法的小代码块
**Layout**: flow

## P4 中断数据结构：__interrupt__ 里有什么
**Type**: content
**Message**: 暂停不是结束，invoke 正常返回一包待审信息
**Points**: action_requests = Agent想干什么(name+args) ; review_configs = 你能怎么回应(allowed_decisions) ; 此刻是「暂停」不是「结束」
**Visual**: 一个手绘信封/包裹拆开，里面两张卡：左 action_requests 右 review_configs
**Layout**: dense

## P5 完整流程图：拦截→存档→续跑
**Type**: content
**Message**: 两次 invoke 同 thread_id，断点精确续跑
**Points**: 第1次invoke→命中interrupt_on→checkpointer存档(thread_id)→返回__interrupt__暂停 ; 人决策 ; 第2次Command(resume)→读档→从断点续跑→approve放行/reject拦下
**Visual**: 左右双栏流程图，中间 checkpointer 存档桶(珊瑚红高亮)作枢纽，弯箭头连"暂停存档→恢复读取"
**Layout**: flow

## P6 三个易错点纠错（结尾）
**Type**: ending
**Message**: 钉死心智模型 + 一句话主线
**Points**: ①是「中断interrupt」不是「loop判断」 ②恢复是「读档续跑」不是「从头重跑」 ③checkpointer是存档档案室(MemorySaver进程退出即失) ; 主线：拦截→存档→暂停→决策→续跑→放行/拦下
**Visual**: 3 张"❌错→✅对"对照卡 + 卡通小人竖大拇指，底部一条主线箭头
**Layout**: balanced
