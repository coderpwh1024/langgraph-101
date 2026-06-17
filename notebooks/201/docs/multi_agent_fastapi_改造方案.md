# multi_agent.py → FastAPI 改造方案（含 SSE 流式）

> 目标：把 `notebooks/201/multi_agent.py` 这个「import 即运行」的教学 demo，
> 改造成一个可对外提供对话服务的 FastAPI 应用，支持 **SSE 流式输出** 与 **人在回路（中断/恢复）**。
> 本文档只描述方案，不含实现代码。

---

## 一、核心原则：建图与调用分离

当前脚本在模块加载时就做了三件「服务里绝不能在 import 时做」的事：

1. `requests.get(...)` 下载 Chinook SQL 并填充内存库；
2. 编译各个 graph；
3. 用写死的 `question` 直接 `invoke` 并 `pretty_print`。

改造后职责切分为两层：

| 时机 | 做什么 |
| --- | --- |
| **应用启动（lifespan，一次性）** | 建 db engine、初始化 `model`、`checkpointer`、`store`，编译 `multi_agent_final_graph`，挂到 `app.state` |
| **每次请求** | 仅 `graph.stream(payload, config)`，从请求体取 `message` / `customer_id` / `thread_id` |

> 建图逻辑（节点函数、边、`@tool`、prompt 常量）**原样迁移**，只删掉文件末尾所有 `question = "..."`、`invoke`、`for message in result: pretty_print()`、`show_graph(...)` 这些演示语句。

---

## 二、目录结构

```
app/
  __init__.py
  main.py          # FastAPI 实例 + lifespan + 路由挂载
  graphs.py        # 迁移自 multi_agent.py：节点/边/工具/prompt，导出 build_graph()
  deps.py          # 共享单例：model / db / checkpointer / store
  schemas.py       # Pydantic 请求/响应模型
  routers/
    chat.py        # /chat 与 /chat/resume 两个 SSE 端点
notebooks/201/multi_agent.py   # 教学脚本保留，改为 import app.graphs 复用同一份图
```

**一份图，两种入口**：`graphs.py` 是唯一的图定义来源；教学脚本和服务都 import 它。
教学脚本继续当「可运行的文档」，服务复用同一逻辑，避免两边漂移。

---

## 三、API 设计

会话状态靠 `thread_id` 串联——这是把无状态 HTTP 缝合成有状态多轮对话的唯一线索。

### 1. `POST /chat`（SSE）—— 首次提问 / 普通多轮

请求体：
```json
{ "message": "我最近一次购买花了多少钱？", "thread_id": null, "customer_id": null }
```
- `thread_id` 为空 → 后端用 `uuid7()` 新建一个，并在首个 SSE 事件里回传。
- `customer_id` 可空；为空时图会走 `verify_info` 验证流程（要电话号）。

### 2. `POST /chat/resume`（SSE）—— 回答中断（补电话号等）

请求体：
```json
{ "thread_id": "已有会话ID", "value": "我的电话号码是 +55 (12) 3923-5555" }
```
- 后端用 `graph.stream(Command(resume=value), config)` 从断点续跑。

> 拆成两个端点是因为语义不同：`/chat` 传 `{"messages":[HumanMessage]}`，
> `/chat/resume` 传 `Command(resume=...)`。也可合并为一个端点用字段区分，但分开更清晰。

---

## 四、难点：SSE 流式 + 中断 如何共存

这是整个改造最需要想清楚的地方。流式输出和「图可能中途挂起等用户输入」要在同一条 SSE 流里表达出来。

### SSE 事件类型设计

| event | data | 含义 |
| --- | --- | --- |
| `meta` | `{ "thread_id": "..." }` | 流的第一个事件，回传会话 ID（前端续接用） |
| `token` | `{ "delta": "部分文本" }` | LLM 增量 token |
| `interrupt` | `{ "prompt": "请提供您的电话号码", "thread_id": "..." }` | 图挂起，需要前端再发 `/chat/resume` |
| `done` | `{ "thread_id": "..." }` | 本轮跑完（图执行结束，无待执行节点） |
| `error` | `{ "message": "..." }` | 异常 |

### 后端生成逻辑（伪流程，非代码）

```
def event_stream(payload, config):
    先 yield meta(thread_id)
    for chunk in graph.stream(payload, config, stream_mode="messages"):
        # stream_mode="messages" 产出 (AIMessageChunk, metadata)
        把 chunk 的增量内容 yield 成 token 事件
    # 流结束后，关键一步：判断是「跑完」还是「停在中断」
    state = graph.get_state(config)
    if state.next:            # 还有待执行节点 → 被 interrupt 挂起
        yield interrupt(从 state.tasks 里取中断提示)
    else:
        yield done(thread_id)
```

