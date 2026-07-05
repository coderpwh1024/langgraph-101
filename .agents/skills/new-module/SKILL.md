---
name: new-module
description: Use when scaffolding a new LangGraph/LangChain learning module (.py) in this repo (e.g. "新建一个学习模块", "scaffold a new graph script", "新建 102/202 脚本"). Generates a runnable script matching the 101/201 conventions — sys.path injection, model import, sectioned print banners, StateGraph + compile + invoke + pretty_print.
---

# 新模块脚手架 (new-module)

为本仓库新建一个**可独立运行的 LangGraph 学习脚本**，复刻 `notebooks/101`、`notebooks/201` 已有脚本的统一结构。目标不是写业务系统，而是「教学示例 + 跑通即看结果」。

## 使用前先问清 3 件事（如用户未说明）

1. **放在哪个系列目录**：`notebooks/101/`（基础）还是 `notebooks/201/`（进阶 Agent/记忆），或新目录。
2. **文件名 / 主题**：如 `103_streaming.py`、`202_subgraph.py`。沿用「序号_主题」命名。
3. **要演示几个递进部分**：每个部分对应一段 `print("---0X-xxx---")` 分隔的可运行代码块。

## 必须遵守的仓库约定（从现有脚本提炼）

### 文件头（固定模板，注意用 `__file__`）

```python
import sys
from pathlib import Path
from typing import TypedDict, Annotated, List
# —— 按主题再补 langchain / langgraph 相关 import ——
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, add_messages
from langgraph.constants import START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from langsmith import uuid7

# 把 notebooks/ 注入 sys.path，才能 `from utils.xxx import ...`
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.models import model
```

> ⚠️ `101_langchain_langgraph.py` 里写的是 `Path().resolve()`（漏了 `__file__`，是已知 bug）。新脚手架**一律用 `Path(__file__).resolve()`**，否则换工作目录就会找不到 `utils`。

### 图可视化（如需）

```python
from utils.utils import show_graph   # 注意是 utils.utils，不是 notebooks.utils.utils
...
show_graph(compiled_graph, xray=True)
```

### 基础设施 & 调用范式

```python
checkpointer = MemorySaver()
in_memory_store = InMemoryStore()

# 每个部分用醒目分隔条，序号从 01 开始
print("---------------------------------01-XXX---------------------------------")

class State(TypedDict):
    messages: Annotated[List[HumanMessage], add_messages]   # add_messages reducer

# ...build graph...
workflow = StateGraph(State)
workflow.add_node(...)
workflow.add_edge(START, ...)
graph = workflow.compile(checkpointer=checkpointer, store=in_memory_store)

config = {"configurable": {"thread_id": uuid7()}}
result = graph.invoke({"messages": [HumanMessage(content="...")]}, config=config)
for message in result["messages"]:
    message.pretty_print()
```

## 工作步骤

1. 确认目录 / 文件名 / 各部分主题。
2. 用上面模板生成脚本：文件头 → 基础设施 → 按部分写 `print("---0X---")` 分隔的可运行代码块，每块结尾都 `invoke` 一次并 `pretty_print` 输出，确保「单文件跑通即可见效」。
3. 中文注释，风格与现有脚本一致（节点/工具上方一行中文注释）。
4. **不要**自动运行（脚本会联网下载 Chinook 数据并消耗 DASHSCOPE_API_KEY 额度）。生成后提示用户：在 `notebooks/` 目录下 `python 1xx/xxx.py` 运行，需先设好 `DASHSCOPE_API_KEY`。

## 完成后

可提醒用户接着用 `/tech-summary` 为新模块生成技术总结。
