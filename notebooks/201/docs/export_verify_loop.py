"""
只导出 multi_agent.py 第 03 部分「添加用户验证-LOOP」那张图（multi_agent_verify）的真实结构 PNG。

说明：
- draw_mermaid_png() / draw_ascii() 只读图的拓扑（节点 + 边），不执行任何节点，
  因此这里用占位函数按 multi_agent.py:542-557 完全一致的拓扑重建该图，
  不调用 LLM / 不连数据库，零 API 费用。

运行：python export_verify_loop.py
"""
import sys
from pathlib import Path
from typing import TypedDict, Annotated

from langgraph.constants import END, START
from langgraph.graph import StateGraph
from langgraph.graph.message import AnyMessage, add_messages

OUT_DIR = Path(__file__).resolve().parent / "image"
OUT_DIR.mkdir(exist_ok=True)


# ---- State / InputState（与原文件一致，仅取构图所需字段）-------------------
class State(TypedDict):
    customer_id: str
    messages: Annotated[list[AnyMessage], add_messages]


class InputState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


# ---- 节点占位函数（绝不执行，仅用于建图）----------------------------------
def verify_info(state: State):
    return state


def human_input(state: State):
    return state


def supervisor(state: State):
    return state


def should_interrupt(state: State):
    return "continue"


# ---- 与 multi_agent.py:542-557 完全一致的拓扑 ------------------------------
multi_agent_verify = StateGraph(State, input_schema=InputState)
multi_agent_verify.add_node("verify_info", verify_info)
multi_agent_verify.add_node("human_input", human_input)
multi_agent_verify.add_node("supervisor", supervisor)

multi_agent_verify.add_edge(START, "verify_info")
multi_agent_verify.add_conditional_edges(
    "verify_info",
    should_interrupt,
    {
        "continue": "supervisor",
        "interrupt": "human_input",
    },
)
multi_agent_verify.add_edge("human_input", "verify_info")
multi_agent_verify.add_edge("supervisor", END)

graph = multi_agent_verify.compile(name="multi_agent_verify")

# ---- 导出 ------------------------------------------------------------------
out_png = OUT_DIR / "03_multi_agent_verify_loop.png"
try:
    png = graph.get_graph().draw_mermaid_png()
    out_png.write_bytes(png)
    print(f"已导出真实结构图: {out_png}")
except Exception as e:
    print(f"PNG 导出失败({e})，改用 ASCII：\n")
    print(graph.get_graph().draw_ascii())
