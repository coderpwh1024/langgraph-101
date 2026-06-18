import os
from dotenv import load_dotenv
from openai import api_key

load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY not found in environment variables")

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import json
import asyncio
import operator
from datetime import datetime
from typing import Literal, Annotated, List
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

# 模型配置
RESEARCH_MODEL = "openai:gpt-4.1-mini"  # Hard requirement for this notebook
MAX_OUTPUT_TOKENS = 10000

# 全局配置
MAX_RESEARCHER_ITERATIONS = 3  # How many times supervisor can delegate
MAX_REACT_TOOL_CALLS = 10  # Max tool calls per researcher
MAX_CONCURRENT_RESEARCH_UNITS = 5  # Max parallel researchers
MAX_STRUCTURED_OUTPUT_RETRIES = 3


# 获取日期的函数
def get_today_str() -> str:
    """获取格式化后用于展示的当前日期"""
    now = datetime.now()
    return f"{now:%a} {now:%b} {now.day} {now:%Y}"


# 联网搜索
def openai_websearch_called(response):
    """检测是否使用了 OpenAI 的网页搜索（联网搜索）功能"""
    try:
        tool_outputs = response.additional_kwargs.get("tool_outputs")
        if not tool_outputs:
            return False
        for tool_output in tool_outputs:
            if tool_output.get("type") == "web_search_call":
                return True
        return False
    except(AttributeError, TypeError):
        return False


# 获取模型
def get_model():
    return init_chat_model(
        model=RESEARCH_MODEL,
        max_tokens=MAX_OUTPUT_TOKENS,
        api_key=os.getenv("OPENAI_API_KEY"),
        use_response_api=True
    )


print("模型初始化完成")
print("\n")
print("\n")

print(
    "-------------------------------------------01-构建-一个单例搜索 Agent--------------------------------------------------------")

print("\n")


# Researcher 状态
class ResearcherState(TypedDict):
    """单个 researcher agent 的状态 """
    researcher_messages: Annotated[List[MessageLikeRepresentation], operator.add]
    researcher_topic: str
    tool_call_iterations: int


# Researcher 输出状态
class ResearcherOutputState(TypedDict):
    """研究员的输出——仅保留压缩后的研究发现"""
    researcher_messages: Annotated[List[MessageLikeRepresentation], operator.add]
    compressed_research: str
    raw_notes: list


@tool(description="表示研究已完成")
def ResearchComplete() -> str:
    """当你已收集到足够信息、能够回答研究问题时，调用此工具"""
    return " 研究已标记为完成"
