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


@tool(description="用于研究规划的战略性反思工具")
def think_tool(reflection: str) -> str:
    """每次搜索后调用此工具，用于分析搜索结果并规划后续步骤。
     Args:
         reflection: 对当前研究进展与后续步骤的详细反思。
     """
    return f"已记录反思内容：{reflection}"


# 获取所有的工具
def get_all_tool():
    """获取所有可用的研究工具"""
    tools = [think_tool, ResearchComplete]
    tools.append({"type": "web_search_preview"})
    return tools


# Researcher 系统提示词
research_system_prompt = """你是一名研究助理，负责针对用户输入的主题开展研究。作为背景信息，今天的日期是 {date}。
<Task>
你的任务是使用工具来收集与用户输入主题相关的信息。
你可以使用提供给你的任意工具，去查找有助于回答该研究问题的资料。
</Task>

<Available Tools>
你可以使用以下工具：
1. **Web search（网页搜索）**：用于进行网页搜索、收集信息。
2. **think_tool**：用于在研究过程中进行反思与战略性规划。

**关键要求：每次搜索之后都要使用 think_tool 来反思搜索结果并规划后续步骤。**
</Available Tools>

<Instructions>
像一位时间有限的人类研究员那样思考：

1. **仔细阅读问题**——用户具体需要哪些信息？
2. **从更宽泛的搜索开始**——先使用宽泛、全面的查询。
3. **每次搜索后暂停并评估**——我掌握的信息是否足以作答？还缺少什么？
4. **随着信息积累，逐步收窄搜索**——填补尚存的空白。
5. **能够自信作答时即停止**——不要为追求完美而无止境地搜索。
</Instructions>

<Hard Limits>
**工具调用预算（Tool Call Budgets）**：
- **简单查询**：最多使用 2-3 次搜索类工具调用。
- **复杂查询**：最多使用 4 次搜索类工具调用。
- **务必停止**：若在 4 次搜索类工具调用后仍未找到合适资料，也要停止。

**遇到以下情况立即停止**：
- 你已能全面地回答用户的问题。
- 你已就该问题获得 3 个及以上相关示例/来源。
- 你最近 2 次搜索返回的信息高度相似。
</Hard Limits>
"""


# 执行搜索
async def researcher(state: ResearcherState, config):
    """主研究节点，负责执行研究任务"""
    researcher_messages = state.get("researcher_messages", [])

    # 获取工具
    tools = get_all_tool()
    # 获取搜索提示词
    research_prompt = research_system_prompt.format(date=get_today_str())
    # 模型绑定工具
    research_model = (
        get_model().bind_tools(tools).with_retry(stop_after_attempt=MAX_STRUCTURED_OUTPUT_RETRIES)
    )
    # 上下文(提示词与上下文)
    messages = [SystemMessage(content=research_prompt)] + researcher_messages
    response = await research_model.ainvoke(messages)

    return {
        "researcher_messages": [response],
        "tool_call_iterations": state.get("tool_call_iterations", 0) + 1
    }


# 工具异步执行
async def execute_tool_safely(tool, args):
    """安全地执行工具，并进行错误处理"""
    try:
        return await tool.invoke(args)
    except Exception as e:
        print(f"工具调用错误：{e}")
        return f"工具调用异常: {str(e)}"


async def researcher_tools(state: ResearcherState, config) -> Command[Literal["researcher", "compress_research"]]:
    """执行 researcher（研究员）调用的工"""

    researcher_message = state["researcher_messages"][-1]
    most_recent_message = researcher_message[-1]

    has_tool_calls = bool(most_recent_message.tool_calls)
    has_native_search = openai_websearch_called(most_recent_message)

    if not has_tool_calls and not has_native_search:
        return Command(goto="compress_search")

    tools =get_all_tool()

    tools_by_name = {
        tool.name if hasattr(tool,"name") else tool.get("name","web_search"):tool for tool in tools
     }
