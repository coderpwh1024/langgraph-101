# 内容分析 — 102_middleware.py 技术总结

## 内容分类
- **类型**：干货知识卡 / 技术科普（教学示例）
- **主题**：LangChain Agent + LangGraph 的 Human-in-the-Loop（中断授权）与 Middleware（中间件）
- **受众**：学习 LangChain / LangGraph 的开发者、AI Agent 工程入门者

## 核心要点（适合卡片化）
1. **核心技术栈** — `create_agent` / `@tool` / `interrupt()` / `Command(resume)` / `checkpointer` / `thread_id` / `AgentMiddleware` / `@dynamic_prompt` / `context_schema`
2. **四大模块** — 基础中断授权 → 高级中断模式(approve/reject/edit) → 中间件 → 安全中间件+中断
3. **中间件三大钩子** — `before_model`（前）/ `wrap_model_call`（中·包裹）/ `after_model`（后）
4. **Human-in-the-Loop 流程** — 两次 invoke 同 thread_id，checkpointer 存档，Command(resume) 精确恢复
5. **动态提示词** — 基于 context_schema(user_role) 千人千面
6. **生产级安全护栏** — 中间件被动监控 + 中断主动兜底人工授权

## 爆款 / 收藏潜力
- 高收藏：技术干货、流程图、钩子位置图天然适合"存下来慢慢看"
- 可视化机会：生命周期钩子位置、中断/恢复双 invoke 流程、整体架构分层

## 推荐方案
- **策略**：B 信息密集型（技术干货，价值优先、结构清晰）
- **风格**：sketch-notes（手绘教育信息图，卡通手绘感，符合用户"卡通版本"要求）
- **配色**：macaron（sketch-notes 默认，柔和马卡龙，亲和易读）
- **布局**：dense / flow（高密度知识卡 + 流程图）
- **预设**：sketch-card（sketch-notes + dense）
- **图片数量**：6 张（封面 + 4 内容 + 结尾）
- **语言**：中文
