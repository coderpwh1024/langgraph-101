from typing import Annotated, NotRequired

from langchain_community.utilities import SQLDatabase
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from langgraph.managed import RemainingSteps
from typedict import TypeDict

from notebooks.utils.utils import get_engine_for_chinook_db

engine = get_engine_for_chinook_db()
db = SQLDatabase()


class InputState(TypeDict):
    messages: Annotated[list[AnyMessage], add_messages]


class State(InputState):
    customer_id: NotRequired[str]
    loaded_memory: NotRequired[str]
    remaining_steps: NotRequired[RemainingSteps]
