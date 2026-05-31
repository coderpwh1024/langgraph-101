# 102_middleware.py 技术知识总结

> 本文档基于 `notebooks/101/102_middleware.py` 的代码，系统梳理其涉及的技术知识、功能模块与架构流程。

这份代码是一个 **LangChain Agent（智能体）+ LangGraph** 的综合教学示例，围绕两大核心能力展开：**Human-in-the-Loop（人在回路 / 中断授权）** 和 **Middleware（中间件）**。整体由 4 个递进的模块组成。

---

## 一、核心技术栈

| 技术组件 | 作用 |
|---------|------|
| `create_agent` | LangChain 高层 API，快速构建一个 ReAct 式智能体 |
| `@tool` | 把普通 Python 函数封装成 LLM 可调用的工具 |
| `interrupt()` | LangGraph 的"中断"机制，暂停执行等待人工输入 |
| `Command(resume=...)` | 从中断点恢复执行，并注入人工决策结果 |
| `MemorySaver` / `checkpointer` | 状态持久化，保存中断时的现场以便恢复 |
| `thread_id` (config) | 会话隔离，标识一次独立的对话上下文 |
| `AgentMiddleware` | 在 Agent 生命周期的关键节点插入自定义逻辑 |
| `@dynamic_prompt` | 中间件装饰器，动态生成系统提示词 |
| `context_schema` | 运行时上下文（如用户角色），驱动动态行为 |

---

## 二、四大模块功能详解

### 模块 1：基础中断授权
- `send_mail` 工具内部调用 `interrupt()`，发邮件前**暂停**，把邮件内容抛回给调用方。
- 主流程检查返回值里是否含 `"__interrupt__"`，若有则展示待审信息。
- 通过 `Command(resume={"approved": True/False})` 恢复执行，演示**批准**与**拒绝**两条路径。

### 模块 2：高级中断模式
- `send_email_v2` 支持三种人工决策：`approve`（批准）、`reject`（拒绝）、`edit`（编辑后发送）。
- 演示了人类不仅能"放行/拦截"，还能**修改 Agent 的行为参数**后再继续。

### 模块 3：中间件
两类中间件：

1. **`@dynamic_prompt` 动态提示词** —— 根据 `context` 中的 `user_role`（expert / beginner / general）切换系统提示词，实现千人千面。
2. **`RequestLoggerMiddleware` 类中间件** —— 实现三个生命周期钩子：
   - `before_model`：调模型**前**记录消息数量
   - `wrap_model_call`：**包裹**模型调用，打印请求详情
   - `after_model`：调模型**后**判断是工具调用还是最终回复

### 模块 4：安全中间件 + 中断结合
- `delete_database` 是危险操作，结合 `interrupt()` 做删除前确认。
- `SafetyMiddleware.after_model` 检测模型输出中是否含 `delete` 类工具调用，命中则打日志告警。
- 体现**生产级 Agent 的安全护栏**：中间件监控 + 中断兜底人工授权。

---

## 三、Agent 执行生命周期（中间件钩子位置）

```text
        invoke(messages)
              │
              ▼
   ┌──────────────────────┐
   │   before_model()      │  ◄── 调模型前：日志/校验/注入
   └──────────────────────┘
              │
              ▼
   ┌──────────────────────┐
   │  dynamic_prompt /      │  ◄── 动态构造 ModelRequest
   │  wrap_model_call()     │      （包裹模型调用）
   └──────────────────────┘
              │
              ▼
        ┌───────────┐
        │   LLM     │  调用大模型
        └───────────┘
              │
              ▼
   ┌──────────────────────┐
   │   after_model()       │  ◄── 调模型后：安全检查/日志
   └──────────────────────┘
              │
       有 tool_calls? ──── No ──► 返回最终回复 (END)
              │ Yes
              ▼
        ┌───────────┐
        │ Tool 执行  │
        └───────────┘
              │
       含 interrupt()? ── Yes ──► ⏸ 暂停，存档到 checkpointer
              │                       └─ 返回 __interrupt__
              │ No                    （等待 Command(resume)）
              ▼
        循环回到 before_model（ReAct Loop）
```

---

## 四、Human-in-the-Loop 中断/恢复流程

```text
 第一次 invoke                         第二次 invoke
 ┌─────────────┐                      ┌────────────────────┐
 │ 用户: 发邮件 │                      │ Command(resume=决策) │
 └──────┬──────┘                      └─────────┬──────────┘
        │                                       │
        ▼                                       ▼
   LLM 决定调用 send_mail              从 checkpointer 恢复现场
        │                                       │
        ▼                                       ▼
   工具内 interrupt() ⏸               interrupt() 返回 resume 的值
        │                                       │
        ▼                              ┌────────┴─────────┐
   存档状态 (thread_id)               approve / reject / edit
        │                              │        │         │
        ▼                              ▼        ▼         ▼
   返回 __interrupt__               发送     拒绝      改后发送
        │                              └────────┬─────────┘
        ▼                                       ▼
   程序展示待审信息                        返回最终响应
```

> **关键点**：两次 `invoke` 用同一个 `thread_id`，`checkpointer` 负责在中断处保存全部状态，`Command(resume=...)` 携带人工决策从断点精确恢复。

---

## 五、整体架构图

```text
┌──────────────────────────────────────────────────────────────┐
│                      应用层 (Demo 调用)                          │
│   invoke(messages) ──► 检查 __interrupt__ ──► Command(resume)   │
└────────────────────────────┬─────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                   create_agent (LangChain)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐  │
│  │  Middleware   │  │    Model     │  │       Tools          │  │
│  │ ·dynamic_prompt│ │  (utils.model)│ │ ·send_mail/v2        │  │
│  │ ·RequestLogger │ │              │  │ ·explain_concept     │  │
│  │ ·Safety        │ │              │  │ ·delete_database     │  │
│  └──────────────┘  └──────────────┘  └──────────┬──────────┘  │
└──────────────────────────────────────┬──────────┼────────────┘
            context_schema              │          │ interrupt()
            (user_role)                 ▼          ▼
┌──────────────────────────────────────────────────────────────┐
│                      LangGraph 运行时                           │
│   StateGraph (ReAct Loop)  +  MemorySaver (checkpointer)       │
│              状态持久化 / 中断暂停 / 断点恢复                     │
└──────────────────────────────────────────────────────────────┘
```

---

## 六、关键要点回顾

1. **Human-in-the-Loop**：通过 `interrupt()` + `Command(resume=...)` + `checkpointer`，让 Agent 在关键操作（发邮件、删库）前暂停，交由人工批准 / 拒绝 / 编辑。
2. **Middleware 三大钩子**：`before_model` / `wrap_model_call` / `after_model` 分别在模型调用前、中、后插入逻辑，可用于日志、动态提示词、安全检查。
3. **动态提示词**：基于 `context_schema` 中的运行时上下文（如用户角色）实现个性化系统提示词。
4. **生产级安全护栏**：中间件被动监控危险操作 + 中断主动兜底人工授权，二者结合保障 Agent 安全。
