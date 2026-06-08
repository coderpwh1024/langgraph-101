"""仅用于可视化 04-Memory 的 email_agent_memory 状态机结构。

使用桩(stub)节点函数还原拓扑，避免导入 email_agent.py 时触发模型调用。
运行: python notebooks/201/draw_memory_graph.py
"""
from typing import TypedDict, Literal, Annotated
from pathlib import Path

from langgraph.constants import END, START
from langgraph.graph import StateGraph
from langgraph.graph.message import AnyMessage, add_messages


class State(TypedDict):
    email_input: dict
    classification_decision: Literal["ignore", "respond", "notify"]
    messages: Annotated[list[AnyMessage], add_messages]
    loaded_memory: str


# ---- 桩节点（仅占位，保持与原文件同名以还原结构）----
def load_memory(state): ...
def triage(state): ...
def human_input(state): ...
def email_agent(state): ...
def create_memory(state): ...


# ---- 条件路由（与 email_agent.py 中一致）----
def handle_classification(state):
    if state["classification_decision"] == "notify":
        return "human_input"
    elif state["classification_decision"] == "respond":
        return "email_agent"
    else:
        return END


def handle_human_input(state):
    if state["classification_decision"] == "respond":
        return "email_agent"
    else:
        return END


def should_create_memory(state):
    return "create_memory"  # or END


# ---- 构建工作流（与 04 部分完全相同的边）----
wf = StateGraph(State)
wf.add_node("triage", triage)
wf.add_node("human_input", human_input)
wf.add_node("email_agent", email_agent)
wf.add_node("load_memory", load_memory)
wf.add_node("create_memory", create_memory)

wf.add_edge(START, "load_memory")
wf.add_edge("load_memory", "triage")
wf.add_conditional_edges("triage", handle_classification, {
    "human_input": "human_input",
    "email_agent": "email_agent",
    END: END,
})
wf.add_conditional_edges("human_input", handle_human_input, {
    "email_agent": "email_agent",
    END: END,
})
wf.add_conditional_edges("email_agent", should_create_memory, {
    "create_memory": "create_memory",
    END: END,
})

graph = wf.compile()

# 1) 打印 mermaid 文本
print(graph.get_graph().draw_mermaid())

# 2) 生成 PNG（需要联网调用 mermaid.ink）
out = Path(__file__).resolve().parent / "04_memory_graph.png"
try:
    out.write_bytes(graph.get_graph().draw_mermaid_png())
    print(f"\n已生成图片: {out}")
except Exception as e:
    print(f"\nPNG 生成失败(可能无网络): {e}")
