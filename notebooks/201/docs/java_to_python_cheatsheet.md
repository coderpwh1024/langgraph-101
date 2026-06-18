# Java → Python / LangGraph 对照速查

> 面向有 Java 背景的工程师，结合本项目 `research_agent.py` 的真实代码。
> 左边 Java，右边 Python / LangGraph，重点标注**差异**与**易踩的坑**。

---

## 一、语言层面（Java vs Python）

### 1. 类型注解：强制 vs 提示

```java
// Java：编译器铁律，写错编译不过
Command researcherTools(State state, Config config) { ... }
```

```python
# Python：只是提示（hint），运行时不检查
async def researcher_tools(state, config) -> Command[Literal["researcher", "compress_research"]]:
```

**坑**：`goto="compress_search"` 与注解里的 `"compress_research"` 不一致时，Python 不报错，跑到那一步才炸。注解骗不了人，但也帮不了你。

### 2. 真值判断：空集合即「假」

```java
if (toolCalls != null && !toolCalls.isEmpty()) { ... }
```

```python
has_tool_calls = bool(most_recent_message.tool_calls)   # 空列表 / None 都 → False
if not has_tool_calls and not has_native_search:
```

**坑**：`0`、`""`、`[]`、`{}`、`None` 全部为假。`if not x:` 区分不了「没值」和「值就是 0」。判 `None` 用 `is None` / `is not None`。

### 3. 字符串拼接：f-string 优先

```java
String s = String.format("%s %d", a, b);
```

```python
return f"{now:%a} {now:%b} {now.day} {now:%Y}"   # 格式化直接内嵌
```

### 4. 异常捕获：抓具体类型，多类型用元组

```java
catch (AttributeError | TypeError e) { ... }
```

```python
except (AttributeError, TypeError):   # 注意是元组
    return False
```

**注意**：裸抓 `except Exception as e` 是兜底大类，本项目规范不推荐，除非确实要拦住所有工具异常。

### 5. 缺省取值：dict.get

```java
state.getOrDefault("tool_call_iterations", 0) + 1;
```

```python
state.get("tool_call_iterations", 0) + 1
```

**坑**：可变默认参数 `def f(x=[])` 是 Python 著名陷阱——`[]` 全局共享一份，被改一次永久污染。用 `None` 占位：

```python
def f(items: list | None = None):
    if items is None:
        items = []
```

### 6. 鸭子类型 vs 接口

```java
// Java：必须实现 Tool 接口的 getName()
tool.getName();
```

```python
# Python：不问类型，只问「有没有这个属性」
tool.name if hasattr(tool, "name") else tool.get("name", "web_search")
```

**坑**：`tools` 列表里混着 `@tool` 对象和 `dict`（如 `{"type": "web_search_preview"}`），所以才用 `hasattr` 兜底。Java 里不可能把两种类型塞进同一个 `List<Tool>`。

### 7. 字典推导式

```java
Map<String, Tool> m = tools.stream()
    .collect(Collectors.toMap(Tool::getName, t -> t));
```

```python
tools_by_name = {tool.name: tool for tool in tools}   # 一行搞定
```

---

## 二、并发：async vs 线程

```java
CompletableFuture<Response> f = model.invokeAsync(messages);
Response r = f.get();
```

```python
response = await research_model.ainvoke(messages)
```

**关键差异**：Python 的 `async` 是**单线程事件循环**，不是多线程。它专治网络 IO（如 LLM 调用），不能加速 CPU 计算。`async` 会「传染」——只要某个函数是 `async`，调用它的整条链路都得 `async` + `await`。

| Java | Python |
| --- | --- |
| `CompletableFuture` / 线程池 | `async def` / `await` |
| `.get()` 阻塞取结果 | `await` 挂起协程 |
| 真并行（多核） | 并发不并行（单线程切换） |
| LangChain 同步方法 `.invoke()` | 异步版加前缀 `a`：`.ainvoke()` |

---

## 三、LangGraph 特有概念（Java 里无直接对应物）

### 1. State 是 TypedDict + reducer，不是 POJO

```python
class ResearcherState(TypedDict):
    researcher_messages: Annotated[List[MessageLikeRepresentation], operator.add]
    tool_call_iterations: int
```

- `Annotated[..., operator.add]` 中的 `operator.add` 是 **reducer**：节点返回 `{"researcher_messages": [response]}` 时，框架**自动 append** 而非覆盖。
- Java 类比：像给字段挂了「合并策略」，但 Java 没有这种声明式机制，得自己 `list.addAll()`。

### 2. 节点 = 函数，返回 dict 即「更新状态」

```python
return {
    "researcher_messages": [response],            # 走 operator.add → 追加
    "tool_call_iterations": state.get(...) + 1,   # 普通字段 → 覆盖
}
```

返回的 dict 不是「全量状态」，而是「这次要改哪些字段」（partial update）。

### 3. Command(goto=...) = 代码里的动态路由

```python
return Command(goto="compress_research")
```

类似工作流引擎里「显式指定下一个节点」。返回类型 `Command[Literal["researcher", "compress_research"]]` 用 `Literal` 把「合法的下一跳」写进类型里——Python 用类型注解模拟「枚举式路由」。

### 4. Schema 即 Prompt（最反直觉的一点）

```python
@tool(description="用于研究规划的战略性反思工具")
def think_tool(reflection: str) -> str:
    """每次搜索后调用此工具……

    Args:
        reflection: 对当前研究进展与后续步骤的详细反思。
    """
```

Java 的 Javadoc 写不写不影响运行；而这里的 `description` 和 docstring 会被序列化成 **JSON Schema 发给大模型**，直接决定模型调不调、怎么调这个工具。所以 docstring 是运行时数据，不是注释——必须写准。

---

## 四、最容易让 Java 程序员栽的 5 个坑

| # | 坑 | 说明 |
| --- | --- | --- |
| 1 | 类型注解不校验 | `goto` 拼错、返回类型不符，运行时才炸 |
| 2 | 可变默认参数 | `def f(x=[])` 的 `[]` 全局共享一份，改一次永久污染 |
| 3 | `==` vs `is` | 判 `None` 用 `is None`，别用 `==` |
| 4 | import 即执行 | 模块顶层的 `load_dotenv()`、`print` 在 import 时就跑了，顶层代码 = 副作用 |
| 5 | 缩进即语法 | 没有 `{}`，缩进错 = 逻辑错，且无编译期报错 |
