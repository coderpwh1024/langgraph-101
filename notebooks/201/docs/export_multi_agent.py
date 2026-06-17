"""桩节点重建 multi_agent.py 的图拓扑，导出真实结构 PNG。

说明：
- draw_mermaid_png() 只读图的「拓扑」（节点 + 边），不执行任何节点，
  因此这里用占位函数按 multi_agent.py 完全一致的拓扑重建各张图，
  绝不顶层 invoke()、不调用 LLM、不连数据库，零 API 费用。
- supervisor / invoice 子智能体用真实的 create_agent 构建（构建期不调用 API），
  这样 verify / final 两张图 xray=True 时能忠实展开 supervisor 内部结构。

由 export-graphs 引擎驱动（推荐）：
    python3 .../export-graphs/scripts/export_graphs.py export_multi_agent.py
也可直接运行：python3 export_multi_agent.py
"""
import sys
from pathlib import Path
from typing import TypedDict, Annotated, List

from langchain.agents import create_agent
from langchain_core.tools import tool
from langgraph.constants import END, START
from langgraph.graph import StateGraph, add_messages
from langgraph.graph.message import AnyMessage
from langgraph.prebuilt import ToolNode, ToolRuntime

# __file__ 位于 notebooks/201/docs/，上溯三级到 notebooks/，以便 import utils
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.models import model


# ---- State / InputState（与 multi_agent.py 一致，仅取构图所需字段）----------
class InputState(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]


class State(InputState):
    customer_id: int
    loaded_memory: str
    remaining_steps: int


# ---- 占位工具（仅用于建 ToolNode / create_agent，绝不执行）-----------------
@tool
def get_albums_by_artist(artist: str):
    """获取某位艺术家的专辑"""
    return ""


@tool
def get_tracks_by_artist(artist: str):
    """按艺术家（或相似艺术家）获取歌曲"""
    return ""


@tool
def get_song_by_genre(genre: str):
    """从数据库中获取匹配特定流派的歌曲"""
    return ""


@tool
def check_for_songs(song_title: str):
    """根据歌曲名称检查歌曲是否存在"""
    return ""


@tool
def get_invoices_by_customer_sorted_by_date(runtime: ToolRuntime) -> list:
    """查询某客户的所有发票（按日期排序）"""
    return []


@tool
def get_invoices_sorted_by_unit_price(runtime: ToolRuntime) -> list:
    """查询某客户的所有发票（按单价排序）"""
    return []


@tool
def get_employee_by_invoice_and_customer(runtime: ToolRuntime, invoice_id: int) -> dict:
    """根据发票与客户返回负责的员工信息"""
    return {}


# ---- 占位节点函数（仅提供拓扑，draw 时不会执行）---------------------------
def music_assistant(state: State):
    return {}


def verify_info(state: State):
    return {}


def human_input(state: State):
    return {}


def load_memory(state: State):
    return {}


def create_memory(state: State):
    return {}


def should_continue(state: State):
    return "end"


def should_interrupt(state: State):
    return "continue"


# ===========================================================================
# 图 1：music_catalog_subagent —— 手搓 ReAct 音乐子智能体（第 01 部分）
# ===========================================================================
def build_music_subagent():
    music_tool_node = ToolNode(
        [get_albums_by_artist, get_tracks_by_artist, get_song_by_genre, check_for_songs]
    )
    b = StateGraph(State)
    b.add_node("music_assistant", music_assistant)
    b.add_node("music_tool_node", music_tool_node)
    b.add_edge(START, "music_assistant")
    b.add_conditional_edges(
        "music_assistant",
        should_continue,
        {"continue": "music_tool_node", "end": END},
    )
    b.add_edge("music_tool_node", "music_assistant")
    return b.compile(name="music_catalog_subagent")


# ===========================================================================
# 图 2：supervisor —— 多智能体超级代理（第 02 部分），真实 create_agent
# ===========================================================================
@tool(name_or_callable="music_catalog_subagent",
      description="处理所有音乐相关查询的子智能体")
def call_music_catalog_subagent(query: str):
    """委派音乐目录查询给音乐子智能体"""
    return ""


@tool(name_or_callable="invoice_information_subagent",
      description="处理所有发票相关查询的子智能体")
def call_invoice_information_subagent(runtime: ToolRuntime, query: str):
    """委派发票查询给发票子智能体"""
    return ""


def build_supervisor():
    return create_agent(
        model=model,
        tools=[call_music_catalog_subagent, call_invoice_information_subagent],
        name="supervisor",
        system_prompt="(omitted)",
        state_schema=State,
    )


# ===========================================================================
# 图 3：multi_agent_verify —— 添加用户验证-LOOP（第 03 部分）
# ===========================================================================
def build_verify(supervisor):
    b = StateGraph(State, input_schema=InputState)
    b.add_node("verify_info", verify_info)
    b.add_node("human_input", human_input)
    b.add_node("supervisor", supervisor)
    b.add_edge(START, "verify_info")
    b.add_conditional_edges(
        "verify_info",
        should_interrupt,
        {"continue": "supervisor", "interrupt": "human_input"},
    )
    b.add_edge("human_input", "verify_info")
    b.add_edge("supervisor", END)
    return b.compile(name="multi_agent_verify")


# ===========================================================================
# 图 4：multi_agent_final —— 添加长期记忆闭环（第 04 部分）
# ===========================================================================
def build_final(supervisor):
    b = StateGraph(State, input_schema=InputState)
    b.add_node("verify_info", verify_info)
    b.add_node("human_input", human_input)
    b.add_node("load_memory", load_memory)
    b.add_node("supervisor", supervisor)
    b.add_node("create_memory", create_memory)
    b.add_edge(START, "verify_info")
    b.add_conditional_edges(
        "verify_info",
        should_interrupt,
        {"continue": "load_memory", "interrupt": "human_input"},
    )
    b.add_edge("human_input", "verify_info")
    b.add_edge("load_memory", "supervisor")
    b.add_edge("supervisor", "create_memory")
    b.add_edge("create_memory", END)
    return b.compile(name="multi_agent_final")


def build_exports():
    """返回 {文件名: graph 或 (graph, xray)}，供 export-graphs 引擎导出。"""
    supervisor = build_supervisor()
    return {
        "01_music_catalog_subagent": build_music_subagent(),
        "02_supervisor": (build_supervisor(), True),
        "03_multi_agent_verify_loop": (build_verify(supervisor), True),
        "04_multi_agent_final": (build_final(supervisor), True),
    }
