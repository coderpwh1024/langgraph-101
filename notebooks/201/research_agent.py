import  os
from dotenv import load_dotenv

load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY not found in environment variables")

import  sys
from pathlib import  Path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import json
import asyncio
import operator
from datetime import datetime
from typing import Literal, Annotated
from typing_extensions import TypedDict

from langchain.chat_models import init_chat_model
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    filter_messages,
    get_buffer_string,
    MessageLikeRepresentation
)
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from utils.utils import show_graph
from utils.models import model