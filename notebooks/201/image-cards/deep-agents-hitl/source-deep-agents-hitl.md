# deep_agents.py · part06 — Human-in-the-Loop（人在回路 / 工具中断审批）

> 源：`notebooks/201/deep_agents.py` part06 段（行 483–548）+ 费曼式讲解精炼。
> 与 101 middleware 那套的区别：这里用 **deepagents 高层封装** `create_deep_agent`，
> 一行 `interrupt_on` 就拿到 LangGraph 的中断能力，**不用手写 node/edge**。

## 一句话本质

HITL 的本质：给 Agent 的**高风险、不可逆动作**（write_file / delete_file / 转账 / 发邮件）
加一道**人工闸门**——在「LLM 决定要做」和「真正执行」之间插入人工确认。
搜索错了可重来，但覆盖/删除文件做了就收不回来，所以要先停下来问人。

## 核心 API / 概念

| 概念 | 作用 |
| --- | --- |
| `create_deep_agent(...)` | deepagents 高层封装，替你搭好整张 LangGraph 图 |
| `interrupt_on={"write_file": True}` | 声明「拦截哪些工具」，命中即暂停，不直接执行 |
| `checkpointer=MemorySaver()` | 存档的档案室：把断点前的状态快照存内存 |
| `thread_id`（config） | 存档的门牌号：checkpointer 用它当 key 定位快照 |
| `result["__interrupt__"]` | 暂停时带回的待审信息（不是异常，是正常返回） |
| `action_requests` | Agent 想干什么：`name`(工具) + `args`(参数) |
| `review_configs` | 你能怎么回应：`allowed_decisions`(approve/edit/reject) |
| `Command(resume={...})` | 向图发送控制指令：读档，带决策从断点续跑 |

## 触发配置：两种写法

```python
# 简写（本例实际使用）：拦截该工具，用默认决策集
interrupt_on={"write_file": True, "edit_file": True}

# 详细写法：精确指定允许的决策
interrupt_on={
    "delete_file": {"allowed_decisions": ["approve", "edit", "reject"]},
    "write_file":  {"allowed_decisions": ["approve", "reject"]},
    "critical_operation": {"allowed_decisions": ["approve"]},  # 只能同意
}
```
> 注：part06 顶部（行 489-493）定义了详细版字典但**没被使用**，是一段死代码；
> 真正生效的是 create 时内联的简写版。

## 完整流程（拦截 → 存档 → 暂停 → 决策 → 续跑）

1. 第一次 `invoke`：用户请求「写 /test.md」→ LLM 决定调 `write_file`
2. `interrupt_on` 命中 → **执行前拦下**，不写盘
3. `checkpointer` 把「到断点为止的完整状态」快照存住，key = `thread_id`
4. `invoke` **正常返回**（暂停，不是结束），`result["__interrupt__"]` 带回 action_requests / review_configs
5. 人查看动作，做决策（approve / reject / edit）
6. 第二次 `invoke(Command(resume=...))` + **同一个 thread_id** → checkpointer 读档
7. **从 write_file 断点续跑，不是从头重跑**
8. approve → 真正执行写盘 → 继续收尾；reject → 不执行 → 告知被拒后继续

## 三个必须钉死的心智模型（易错点）

1. **是「中断 / interrupt」，不是「loop 判断」**——名字里的 loop 指人参与进循环。
2. **恢复是「读档续跑」，不是「从头重跑」**——前面的思考/搜索不重来（可用"搜索只打印 1 次"验证）。
3. **checkpointer = 存/读快照的档案室**——删了它，暂停瞬间无处存，HITL 崩溃；
   `MemorySaver` 存内存、**进程一退就没**，跨重启要换 `SqliteSaver`/`PostgresSaver`。

## 一句话主线

> 拦截(interrupt_on) → 存档(checkpointer + thread_id) → 暂停返回(__interrupt__)
> → 人决策 → 读档续跑(Command resume) → approve 放行 / reject 拦下
