# 内容分析 — deep_agents.py part07 长期记忆（Backend）

## 内容分类
- **类型**：干货知识卡 / 技术科普（教学示例）
- **主题**：Deep Agents 的 Backend 机制与长期记忆（StateBackend / FilesystemBackend / StoreBackend / CompositeBackend + namespace）
- **受众**：学习 LangChain / LangGraph / deepagents 的开发者、AI Agent 工程入门者

## 核心要点（适合卡片化）
1. **一句话本质** — 长期记忆不是模型变聪明，而是「把文件柜从便利贴换成云盘」；文件存哪由 Backend 决定
2. **四种 Backend** — StateBackend(便利贴/临时) / FilesystemBackend(档案柜/磁盘) / StoreBackend(云盘/跨线程) / CompositeBackend(前台/路由)
3. **CompositeBackend 路由** — 按路径前缀转发：`/memories/`→StoreBackend(持久)，其余→StateBackend(临时)；跨线程读写演示
4. **三种记忆类型** — semantic(事实) / episodic(经历) / procedural(规则)，共用一个 store，靠 namespace 分桶
5. **分级记忆 private vs shared** — namespace 的 `lambda rt` 动态拼进 user_id → 按人隔离；写死则全员共享
6. **三级递进主线** — routing 前缀 → 静态 namespace → 动态 namespace(lambda rt)

## 爆款 / 收藏潜力
- 高收藏：Backend 对比表、跨线程记忆流程、private/shared 隔离图天然适合「存下来慢慢看」
- 可视化机会：四种 Backend 文件柜类比图、CompositeBackend 前台路由图、Alice/Bob 隔离对比图、三级递进阶梯图

## 推荐方案
- **策略**：B 信息密集型（技术干货，价值优先、结构清晰）
- **风格**：sketch-notes（手绘教育信息图，卡通手绘感）
- **配色**：macaron（柔和马卡龙，亲和易读）
- **布局**：dense / flow（高密度知识卡 + 流程图）
- **预设**：sketch-card（sketch-notes + dense）
- **图片数量**：6 张（封面 + 4 内容 + 结尾）
- **语言**：中文
