# LangChain & LangGraph 技术知识点总结

> 本文档基于以下三份源码的整体阅读，系统梳理 LangChain / LangGraph 的核心技术知识点：
>
> - **`101_langchain_langgraph.py`** —— 入门主线，6 大模块覆盖「模型调用 → 消息 → 工具 → Agent → 记忆 → 流式」
> - **`101_langchain_langgraph_07.py`** —— `create_agent` 实战：多工具 + 记忆的个人助理
> - **`101_langchain_langgraph_08.py`** —— 用 `StateGraph` 手动搭建 ReAct Agent（已有独立文档 `101_langchain_langgraph_08.md`）
>
> 配套依赖：`utils/models.py`（多厂商模型配置）、`utils/utils.py`（图可视化与示例数据库）。

---

## 目录

- [学习主线总览](#学习主线总览)
- [第一部分：基础入门（101_langchain_langgraph.py）](#第一部分基础入门101_langchain_langgraphpy)
  - [0. 环境与模型准备](#0-环境与模型准备)
  - [1. 基础模型调用](#1-基础模型调用)
  - [2. 消息类型与多轮对话](#2-消息类型与多轮对话)
  - [3. 工具（Tool）](#3-工具tool)
  - [4. create_agent —— 预构建 Agent](#4-create_agent--预构建-agent)
  - [5. Agent 记忆与会话状态](#5-agent-记忆与会话状态)
  - [6. 流式响应（Streaming）](#6-流式响应streaming)
- [第二部分：create_agent 实战（101_langchain_langgraph_07.py）](#第二部分create_agent-实战101_langchain_langgraph_07py)
- [第三部分：手动构建 ReAct 图（101_langchain_langgraph_08.py）](#第三部分手动构建-react-图101_langchain_langgraph_08py)
- [两条路线对比：create_agent vs StateGraph](#两条路线对比create_agent-vs-stategraph)
- [配套工具模块](#配套工具模块)
- [核心 API 速查表](#核心-api-速查表)
- [常见易错点与建议](#常见易错点与建议)

---

## 学习主线总览

三份文件构成一条由浅入深的学习路径：

```
101_langchain_langgraph.py      基础概念全景
        │  模型 → 消息 → 工具 → Agent → 记忆 → 流式
        ▼
101_langchain_langgraph_07.py   create_agent 的"高层封装"用法
        │  一行 create_agent 搞定多工具 + 记忆
        ▼
101_langchain_langgraph_08.py   StateGraph 的"底层手搓"用法
           揭开 create_agent 的内部黑盒：节点 + 状态 + 条件边
```

核心结论：**`create_agent` 是 `StateGraph` 搭建 ReAct 循环的高层封装**。文件 07 用封装，文件 08 手搓，二者本质等价——理解了 08 就理解了 07 的内部原理。

---

## 第一部分：基础入门（101_langchain_langgraph.py）

该文件按 6 个递进模块组织，是整套知识体系的骨架。

### 0. 环境与模型准备

```python
project_root = Path().resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
from utils.models import model

import warnings
warnings.filterwarnings('ignore', message="LangSmith now uses UUID v7")
```

| 知识点 | 说明 |
| --- | --- |
| 动态 `sys.path` | 把项目根目录加入模块搜索路径，使 `from utils.models import model` 在子目录中可用 |
| 模型集中配置 | `model` 统一在 `utils/models.py` 定义，业务代码与模型厂商解耦 |
| 警告过滤 | 屏蔽 LangSmith 的 UUID v7 提示，保持输出整洁 |
| 耗时统计 | `datetime.datetime.now()` 前后差值，简单度量一次调用的延迟 |

### 1. 基础模型调用

```python
result = model.invoke("解释一下什么是智能体?")
result.pretty_print()
```

- **`model.invoke(...)`**：LangChain 模型的统一同步调用入口，可直接传字符串。
- **返回值是 `AIMessage` 对象**，而非纯字符串——内部含 `content`、`tool_calls`、`response_metadata` 等。
- **`pretty_print()`**：消息对象的便捷方法，格式化打印消息（带角色标签），便于调试观察。

### 2. 消息类型与多轮对话

```python
messages = [
    SystemMessage(content="你是一个乐于助人的 AI 助手……"),
    HumanMessage(content="什么是智能体（agent）？")
]
resultMessage = model.invoke(messages)

# 多轮对话：把上一轮回复 + 新问题继续追加
messages.append(resultMessage)
messages.append(HumanMessage(content="请用中文给我举一个例子"))
resultMessage = model.invoke(messages)
```

| 消息类型 | 角色 | 用途 |
| --- | --- | --- |
| `SystemMessage` | system | 设定 AI 的人设、行为约束（仅一条，置于开头） |
| `HumanMessage` | user | 用户输入 |
| `AIMessage` | assistant | 模型回复（`invoke` 的返回值） |
| `ToolMessage` | tool | 工具执行结果（见下一节） |

**多轮对话的本质**：LLM 是无状态的，"记忆"靠**手动维护一个消息列表**实现——每轮把历史消息 + 新消息整体重新传给模型。

### 3. 工具（Tool）

工具让模型能"调用外部能力"。本节展示了**完整的手动工具调用流程**。

#### 3.1 用 `@tool` 定义工具

```python
@tool
def search_movies(genre: str) -> str:
    """按类型搜索电影"""
    movies = {"科幻": "沙丘, 星际穿越, 银翼杀手 2049", ...}
    return movies.get(genre, "没有找到此类型的电影")

@tool
def get_weather(latitude: float, longitude: float) -> str:
    """获取指定坐标的当前温度（华氏度）和天气代码。……"""
    weather = requests.get(url, params).json()["current"]
    return json.dumps(result)
```

| 知识点 | 说明 |
| --- | --- |
| `@tool` 装饰器 | 来自 `langchain_core.tools`，把普通函数封装为 LLM 可调用工具 |
| docstring 即工具说明 | 函数 docstring 作为工具描述传给 LLM，**直接影响模型何时调用、如何调用** |
| 类型注解生成 Schema | 参数注解（`latitude: float`）用于生成工具的 JSON Schema，模型据此填参 |
| 返回值统一为字符串 | 结构化数据需手动 `json.dumps()` 序列化 |
| 本地工具 vs 远程工具 | `search_movies` 用字典模拟；`get_weather` 调用真实 API（open-meteo） |

**实用技巧——用 docstring 约束模型输出**：`get_weather` 的 docstring 中明确写"不要直接输出 `weather_code` 数字，请翻译成中文天气描述、温度补充摄氏度"，这是通过工具描述反向约束模型最终回复的有效手法。

#### 3.2 绑定工具与手动调用流程

```python
tools = [search_movies, get_weather]
model_with_tools = model.bind_tools(tools)
resultTool = model_with_tools.invoke(message)
print("工具:", resultTool.tool_calls)
```

完整的"手动 ReAct 一轮"流程，揭示了 Agent 的底层机制：

```
1. bind_tools(tools)            把工具 Schema 注入模型
2. model_with_tools.invoke()    模型返回带 tool_calls 的 AIMessage
3. 读取 tool_calls[0]，按 name 分发，执行对应工具函数
4. 把结果包装成 ToolMessage(content=result, tool_call_id=tool_call["id"])
5. 把 [HumanMessage, AIMessage(含tool_calls), ToolMessage] 一起回传模型
6. 模型基于工具结果生成最终自然语言回复
```

**关键点**：`ToolMessage` 必须带 `tool_call_id`，与 `AIMessage` 中的 `tool_calls[*]["id"]` 一一对应，模型才能把"结果"和"调用"配对。

> 这一手动流程在后续的 `create_agent` 和 `ToolNode` 中被自动化——理解它就理解了 Agent 的内核。

### 4. create_agent —— 预构建 Agent

```python
agent = create_agent(
    model=model,
    tools=[get_weather, search_movies],
    system_prompt="""你是一个能查询天气和推荐电影的智能助手"""
)
agentResult = agent.invoke({
    "messages": [HumanMessage(content="纽约的天气怎么样?…另外推荐几部科幻电影")]
})
for message in agentResult["messages"]:
    message.pretty_print()
```

| 知识点 | 说明 |
| --- | --- |
| `create_agent` | 来自 `langchain.agents`，一行代码构建完整 ReAct Agent |
| 自动化第 3 节的全部手工流程 | 工具分发、`ToolMessage` 包装、多轮循环全部内置 |
| 输入/输出结构 | 输入 `{"messages": [...]}`；输出同样是含完整消息链的 `dict` |
| 自主多轮 | 一次 `invoke` 内，模型可连续调用多个工具直到产出最终答案 |

`create_agent` 把第 3 节的 6 步手动流程完全封装——这是"高层路线"。

### 5. Agent 记忆与会话状态

```python
checkpointer = MemorySaver()
agent_with_memory = create_agent(
    model=model, tools=[...], system_prompt="你是一个智能助手!",
    checkpointer=checkpointer
)
config = {"configurable": {"thread_id": uuid7()}}

result1 = agent_with_memory.invoke({"messages": [...]}, config=config)  # "我叫 Alice"
result2 = agent_with_memory.invoke({"messages": [...]}, config=config)  # "我叫什么？" → 记得

new_config = {"configurable": {"thread_id": uuid7()}}                   # 换 thread_id
result3 = agent_with_memory.invoke({"messages": [...]}, config=new_config)  # → 不记得
```

| 知识点 | 说明 |
| --- | --- |
| `MemorySaver` | `langgraph.checkpoint.memory` 提供的**内存级检查点存储**（进程结束即丢失） |
| `checkpointer` 参数 | 传给 `create_agent` 后，Agent 自动按线程持久化对话状态 |
| `thread_id` | 会话隔离的唯一键，置于 `config["configurable"]` 中 |
| `uuid7()` | `langsmith` 提供的时间有序 UUID，适合做线程 ID |

**核心机制**：
- **同一 `thread_id`** → 状态累积，Agent "记得"之前对话（`result2` 能答出名字）。
- **不同 `thread_id`** → 全新会话，互相隔离（`result3` 答不出名字）。
- 这就是多用户 / 多会话隔离的标准做法：每个会话一个 `thread_id`。

> 生产环境可换成 `SqliteSaver` / `PostgresSaver` 实现持久化，接口一致。

### 6. 流式响应（Streaming）

`stream()` 替代 `invoke()`，边生成边输出。本节演示两种 `stream_mode`：

#### 6.1 `stream_mode="updates"` —— 按节点步骤流式

```python
for chunk in agent.stream({"messages": [...]}, stream_mode="updates"):
    for node_name, data in chunk.items():
        print(f"Step:{node_name}")
        # 区分是工具调用步骤还是文本回复步骤
        if hasattr(message, 'tool_calls') and message.tool_calls:
            print(f" Tool call:{message.tool_calls[0]['name']}")
        elif hasattr(message, 'content'):
            print(f"Content:{message.content[:100]}...")
```

- 每个 `chunk` 是 `{节点名: 状态更新}`，**粒度为"节点"**。
- 适合展示 Agent 的执行轨迹（哪一步调了哪个工具）。

#### 6.2 `stream_mode="messages"` —— 按 token 流式

```python
for token, metadata in agent.stream({"messages": [...]}, stream_mode="messages"):
    if metadata.get('langgraph_node') == 'model':
        for block in token.content_blocks:
            if block.get('type') == 'text' and block.get('text'):
                print(block['text'], end='', flush=True)
```

- 每次产出 `(token, metadata)`，**粒度为"token"**，实现打字机效果。
- `metadata['langgraph_node']` 用于过滤只输出 `model` 节点的内容。
- `token.content_blocks` 按块遍历，仅取 `type == 'text'` 的文本块。

| `stream_mode` | 粒度 | 典型用途 |
| --- | --- | --- |
| `"updates"` | 节点步骤 | 展示 Agent 执行流程 / 进度 |
| `"messages"` | token | 前端打字机效果 |

---

## 第二部分：create_agent 实战（101_langchain_langgraph_07.py）

文件 07 是第一部分知识的综合应用——用 `create_agent` 构建一个**带记忆的多工具个人助理**。

### 工具集（3 个）

```python
@tool
def get_weather(latitude, longitude) -> str: ...        # 真实 API
@tool
def get_user_preferences(user_id: str) -> str: ...       # 查用户偏好（字典模拟）
@tool
def book_recommendation(genre, user_preferences="") -> str: ...  # 个性化电影推荐
```

新增知识点：
- **带默认值的工具参数**：`book_recommendation(genre, user_preferences="")` 中 `user_preferences` 有默认值，对模型而言是可选参数。
- **工具协作设计**：`get_user_preferences` 的输出可作为 `book_recommendation` 的输入——多工具串联完成"查偏好 → 个性化推荐"的链路。

### 一行构建带记忆的 Agent

```python
assistant = create_agent(
    model=model,
    tools=[get_user_preferences, book_recommendation, get_weather],
    system_prompt="""你是一个乐于助人的个人助理。
    你可以：
    - 查询任意城市的天气
    - 查找用户偏好设置
    - 根据偏好推荐电影
    请始终保持友好的态度，并根据用户偏好对回复进行个性化处理。""",
    checkpointer=MemorySaver()      # 直接内联，无需先存变量
)
config = {"configurable": {"thread_id": uuid7()}}
result = assistant.invoke({"messages": [{"role": "user", "content": "..."}]}, config=config)
```

| 知识点 | 说明 |
| --- | --- |
| `system_prompt` 写法 | 用多行字符串清晰罗列 Agent 的能力清单与行为风格，是 prompt 工程的良好实践 |
| `checkpointer` 内联 | `MemorySaver()` 可直接作为参数传入，无需单独变量 |
| 消息的 dict 写法 | `{"role": "user", "content": "..."}` 与 `HumanMessage(content="...")` 等价，更简洁 |
| `result['messages'][-1].content` | 取最后一条消息的文本内容 = Agent 的最终回复 |

**与第一部分的关系**：文件 07 = 第 3 节（工具）+ 第 4 节（create_agent）+ 第 5 节（记忆）的组合实战，完全走"高层封装"路线。

> ⚠️ 源码注意：第 88 行用户问题字符串有重复粘贴（"另外，旧金山的天气怎么样？（北纬37." 出现两次），属笔误，不影响运行但建议清理。

---

## 第三部分：手动构建 ReAct 图（101_langchain_langgraph_08.py）

文件 08 不用 `create_agent`，而是用 **`StateGraph` 从零手搓 ReAct Agent**，揭开高层封装的黑盒。已有独立文档 `101_langchain_langgraph_08.md`，此处提炼要点。

### 核心五件套

```python
# ① 状态：用 TypedDict + reducer 定义图的共享数据
class State(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]

# ② 节点 A：LLM 推理节点
def assistant(state: State):
    all_messages = [SystemMessage(content=system_prompt)] + state["messages"]
    return {"messages": [model_with_tools.invoke(all_messages)]}

# ③ 节点 B：工具执行节点（预构建）
tool_node = ToolNode(tools)

# ④ 路由函数：决定是否继续调用工具
def should_continue(state: State):
    return "continue" if state["messages"][-1].tool_calls else "end"

# ⑤ 组装图
builder = StateGraph(State)
builder.add_node("assistant", assistant)
builder.add_node("tool_node", tool_node)
builder.add_edge(START, "assistant")
builder.add_conditional_edges("assistant", should_continue,
                              {"continue": "tool_node", "end": END})
builder.add_edge("tool_node", "assistant")          # 关键：形成循环
agent = builder.compile(name="agent")
```

| 概念 | 作用 |
| --- | --- |
| `StateGraph` | 有状态图的构建器，泛型参数为 State |
| `TypedDict` State | 定义节点间传递的共享状态结构 |
| `Annotated[..., add_messages]` | **reducer**：让 `messages` 字段为"追加"语义而非"覆盖"，并处理消息去重/更新 |
| `add_node` | 注册节点（节点 = 一个接收 state、返回 state 部分更新的函数） |
| `add_edge` | 固定流向的普通边 |
| `add_conditional_edges` | 条件边：按路由函数返回值映射到不同目标，实现分支 |
| `ToolNode` | `langgraph.prebuilt` 预构建节点，自动解析 `tool_calls`、执行、包装 `ToolMessage` |
| `START` / `END` | `langgraph.constants` 提供的入口/出口哨兵节点 |
| `compile()` | 把图编译成可执行的 Runnable |

### ReAct 循环

```
START → assistant ──(有 tool_calls)──→ tool_node ──┐
            ↑                                       │
            └───────────────────────────────────────┘
            └──(无 tool_calls)──→ END
```

`tool_node → assistant` 这条回边构成 ReAct 的「思考 → 行动 → 观察 → 再思考」闭环。一次 `invoke` 中模型可多轮调用工具，直到产出不含 `tool_calls` 的最终回答。

**这正是 `create_agent` 的内部结构**——文件 08 手动实现了文件 04/07 一行封装背后的全部机制。

> ⚠️ 源码注意：第 12 行 `from langgraph.managed.is_last_step import RemainingSteps` 导入后未使用，可清理。

---

## 两条路线对比：create_agent vs StateGraph

| 维度 | `create_agent`（文件 04 / 07） | `StateGraph`（文件 08） |
| --- | --- | --- |
| 抽象层级 | 高层封装 | 底层手搓 |
| 代码量 | 一行构建 | 需手写状态/节点/边/路由 |
| 灵活性 | 标准 ReAct 循环 | 可自定义任意拓扑、节点逻辑 |
| 工具执行 | 内部自动 | 自己用 `ToolNode` 或手写 |
| 记忆 | 传 `checkpointer` 即可 | `compile(checkpointer=...)` |
| 适用场景 | 标准 Agent 快速落地 | 复杂工作流、需精细控制流程 |
| 关系 | = StateGraph ReAct 循环的封装 | create_agent 的内部实现 |

**选型建议**：标准工具调用 Agent 用 `create_agent`；需要自定义节点、分支、人工介入（human-in-the-loop）、并行等复杂编排时用 `StateGraph`。

---

## 配套工具模块

### `utils/models.py` —— 多厂商模型配置

```python
from dotenv import load_dotenv
load_dotenv(override=True)
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    model="qwen-plus",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
```

| 知识点 | 说明 |
| --- | --- |
| 当前启用 | 阿里云百炼 DashScope 的 `qwen-plus`，走 **OpenAI 兼容模式** |
| 兼容模式技巧 | 用 `ChatOpenAI` + 自定义 `base_url` 即可对接任意 OpenAI 兼容服务 |
| `.env` 管理密钥 | `load_dotenv(override=True)` 加载环境变量，`api_key` 不硬编码 |
| 多厂商可切换 | 文件中以注释形式预留 Anthropic / Azure OpenAI / AWS Bedrock / Google Vertex AI 配置 |
| 集中配置的价值 | 业务代码统一 `from utils.models import model`，换模型只改一处 |

### `utils/utils.py` —— 图可视化与示例数据库

```python
def show_graph(graph, xray=False):
    """渲染 LangGraph 的 mermaid 图，失败则回退到 ASCII 图"""

def get_engine_for_chinook_db():
    """下载 Chinook SQL 脚本，载入内存 SQLite，返回 SQLAlchemy engine"""
```

- `show_graph`：可视化已编译的图结构，IPython 环境下显示 PNG，失败回退 ASCII。
- `get_engine_for_chinook_db`：用 `StaticPool` 把 Chinook 示例库灌进内存 SQLite，常用于"Text-to-SQL" Agent 演示。

> ⚠️ 源码注意：`show_graph` 中 `dray_mermaid_png()` / `dray_asscli()` 疑似拼写错误，正确应为 `draw_mermaid_png()` / `draw_ascii()`，当前会触发异常分支。

---

## 核心 API 速查表

| API / 概念 | 来源 | 作用 |
| --- | --- | --- |
| `model.invoke()` | LangChain | 同步调用模型，返回 `AIMessage` |
| `model.stream()` | LangChain | 流式调用模型 |
| `model.bind_tools()` | LangChain | 给模型注入工具 Schema，获得函数调用能力 |
| `SystemMessage` / `HumanMessage` / `AIMessage` / `ToolMessage` | `langchain_core.messages` | 四类消息角色 |
| `@tool` | `langchain_core.tools` | 把函数封装为 LLM 可调用工具 |
| `pretty_print()` | 消息对象方法 | 格式化打印消息 |
| `create_agent()` | `langchain.agents` | 一行构建 ReAct Agent |
| `MemorySaver` | `langgraph.checkpoint.memory` | 内存级会话检查点存储 |
| `thread_id` | `config["configurable"]` | 会话隔离唯一键 |
| `uuid7()` | `langsmith` | 时间有序 UUID |
| `StateGraph` | `langgraph.graph` | 有状态图构建器 |
| `TypedDict` + `Annotated` | `typing` / `typing_extensions` | 定义带 reducer 的图状态 |
| `add_messages` | `langgraph.graph.message` | messages 字段的"追加"reducer |
| `ToolNode` | `langgraph.prebuilt` | 预构建工具执行节点 |
| `add_edge` / `add_conditional_edges` | `StateGraph` 方法 | 普通边 / 条件边 |
| `START` / `END` | `langgraph.constants` | 图的入口 / 出口哨兵 |
| `compile()` | `StateGraph` 方法 | 编译图为可执行 Runnable |

---

## 常见易错点与建议

| 类别 | 问题 | 建议 |
| --- | --- | --- |
| **工具描述** | docstring 写得含糊导致模型乱调工具 | docstring 要写清用途、参数、返回格式，必要时约束输出 |
| **ToolMessage** | 手动调用时漏传 `tool_call_id` | 必须与 `AIMessage.tool_calls[*]["id"]` 一一对应 |
| **记忆** | 误以为换 `thread_id` 还能记得上下文 | 不同 `thread_id` 完全隔离；同会话须复用同一 ID |
| **记忆持久化** | `MemorySaver` 进程退出即丢失 | 生产用 `SqliteSaver` / `PostgresSaver` |
| **状态 reducer** | 忘记 `add_messages`，messages 被覆盖 | 状态中的消息列表务必加 `Annotated[..., add_messages]` |
| **死代码** | 文件 08 导入 `RemainingSteps` 未用 | 及时清理无用 import |
| **拼写** | `utils.py` 的 `dray_*` 方法名拼错 | 应为 `draw_mermaid_png()` / `draw_ascii()` |
| **笔误** | 文件 07 第 88 行问题字符串重复粘贴 | 清理重复文本 |

---

## 一句话总结

这三份代码完整呈现了从 **「裸调用模型」→「手动工具调用」→「高层 `create_agent`」→「底层 `StateGraph` 手搓 ReAct」** 的学习闭环：`create_agent` 让你快速落地标准 Agent，`StateGraph` 让你掌握其内部原理并应对复杂编排——**先会用封装（07），再懂原理（08），才能游刃有余。**
