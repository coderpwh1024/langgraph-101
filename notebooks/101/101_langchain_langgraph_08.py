from typing_extensions import TypedDict
from typing import Annotated, List
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.managed.is_last_step import RemainingSteps


# 定义状态
class State(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]



tools = []
tool_name