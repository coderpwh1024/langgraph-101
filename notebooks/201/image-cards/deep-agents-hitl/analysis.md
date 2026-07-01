# 内容分析 — deep_agents.py · part06 HITL 流程图

## 内容分类
- **类型**：干货知识卡 / 技术科普（教学示例，聚焦单主题）
- **主题**：deepagents `create_deep_agent` 的 Human-in-the-Loop（工具中断审批）流程
- **受众**：学习 LangGraph / deepagents 的开发者、AI Agent 工程入门者

## 核心要点（适合卡片化）
1. **一句话本质** — 给高风险/不可逆动作加人工闸门，在「决定做」和「真正做」之间插确认
2. **核心 API** — `create_deep_agent` / `interrupt_on` / `checkpointer(MemorySaver)` / `thread_id` / `__interrupt__` / `Command(resume)`
3. **触发闸门** — `interrupt_on={"write_file":True}` 命中即暂停；两种写法：`True`(默认) vs `{"allowed_decisions":[...]}`(精细)
4. **中断数据结构** — `__interrupt__` = action_requests(想干什么) + review_configs(能怎么回应)
5. **完整流程图** — 拦截→存档→暂停返回→人决策→读档续跑→approve/reject
6. **三个心智模型纠错** — 中断≠loop判断 / 续跑≠从头重跑 / checkpointer是存档(MemorySaver易失)

## 爆款 / 收藏潜力
- 高收藏：流程图 + 「易错点纠正」天然适合"存下来防踩坑"
- 可视化机会：闸门位置图（决定 vs 执行之间）、双 invoke 存档/读档流程、续跑 vs 重跑对比
- 情绪钩子：「你以为的恢复 = 从头重跑？错！」这种认知反转最抓收藏

## 推荐方案
- **策略**：B 信息密集型（技术干货，价值优先、结构清晰）
- **风格**：sketch-notes（手绘教育信息图，卡通手绘感）
- **配色**：macaron（柔和马卡龙，亲和易读）
- **布局**：dense / flow（高密度知识卡 + 流程图）
- **预设**：sketch-card（sketch-notes + dense）
- **图片数量**：6 张（封面 + 4 内容 + 结尾）
- **语言**：中文
