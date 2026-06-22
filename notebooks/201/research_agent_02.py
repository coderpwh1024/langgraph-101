import operator
from typing import Annotated, NotRequired, TypedDict

from langchain_core.messages import HumanMessage, MessageLikeRepresentation
from langchain_core.tools import tool

# 复用 research_agent 中已编译好的 researcher 子图
from research_agent import researcher_graph


# 覆盖 reducer
def override_reducer(current_value, new_value):
    """允许覆盖（override）state 中已有值的 reducer 函数"""
    if isinstance(new_value, dict) and new_value.get("type") == "override":
        return new_value.get("value", new_value)
    else:
        return operator.add(current_value, new_value)


# 构建 supervisor 子图
class SupervisorState(TypedDict):
    """supervisor（监督者）智能体的 state"""
    supervisor_messages: Annotated[list[MessageLikeRepresentation], operator.add]
    research_brief: str
    notes: NotRequired[Annotated[list[str], override_reducer]]
    research_iterations: NotRequired[int]
    raw_notes: NotRequired[Annotated[list[str], override_reducer]]


@tool(description="将一项研究任务委派给专门的 researcher（研究员）")
async def ConductResearch(research_topic: str) -> dict:
    """将某个具体的研究主题委派给 researcher（研究员）智能体。

    Args:
        research_topic: 交给子智能体（sub-agent）的研究问题，需清晰、具体。

    Returns:
        researcher 子图执行后的完整 state，包含 compressed_research 等字段。
    """
    # researcher_graph 期望的初始 state 字段见 research_agent.ResearcherState
    result = await researcher_graph.ainvoke(
        {
            "researcher_messages": [HumanMessage(content=research_topic)],
            "researcher_topic": research_topic,
            "tool_call_iterations": 0,
        }
    )
    return {
        "compressed_research": result.get("compressed_research", "Error in research"),
        "raw_notes": result.get("raw_notes", [])
    }