要点：
- **`stream_mode="messages"`** 适合逐 token 推送（产出 message chunk + 元数据）；
  也可用 `stream_mode="updates"` 按节点粒度推送（更结构化，但不是逐字）。二选一或组合。
- **中断的判定不在 stream 内部，而在 stream 结束后** 看 `graph.get_state(config).next` 是否非空，
  以及 `state.tasks[].interrupts`。这是因为 `human_input` 节点抛出的 `interrupt()` 会让整张图存档退出。
- 前端拿到 `interrupt` 事件 → 收集用户输入 → 调 `/chat/resume`，新的 SSE 流继续。

---

## 五、必须解决的工程问题

| 问题 | demo 现状 | 服务里的处理 |
| --- | --- | --- |
| **阻塞调用** | `model.invoke` / `db.run` 同步阻塞 | SSE 用 **同步生成器** + `StreamingResponse`，FastAPI 自动在线程池跑，不卡事件循环。端点用 `def` 而非 `async def`，或显式 `run_in_threadpool` |
| **状态持久化** | `MemorySaver` + `InMemoryStore`（进程内存） | demo/单 worker 够用。**多 worker 或重启即丢**——生产换 `PostgresSaver` + Postgres store，且 `uvicorn --workers>1` 时必须用共享后端，否则中断会话会「找不到」 |
| **DB 初始化** | 每次 import `requests.get` 下载 | 移到 `lifespan` 启动钩子，进程内只下载一次；建议加本地缓存或预置 sqlite 文件 |
| **`customer_id`** | 写死 `1` | 从请求体/认证传入，注入 `state`；为空则触发验证流程 |
| **并发隔离** | 不涉及 | 每个会话独立 `thread_id`，checkpointer 按 thread 隔离；`store` 按 `("memory_profile", customer_id)` 命名空间隔离，天然多租户 |
| **超时/断连** | 不涉及 | SSE 长连接要处理客户端断开（FastAPI `request.is_disconnected()`），及时停止 `graph.stream` |

---

## 六、SSE 媒体细节（前端对接约定）

- 响应头：`Content-Type: text/event-stream`、`Cache-Control: no-cache`、`Connection: keep-alive`。
- 每条事件格式：`event: token\ndata: {"delta":"..."}\n\n`（两个换行结尾）。
- 前端用浏览器 `EventSource`（仅 GET）或 `fetch` + ReadableStream（支持 POST，推荐，因为要发 body）。
- 心跳：长时间无 token 时定期发注释行 `: ping\n\n` 防代理断连。

---

## 七、改造工作量清单（落地时按此拆任务）

- [ ] 抽离 `graphs.py`：迁移节点/边/工具/prompt，导出已编译 graph 与 `build_graph()`
- [ ] `deps.py`：model / db / checkpointer / store 单例，DB 下载逻辑搬进来
- [ ] `schemas.py`：`ChatRequest` / `ResumeRequest` / SSE 事件模型
- [ ] `main.py`：`lifespan` 里建库+编译图挂 `app.state`
- [ ] `routers/chat.py`：`/chat`、`/chat/resume` 两个 SSE 端点 + 事件生成器
- [ ] 中断判定逻辑：stream 结束后查 `state.next` / `state.tasks[].interrupts`
- [ ] 清理 demo：删 `multi_agent.py` 末尾所有 invoke/print/show_graph，改 import `app.graphs`
- [ ] （顺带）修 `supervisor_prompt` 的重复段落与未闭合 `<重要指示>` 标签
- [ ] （生产可选）换 Postgres checkpointer/store，配置化 model/DB

---

## 八、风险与注意点

1. **SSE + 中断的判定时机**：中断不会以 token 形式出现在流里，必须在 stream 结束后查状态——这是最容易写错的点。
2. **多 worker 下的 in-memory 状态**：上线前若仍用 `MemorySaver`，必须锁定单 worker，否则中断恢复随机失败。
3. **`db.run` 的 SQL 注入**：现有工具全是 f-string 拼接，对外开放后注入风险被放大，生产应改参数化查询。
4. **结构化输出在流式下不逐字**：`verify_info` / `create_memory` 用了 `with_structured_output`，这类调用是整块返回，不适合逐 token，流式只对 supervisor 的自然语言回复有意义。
