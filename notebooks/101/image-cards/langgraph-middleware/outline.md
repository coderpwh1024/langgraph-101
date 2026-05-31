---
strategy: b
name: Information-Dense
style: sketch-notes
palette: macaron
style_reason: "手绘教育风 + 卡通手绘感，把技术干货变得亲和易懂，符合用户「卡通版本」要求"
elements:
  background: paper-texture (warm cream #F5F0E8)
  decorations: [hand-drawn-lines, stars-sparkles, arrows-curvy, circle-mark]
  emphasis: underline + coral-red accent
  typography: handwritten
layout: dense / flow
image_count: 6
language: zh
---

## P1 封面 Cover
**Type**: cover
**Hook**: "LangGraph 中间件 & 人在回路 一张图看懂"
**Visual**: 卡通小人坐在电脑前，旁边一个机器人 Agent，中间一个暂停⏸图标 + 锁🔒
**Layout**: sparse

## P2 核心技术栈
**Type**: content
**Message**: 9 个核心 API/概念速记
**Points**: create_agent / @tool / interrupt() / Command(resume) / checkpointer / thread_id / AgentMiddleware / @dynamic_prompt / context_schema
**Visual**: 9 个圆角彩色小卡片，每个配一个手绘小图标
**Layout**: dense

## P3 四大模块（递进）
**Type**: content
**Message**: 从基础中断 → 安全护栏的 4 步递进
**Points**: ①基础中断授权 ②高级中断(approve/reject/edit) ③中间件(动态提示词+日志) ④安全中间件+中断
**Visual**: 4 个手绘弯箭头串联的步骤块
**Layout**: flow

## P4 中间件三大钩子
**Type**: content
**Message**: 模型调用「前·中·后」插入逻辑
**Points**: before_model(前·日志校验) / wrap_model_call(中·包裹请求) / after_model(后·安全检查)
**Visual**: 竖向生命周期流程，LLM 在中间，三个钩子标注位置
**Layout**: flow

## P5 Human-in-the-Loop 中断恢复
**Type**: content
**Message**: 两次 invoke 同 thread_id，断点精确恢复
**Points**: 第一次invoke→interrupt()暂停→checkpointer存档 ; 第二次Command(resume=决策)→恢复→approve/reject/edit
**Visual**: 左右双栏流程图 + 中间 checkpointer 存档桶
**Layout**: flow

## P6 关键要点回顾（结尾）
**Type**: ending
**Message**: 4 大要点 + 一句话总结
**Points**: ①人在回路 interrupt+resume+checkpointer ②中间件三钩子 ③动态提示词千人千面 ④安全护栏(监控+兜底)
**Visual**: 卡通小人竖大拇指，4 个打勾要点卡片
**Layout**: balanced
