---
strategy: b
name: Information-Dense
style: sketch-notes
palette: macaron
style_reason: "手绘教育风 + 卡通手绘感，把 Backend 与长期记忆这类抽象机制变得亲和易懂，与 middleware 系列保持一致"
elements:
  background: paper-texture (warm cream #F5F0E8)
  decorations: [hand-drawn-lines, stars-sparkles, arrows-curvy, circle-mark]
  emphasis: underline + coral-red accent
  typography: handwritten
layout: dense / flow
image_count: 7
language: zh
---

## P1 封面 Cover
**Type**: cover
**Hook**: "给 AI Agent 装上长期记忆：一张图看懂 Deep Agents 的 Backend"
**Visual**: 卡通机器人 Agent 抱着一个大脑💭，旁边一排文件柜（便利贴/档案柜/云盘），中间一个「记忆」齿轮图标
**Layout**: sparse

## P2 四种 Backend（核心对比）
**Type**: content
**Message**: 文件存哪、能不能记住，全看 Backend
**Points**: StateBackend=便利贴(线程结束擦掉) / FilesystemBackend=档案柜(磁盘永久) / StoreBackend=云盘(跨线程持久) / CompositeBackend=前台(按路径路由)
**Visual**: 4 个手绘文件柜卡片，各配一个类比小图标（便利贴/档案柜/云朵/前台铃铛）
**Layout**: dense

## P3 CompositeBackend 路由 + 跨线程记忆
**Type**: content
**Message**: 前台按路径前缀转发，决定文件能否跨对话
**Points**: /memories/→StoreBackend(云盘·持久) ; 其余→StateBackend(便利贴·临时) ; 线程1写→线程2(新thread_id)仍读得到 ; /scratch.txt 换线程即消失
**Visual**: 中间一个前台，两条手绘岔路箭头分别指向「云盘」和「便利贴」；下方左右双线程读写流程
**Layout**: flow

## P4 三种记忆类型（namespace 分桶）
**Type**: content
**Message**: 一个 store，靠 namespace 分成三个记忆桶
**Points**: semantic 语义=事实(喜欢Python) / episodic 情景=经历(上次研究LangGraph) / procedural 程序=规则([1][2]引用) ; namespace 是分区键(namespace,key)定位
**Visual**: 一个大云盘里三个贴标签的抽屉，标签分别 semantic/episodic/procedural
**Layout**: dense

## P5 分级记忆 private vs shared（lambda rt 开关）
**Type**: content
**Message**: namespace 里动态拼进 user_id → 按人隔离
**Points**: Alice→("user","alice") ; Bob→("user","bob") 互不可见 ; shared 写死("shared") 全员共享 ; 隔离开关 = namespace 那行 lambda rt
**Visual**: 左 Alice 右 Bob 各自私有抽屉(带锁🔒不互通)，中间一个共享抽屉(两人都能拿)；高亮一行 lambda rt
**Layout**: flow

## P6 三个维度辨析 checkpointer vs thread_id vs namespace
**Type**: content
**Message**: 三件事是三个维度，不是包含关系（本块唯一难点）
**Points**: checkpointer=拍快照存档·管「会不会丢」(内存版临时/落盘版持久) ; thread_id=选读哪份存档·管「读谁的会话」 ; namespace=store里按用户分抽屉·管「哪个用户的长期记忆」 ; 难点：没checkpointer=根本没存档，换thread=读错了存档，原因不同
**Visual**: 三张并排竖卡(相机📷/号码牌/贴标签抽屉)，下方珊瑚红虚线框画双格对比(打叉相机 vs 两个号码牌)，结论一行「先存档→再选编号」
**Layout**: dense

## P7 关键要点回顾（结尾）
**Type**: ending
**Message**: 三级递进 + 一句话总结
**Points**: ①四种Backend各司其职 ②CompositeBackend按前缀路由 ③namespace分桶三类记忆 ④lambda rt按user_id隔离 ; 主线：routing→静态namespace→动态namespace
**Visual**: 卡通机器人竖大拇指，一个三级台阶(routing→静态namespace→动态namespace) + 4 个打勾要点卡片
**Layout**: balanced
