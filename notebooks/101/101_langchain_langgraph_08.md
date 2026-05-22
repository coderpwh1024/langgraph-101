# 101_langchain_langgraph_08 技术知识点总结

> 本文档对应源码 `101_langchain_langgraph_08.py`，这是一个用 **LangGraph 构建的 ReAct 风格工具调用 Agent** 的完整示例。

## 目录

- [整体概览](#整体概览)
- [1. 工具定义（Tool）](#1-工具定义tool)
- [2. 状态定义（State）](#2-状态定义state)
- [3. 节点（Node）](#3-节点node)
- [4. 模型绑定工具](#4-模型绑定工具)
- [5. 图的构建与条件路由](#5-图的构建与条件路由)
- [6. ReAct 执行循环](#6-react-执行循环)
- [7. 调用与结果展示](#7-调用与结果展示)
- [核心要点速查](#核心要点速查)

---

## 整体概览

本文件展示了 LangGraph 的核心范式——用 `StateGraph` + `TypedDict 状态` + `add_messages reducer` + `ToolNode` + `条件边`，搭建出一个能自主多轮调用工具的 ReAct Agent，本质上是手动实现了 `create_react_agent` 的内部结构。

Agent 具备两个能力：查询天气、按类型推荐电影。

---

## 1. 工具定义（Tool）

```python
@tool
def get_weather(latitude: float, longitude: float) -> str:
    """获取指定坐标的当前温度（华氏度）和天气代码。..."""
```

| 知识点 | 说明 |
| --- | --- |
| `@tool` 装饰器 | 来自 `langchain_core.tools`，把普通 Python 函数转成 LLM 可调用的工具 |
| docstring 即工具说明 | 函数 docstring 会作为工具描述传给 LLM，直接影响模型何时调用、如何调用 |
| 类型注解很关键 | 参数类型注解（`latitude: float`）用于生成工具的 JSON Schema，模型据此填参 |
| 返回值序列化 | 工具输出统一为字符串，结构化数据需手动 `json.dumps()` |

**两个工具的风格对比：**

- `get_weather`：调用真实外部 API（open-meteo），返回 `json.dumps(result)`。
- `search_movies`：用本地字典模拟数据，演示工具的不同实现方式。

**技巧：通过工具描述约束模型输出。** `get_weather` 的 docstring 中明确要求「不要直接输出 `weather_code` 数字，请翻译成中文天气描述」，这是一种通过工具描述对模型最终回复做约束的实用手法。

---

## 2. 状态定义（State）

```python
class State(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]
```

- **`TypedDict` 定义图的共享状态**：是 LangGraph 节点之间传递数据的结构。
- **`Annotated[..., add_messages]` —— reducer（归约器）**：核心概念。`add_messages` 决定了当节点返回 `messages` 时，是**追加**而非**覆盖**到现有列表，并能正确处理消息的去重 / 更新。
- **`AnyMessage`**：各类消息（System / Human / AI / Tool）的统一类型。

> ⚠️ 注意：源码第 12 行 `from langgraph.managed.is_last_step import RemainingSteps` 实际未被使用，可清理。

---

## 3. 节点（Node）

### Assistant 节点 —— LLM 推理节点

```python
def assistant(state: State):
    system_prompt = """你是一个有用的助手，可以查询天气并推荐电影"""
    all_messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response = model_with_tools.invoke(all_messages)
    return {"messages": [response]}
```

- 每次调用都**动态拼接 `SystemMessage` + 历史消息**（system prompt 不存进 state）。
- 节点返回的是 **state 的部分更新**（`{"messages": [...]}`），交给 reducer 合并。

### ToolNode —— 预构建工具执行节点

```python
tool_node = ToolNode(tools)
```

- `langgraph.prebuilt.ToolNode` 自动解析上一条 AIMessage 里的 `tool_calls`，执行对应工具，并把结果包装成 `ToolMessage` 写回 state。
- 无需手写工具分发逻辑，开箱即用。

---

## 4. 模型绑定工具

```python
model_with_tools = model.bind_tools(tools)
```

- **`bind_tools`** 把工具的 schema 注入模型，使模型具备「函数调用」能力。
- 绑定后，模型输出 AIMessage 时可能携带 `tool_calls` 字段。

---

## 5. 图的构建与条件路由

```python
builder = StateGraph(State)
builder.add_node("assistant", assistant)
builder.add_node("tool_node", tool_node)

builder.add_edge(START, "assistant")

builder.add_conditional_edges(
    "assistant", should_continue,
    {"continue": "tool_node", "end": END}
)

builder.add_edge("tool_node", "assistant")
agent = builder.compile(name="agent")
```

| 知识点 | 说明 |
| --- | --- |
| `StateGraph` | 图的构建器，泛型参数为 State |
| `add_edge` 普通边 | 固定流向（`START→assistant`、`tool_node→assistant`） |
| `add_conditional_edges` 条件边 | 根据路由函数返回值映射到不同目标节点，实现分支 |
| `START` / `END` | 来自 `langgraph.constants`，图的入口与出口哨兵节点 |
| `compile()` | 把图编译成可执行的 `agent`（Runnable） |

**路由函数 `should_continue`：**

```python
def should_continue(state: State):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "continue"   # 有工具调用 → 执行工具
    else:
        return "end"        # 无工具调用 → 结束
```

`tool_node → assistant` 形成**循环**，构成 ReAct 的「思考→行动→观察→再思考」闭环。

---

## 6. ReAct 执行循环

```
START → assistant ──(有 tool_calls)──→ tool_node ──┐
            ↑                                       │
            └───────────────────────────────────────┘
            └──(无 tool_calls)──→ END
```

一次 `invoke` 中，模型可多轮调用工具，直到生成不含工具调用的最终回答。本例会调用 `get_weather` + `search_movies` 两个工具。

---

## 7. 调用与结果展示

```python
question = "今天旧金山（北纬37.77°，西经122.42°）的天气怎么样？有什么好看的科幻电影推荐吗？"
result = agent.invoke({"messages": HumanMessage(content=question)})

for message in result["messages"]:
    message.pretty_print()
```

- `invoke` 传入初始 state；`messages` 可直接传单条消息（reducer 会处理成列表）。
- `pretty_print()`：消息对象的便捷方法，格式化打印整条消息链，便于观察 System / Human / AI / Tool 的完整轨迹。

---

## 核心要点速查

| 概念 | 作用 |
| --- | --- |
| `@tool` | 把函数封装为 LLM 可调用工具 |
| `TypedDict` State | 定义图的共享状态结构 |
| `add_messages` reducer | 控制 messages 字段为「追加」语义 |
| `bind_tools` | 让模型获得函数调用能力 |
| `ToolNode` | 预构建节点，自动执行工具调用 |
| `StateGraph` | 构建有状态的图 |
| `add_conditional_edges` | 实现基于状态的动态路由 |
| `START` / `END` | 图的入口 / 出口 |
| `compile()` | 生成可执行 Agent |

**一句话总结**：本文件用 LangGraph 手动搭建了一个 ReAct Agent，核心是「LLM 节点 ↔ 工具节点」之间由条件边驱动的循环，等价于 `create_react_agent` 的内部实现。
