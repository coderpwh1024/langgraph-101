"""
导出 email_agent.py 中 4 张图的真实流程图 PNG。

说明：
- draw_mermaid_png() 只需要图的「拓扑结构」（节点 + 边），不会执行任何节点，
  因此本脚本按 email_agent.py 完全一致的拓扑重建 4 张图，
  节点函数用占位实现（绝不调用 LLM），不产生任何 API 费用。
- email_prebuilt 用真实的 create_agent 构建（构建期不调用 API），结构最忠实。

运行：python export_graphs.py
"""
import sys
from pathlib import Path
from typing import TypedDict, Literal, Annotated

from pydantic import BaseModel
from langgraph.constants import END, START
from langgraph.graph import StateGraph
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from langchain.agents import create_agent

# 让 utils 可导入（构造 model 不触发 API 调用）
# __file__ 位于 notebooks/201/docs/，上溯三级到 notebooks/
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
from utils.models import model

OUT_DIR = Path(__file__).resolve().parent / "image"
OUT_DIR.mkdir(exist_ok=True)


# ---- State（与原文件一致）-------------------------------------------------
class State(TypedDict):
    email_input: dict
    classification_decision: Literal["ignore", "respond", "notify"]
    messages: Annotated[list[AnyMessage], add_messages]
    loaded_memory: str


# ---- 工具（与原文件一致，仅用于构建 ToolNode，不会被执行）-----------------
@tool
def schedule_meeting(attendees: list, subject: str, duration_minutes: int,
                     preferred_day: str, start_time: int) -> str:
    """安排一个日历会议"""
    return ""


@tool
def check_calendar_availability(day: str) -> str:
    """查询某一天的日历可用时间"""
    return ""


@tool
def write_email(to: str, subject: str, content: str) -> str:
    """写邮件并发送"""
    return ""


@tool
class Done(BaseModel):
    """邮件已经发送"""
    done: bool


tools = [schedule_meeting, check_calendar_availability, write_email, Done]
tool_node = ToolNode(tools)


# ---- 占位节点函数（仅提供拓扑，draw 时不会执行）---------------------------
def _noop(state: State):
    return {}


def reasoning_node(state):      return {}
def triage_router(state):       return {}
def human_input(state):         return {}
def load_memory(state):         return {}
def create_memory(state):       return {}


def should_continue(state) -> Literal["tools", "__end__"]:
    return END


def handle_classification(state):
    return END


def handle_human_input(state):
    return END


def should_create_memory(state):
    return END


# ===========================================================================
# 图 1：agent —— 手搓 ReAct（第 01 部分）
# ===========================================================================
def build_agent():
    b = StateGraph(State)
    b.add_node("agent", reasoning_node)
    b.add_node("tools", tool_node)
    b.add_edge(START, "agent")
    b.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    b.add_edge("tools", "agent")
    return b.compile()


# ===========================================================================
# 图 2：email_prebuilt —— 预编制（第 02 部分），真实 create_agent
# ===========================================================================
def build_prebuilt():
    return create_agent(
        model=model,
        tools=tools,
        name="email_prebuilt",
        system_prompt="(omitted)",
        state_schema=State,
    )


# ===========================================================================
# 图 3：email_hitl —— 人机协同（第 03 部分）
# ===========================================================================
def build_hitl(agent_subgraph):
    b = StateGraph(State)
    b.add_node("triage", triage_router)
    b.add_node("human_input", human_input)
    b.add_node("email_agent", agent_subgraph)
    b.add_edge(START, "triage")
    b.add_conditional_edges("triage", handle_classification,
                            {"human_input": "human_input", "email_agent": "email_agent", END: END})
    b.add_conditional_edges("human_input", handle_human_input,
                            {"email_agent": "email_agent", END: END})
    return b.compile()


# ===========================================================================
# 图 4：email_agent_memory —— 长期记忆闭环（第 04 部分）
# ===========================================================================
def build_memory(agent_subgraph):
    b = StateGraph(State)
    b.add_node("triage", triage_router)
    b.add_node("human_input", human_input)
    b.add_node("email_agent", agent_subgraph)
    b.add_node("load_memory", load_memory)
    b.add_node("create_memory", create_memory)
    b.add_edge(START, "load_memory")
    b.add_edge("load_memory", "triage")
    b.add_conditional_edges("triage", handle_classification,
                            {"human_input": "human_input", "email_agent": "email_agent", END: END})
    b.add_conditional_edges("human_input", handle_human_input,
                            {"email_agent": "email_agent", END: END})
    b.add_conditional_edges("email_agent", should_create_memory,
                            {"create_memory": "create_memory", END: END})
    return b.compile()


def export(graph, filename, xray=False):
    path = OUT_DIR / filename
    try:
        png = graph.get_graph(xray=xray).draw_mermaid_png()
        path.write_bytes(png)
        print(f"[OK]  {filename}  ({len(png)} bytes)")
    except Exception as e:
        # 离线时 mermaid.ink 不可用，回退导出 .mmd 源码
        mmd = graph.get_graph(xray=xray).draw_mermaid()
        mmd_path = path.with_suffix(".mmd")
        mmd_path.write_text(mmd, encoding="utf-8")
        print(f"[FALLBACK] PNG 失败 ({type(e).__name__})，已导出源码: {mmd_path.name}")


if __name__ == "__main__":
    agent = build_agent()
    export(agent, "01_agent_react.png")
    export(build_prebuilt(), "02_email_prebuilt.png")
    export(build_hitl(agent), "03_email_hitl.png", xray=True)
    export(build_memory(agent), "04_email_agent_memory.png", xray=True)
    print("完成。")
