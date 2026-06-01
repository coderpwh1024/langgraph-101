import os
import sys
from pathlib import Path
from typing import TypedDict, Literal, Annotated

from langgraph.graph.message import AnyMessage, add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

# Add project root to path
project_root = Path().resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.models import model

# 初始化长期记忆
in_memory_store = InMemoryStore()

# 创建长期记忆保存器
checkpointer = MemorySaver()

print("-----------------------------01-创建 email Agent---------------------------------------")

class State(TypedDict):
    email_input:dict
    classification_decision:Literal["ignore","respond","notify"]
    messages:Annotated[list[AnyMessage],add_messages]
    loaded_memory:str
    remaining_steps:int

