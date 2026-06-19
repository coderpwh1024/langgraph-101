"""导出 research_agent.py 中 researcher 子图的状态机流程图 PNG。

说明：
- draw_mermaid_png() 只需要图的「拓扑结构」（节点 + 边），不会执行任何节点，
  因此本脚本按 research_agent.py 完全一致的拓扑重建 researcher 子图，
  节点函数用占位实现（绝不调用 LLM / 联网），不产生任何 API 费用。
- researcher_tools 用 Command[Literal[...]] 的返回注解承载条件跳转，
  draw 时据此画出「回到 researcher 继续 ReAct」与「进入 compress_research」两条边。

可被本仓库 export-graphs 引擎驱动（优先识别 build_exports()），
也可直接运行：python export_research_agent.py
"""
import operator
import sys
from pathlib import Path
from typing import Annotated, List, Literal

from typing_extensions import TypedDict

from langchain_core.messages import MessageLikeRepresentation
from langgraph.constants import END, START
from langgraph.graph import StateGraph
from langgraph.types import Command

# __file__ 位于 notebooks/201/docs/，上溯两级到 notebooks/201/，再让 utils 可导入
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

OUT_DIR = Path(__file__).resolve().parent / "image"
OUT_DIR.mkdir(exist_ok=True)


# ---- State（与原文件一致）-------------------------------------------------
class ResearcherState(TypedDict):
    """单个 researcher agent 的状态。"""
    researcher_messages: Annotated[List[MessageLikeRepresentation], operator.add]
    researcher_topic: str
    tool_call_iterations: int


class ResearcherOutputState(TypedDict):
    """研究员的输出——仅保留压缩后的研究发现。"""
    researcher_messages: Annotated[List[MessageLikeRepresentation], operator.add]
    compressed_research: str
    raw_notes: list


# ---- 占位节点函数（仅提供拓扑，draw 时不会执行）---------------------------
def researcher(state: ResearcherState) -> dict:
    return {}


def researcher_tools(
    state: ResearcherState,
) -> Command[Literal["researcher", "compress_research"]]:
    # 返回注解承载条件跳转：回到 researcher 继续 ReAct，或进入 compress_research
    return Command(goto="compress_research")


def compress_research(state: ResearcherState) -> dict:
    return {}


# ===========================================================================
# researcher 子图 —— ReAct 研究循环 + 结果压缩
# ===========================================================================
def build_researcher():
    """按 research_agent.py 一致的拓扑重建 researcher 子图。"""
    b = StateGraph(ResearcherState, output_schema=ResearcherOutputState)
    b.add_node("researcher", researcher)
    b.add_node("researcher_tools", researcher_tools)
    b.add_node("compress_research", compress_research)
    b.add_edge(START, "researcher")
    b.add_edge("researcher", "researcher_tools")
    b.add_edge("compress_research", END)
    return b.compile()


def build_exports():
    """供 export-graphs 引擎发现：文件名 -> 编译图。"""
    return {
        "05_researcher.png": build_researcher(),
    }


if __name__ == "__main__":
    from export_graphs import export

    export(build_researcher(), "05_researcher.png")
    print("完成。")
