import operator
from typing import Annotated, NotRequired, TypedDict

from langchain_core.messages import MessageLikeRepresentation


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
