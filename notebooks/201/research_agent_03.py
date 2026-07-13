import asyncio
import operator
import sys
from datetime import datetime
from pathlib import Path
from typing import Annotated
from typing import Any
from typing import Literal
from typing import TypedDict

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, filter_messages
from langchain_core.messages import HumanMessage
from langchain_core.messages import MessageLikeRepresentation
from langchain_core.messages import SystemMessage
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.types import Command

# 将 notebooks 目录加入 sys.path，以便以脚本方式运行时能 import utils
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.models import model

# 研究过程限制
MAX_RESEARCHER_ITERATIONS = 3  # supervisor 最多委派研究的轮次
MAX_REACT_TOOL_CALLS = 10  # 每个 researcher 最多调用工具的次数
MAX_CONCURRENT_RESEARCH_UNITS = 5  # 最多并行运行的 researcher 数量
MAX_STRUCTURED_OUTPUT_RETRIES = 3


def get_today_str() -> str:
    """获取格式化后用于展示的当前日期。

    Returns:
        包含星期、月份、日期和年份的英文日期字符串。
    """
    now = datetime.now()
    return f"{now:%a} {now:%b} {now.day} {now:%Y}"


def get_model() -> BaseChatModel:
    """获取项目统一配置的千问聊天模型。

    模型名称、DashScope API Key 与兼容模式地址统一在
    ``utils.models`` 中配置，业务脚本不重复读取密钥。

    Returns:
        项目共享的千问聊天模型实例。
    """
    return model


@tool(
    description="联网搜索工具：使用千问内置联网搜索能力检索最新网络信息"
)
async def web_search(query: str) -> str:
    """使用千问（阿里云百炼）内置联网搜索能力检索信息。

    Args:
        query: 需要联网检索的问题，应尽量具体、聚焦。

    Returns:
        千问根据联网搜索结果生成的回答，包含来源标题和链接。
    """
    # 在共享模型上临时开启搜索，避免业务脚本重复配置 API Key 和地址。
    search_model = get_model().bind(
        extra_body={
            "enable_search": True,
            "search_options": {"forced_search": True},
        }
    )
    search_prompt = (
        "请联网搜索以下问题并给出简明、准确的回答，"
        "在回答结尾列出信息来源的标题和链接：\n"
        f"{query}"
    )
    response = await search_model.ainvoke([HumanMessage(content=search_prompt)])
    return str(response.content)


def qwen_websearch_called(response: AIMessage) -> bool:
    """判断千问是否发起了 ``web_search`` 工具调用。

    百炼 OpenAI 兼容接口不会返回 OpenAI Responses API 中的
    ``tool_outputs/web_search_call`` 字段，因此应检查 LangChain 解析后的
    ``tool_calls``。真正的联网检索由 ``web_search`` 工具执行。

    Args:
        response: 千问返回的 AI 消息。

    Returns:
        如果消息中包含 ``web_search`` 工具调用则返回 True，否则返回 False。
    """
    return any(
        tool_call.get("name") == web_search.name
        for tool_call in response.tool_calls
    )


print("\n")
print("✓ 已加载项目统一配置的千问模型（阿里云百炼）")
print("\n")

print(
    "--------------------01-构建一个单例搜索 Agent--------------------"
)
print("\n")


# 研究的状态实体类
class ResearcherState(TypedDict):
    """单个研究员智能体的状态。"""

    researcher_messages: Annotated[list[MessageLikeRepresentation], operator.add]
    researcher_topic: str
    tool_call_iterations: int


# 输出实体类
class ResearcherOutputState(TypedDict):
    """研究员图的最终输出。"""

    researcher_messages: Annotated[list[MessageLikeRepresentation], operator.add]
    compressed_research: str
    raw_notes_content: list[str]


print("\n")


@tool(description="表示研究已完成")
def researcher_complete() -> str:
    """在收集到足够信息后标记研究完成。

    Returns:
        研究已完成的确认信息。
    """
    return "研究已标记为完成"


@tool(description="用于研究规划的战略性反思工具")
def think_tool(reflection: str) -> str:
    """每次搜索后使用此工具分析结果并规划后续步骤。

    Args:
        reflection: 对研究进展和后续步骤的详细反思。

    Returns:
        已记录的研究反思。
    """
    return f"反思已记录：{reflection}"


def get_all_tools() -> list[object]:
    """获取所有可用的研究工具。

    Returns:
        研究阶段可调用的工具列表。
    """
    return [web_search, researcher_complete, think_tool]


research_system_prompt = """你是一名研究助理，负责围绕用户输入的主题开展研究。作为背景信息，今天的日期是 {date}。

  <Task>
  你的任务是使用工具收集与用户输入主题相关的信息。
  你可以使用提供给你的任意工具，查找有助于回答研究问题的资料。
  </Task>

  <Available Tools>
  你可以使用以下工具：
  1. **Web search**：执行网络搜索以收集信息
  2. **think_tool**：在研究过程中进行反思和策略规划

  **关键要求：每次搜索后都必须使用 think_tool 反思搜索结果，并规划下一步行动。**
  </Available Tools>

  <Instructions>
  像一名时间有限的人类研究员一样思考：

  1. **仔细阅读问题**——用户具体需要哪些信息？
  2. **从宽泛搜索开始**——首先使用覆盖面广、综合性强的搜索查询
  3. **每次搜索后暂停并评估**——现有信息是否足以回答问题？还缺少什么？
  4. **随着信息逐渐完善，执行更精准的搜索**——补齐信息缺口
  5. **能够自信回答时立即停止**——不要为了追求完美而继续搜索
  </Instructions>

  <Hard Limits>
  **工具调用预算**：
  - **简单问题**：最多调用搜索工具 2～3 次
  - **复杂问题**：最多调用搜索工具 4 次
  - **必须停止**：调用搜索工具 4 次后，即使仍未找到合适的资料，也必须停止搜索

  **出现以下情况时立即停止**：
  - 已经能够全面回答用户的问题
  - 已经找到 3 个以上与问题相关的示例或信息来源
  - 最近两次搜索返回了相似的信息
  </Hard Limits>
  """


#  研究节点
async def researcher(state: ResearcherState) -> dict:
    """执行研究工作的主研究员节点。

    Args:
        state: 当前研究员状态。

    Returns:
        包含模型响应及工具调用轮次的状态更新。
    """
    researcher_messages = state.get("researcher_messages", [])

    # 获取所有的工具
    tools = get_all_tools()

    # 提示词
    researcher_prompt = research_system_prompt.format(date=get_today_str())

    research_model = (
        get_model().bind_tools(tools).with_retry(stop_after_attempt=MAX_STRUCTURED_OUTPUT_RETRIES)
    )

    messages = [SystemMessage(content=researcher_prompt)] + researcher_messages

    response = await research_model.ainvoke(messages)

    return {
        "researcher_messages": [response],
        "tool_call_iterations": state.get("tool_call_iterations", 0) + 1,
    }


# 执行工具时统一捕获异常，避免单个工具失败中断其他并发任务。
async def execute_tool_safely(
        selected_tool: Any,
        arguments: dict[str, Any],
) -> str:
    """安全地执行工具，并将异常转换为可供模型理解的结果。

    Args:
        selected_tool: 待执行的 LangChain 工具。
        arguments: 工具调用参数。

    Returns:
        工具执行结果；执行失败时返回包含错误原因的文本。
    """
    try:
        result = await selected_tool.ainvoke(arguments)
    except Exception as error:  # pylint: disable=broad-exception-caught
        print(f"工具执行失败：{error}")
        return f"执行工具时出错：{error}"
    return str(result)


# 研究工具节点负责并发执行模型发起的工具调用，并决定下一跳。
async def researcher_tools(
        state: ResearcherState,
) -> Command[Literal["researcher", "compress_research"]]:
    """执行研究员调用的工具并选择后续节点。

    Args:
        state: 当前研究员状态。

    Returns:
        指向研究节点或压缩节点的跳转命令。
    """
    researcher_messages = state.get("researcher_messages", [])
    most_recent_message = researcher_messages[-1]

    # 结构化返回，看是否 tool 工具的调用
    has_tool_calls = bool(most_recent_message.tool_calls)
    has_native_search = qwen_websearch_called(most_recent_message)

    if not has_tool_calls and not has_native_search:
        return Command(goto="compress_research")

    tools_by_name = {
        available_tool.name: available_tool
        for available_tool in get_all_tools()
    }

    tool_calls = most_recent_message.tool_calls
    tool_execution_tasks = []

    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_arguments = tool_call["args"]
        execution_task = execute_tool_safely(
            tools_by_name[tool_name],
            tool_arguments,
        )
        tool_execution_tasks.append(execution_task)

    # 异步执行工具
    observations = await asyncio.gather(*tool_execution_tasks)

    tool_outputs = []
    for observation, tool_call in zip(observations, tool_calls, strict=True):
        tool_message = ToolMessage(
            content=observation,
            name=tool_call["name"],
            tool_call_id=tool_call["id"],
        )
        tool_outputs.append(tool_message)

    exceeded_iterations = (
            state.get("tool_call_iterations", 0) >= MAX_REACT_TOOL_CALLS
    )

    research_complete = False
    for tool_call in most_recent_message.tool_calls:
        if tool_call["name"] == researcher_complete.name:
            research_complete = True
            break

    if exceeded_iterations or research_complete:
        return Command(
            goto="compress_research",
            update={"researcher_messages": tool_outputs},
        )

    return Command(goto="researcher", update={"researcher_messages": tool_outputs})


# 压缩 research 节点
compress_research_system_prompt = """你是一名已经围绕某个主题开展研究的研究助理。你的任务是整理研究发现。

  <Task>
  整理通过工具调用和网页搜索收集到的信息。所有相关信息都应逐字保留。
  此工作的目的仅是删除明显无关或重复的信息。
  </Task>

  <Guidelines>
  1. 输出必须全面，并包含收集到的所有信息和来源
  2. 为每个来源添加行内引用，如 [1]、[2] 等
  3. 在结尾添加“来源”部分，列出所有带引用编号的来源
  4. 确保包含所有来源——后续的 LLM 会将此报告与其他报告合并
  </Guidelines>
  """


# 压缩 research 节点
async def compress_research(state: ResearcherState) -> dict:
    """压缩并综合研究发现。

    Args:
        state: 当前研究员状态。

    Returns:
        包含压缩研究结果和原始笔记内容的状态更新。
    """
    researcher_messages = state.get("researcher_messages", [])
    researcher_messages.append(HumanMessage(content="请整理这些研究发现。不要总结——请逐字保留所有相关信息"))

    # 提示词
    compression_prompt = compress_research_system_prompt
    messages = [SystemMessage(content=compression_prompt)] + researcher_messages

    response = await  get_model().ainvoke(messages)

    raw_notes_content = []
    for message in filter_messages(researcher_messages, include_types=["tool", "ai"]):
        raw_notes_content.append(str(message.content))
    raw_notes_content = "\n".join(raw_notes_content)

    return {
        "compressed_research": str(response.content),
        "raw_notes_content": [raw_notes_content],
    }


# 构建 StateGraph
researcher_builder = StateGraph(ResearcherState, output_schema=ResearcherOutputState)

# 添加节点
researcher_builder.add_node("researcher", researcher)
researcher_builder.add_node("researcher_tools", researcher_tools)
researcher_builder.add_node("compress_research", compress_research)

researcher_builder.add_edge(START, "researcher")
researcher_builder.add_edge("researcher", "researcher_tools")
researcher_builder.add_edge("compress_research", END)

researcher_graph = researcher_builder.compile()
# researcher_graph
#
# test_query = "2026年世界杯，预测一下阿根廷VS英格兰，谁赢谁输?概率有多大？"
# initial_state = {
#     "researcher_messages": [HumanMessage(content=test_query)],
#     "researcher_topic": test_query,
#     "tool_call_iterations": 0
# }

# result = asyncio.run(researcher_graph.ainvoke(initial_state))
# print("\n")
# print("="*60)
# print("研究员消息历史：")
# print("="*60)
# print("\n")
#
# for message in result["researcher_messages"]:
#     message.pretty_print()
#
# print("\n" + "="*60)
# print("="*60)
# print(result["compressed_research"])

print("\n")
print(
    "--------------------02-构建一个Supervisor Agent--------------------"
)
print("\n")


# value覆盖
def override_reducer(current_value, new_value):
    """允许覆盖状态中值的 Reducer 函数"""
    if isinstance(new_value, dict) and new_value.get("type") == "override":
        return new_value.get("value", new_value)
    else:
        return operator.add(current_value, new_value)


# 监督这状态实体
class SupervisorState(TypedDict):
    """监督者智能体的状态"""
    supervisor_messages: Annotated[list[MessageLikeRepresentation], override_reducer]
    researcher_brief: str
    notes: Annotated[list[str], override_reducer] = []
    research_iterations: int = 0
    raw_notes: Annotated[list[str], override_reducer] = []


@tool(description="将研究任务委派给专业研究员")
async def ConductResearch(research_topic: str) -> dict:
    """将特定研究主题委派给研究员智能体。

     Args:
         research_topic: 供子智能体研究的清晰、具体的问题。
     """
    result = await  researcher_graph.invoke(
        {
            "researcher_messages": [HumanMessage(content=research_topic)],
            "researcher_topic": research_topic,
            "tool_call_iterations": 0
        }
    )

    return {
        "compressed_research": result.get("compressed_research", "Error in research"),
        "raw_notes": result.get("raw_notes", [])
    }


@tool(description="标记所有研究工作已完成")
def ResearchComplete():
    """已收集完所有必要信息时调用此工具"""
    return "研究已标记为完成"


lead_researcher_prompt = """你是一名研究主管。你的工作是通过调用 “ConductResearch” 工具来开展研究。

  <Task>
  调用 “ConductResearch” 工具以委派研究任务。当你对研究发现感到满意时，调用 “ResearchComplete”。
  </Task>

  <Available Tools>
  1. **ConductResearch**：将研究任务委派给专业子智能体。
  2. **ResearchComplete**：表示研究已完成。
  3. **think_tool**：用于反思和战略规划。

  **重要：调用 ConductResearch 前必须使用 think_tool 制定计划，调用后必须使用它评估进展。**
  </Available Tools>

  <Instructions>
  像研究经理一样思考：

  1. **仔细阅读问题**：需要哪些具体信息？
  2. **决定如何委派**：是否可以同时从多个相互独立的角度展开研究？
  3. **每次调用 ConductResearch 后进行评估**：信息是否已经足够？还缺少什么？
  </Instructions>

  <Hard Limits>
  - **限制工具调用次数**：如果无法找到合适的来源，在调用 {max_researcher_iterations} 次工具后停止。
  - **每轮最多并行运行 {max_concurrent_research_units} 个智能体。**
  </Hard Limits>

  <Scaling Rules>
  **简单查询**：使用一个子智能体。
  **对比类问题**：为每个待比较对象分别使用一个子智能体。
  **重要**：调用 ConductResearch 时，必须提供完整且可独立理解的任务说明。
  </Scaling Rules>
  """


# 监督者函数
async def supervisor(state: SupervisorState, config):
    """负责委派研究任务的监督者智能体"""

    lead_researcher_tools = [ConductResearch, ResearchComplete, think_tool]

    # 构建模型
    researcher_model = (
        get_model().bind_tools(lead_researcher_tools).with_retry(stop_after_attempt=MAX_STRUCTURED_OUTPUT_RETRIES))

    supervisor_messages = state.get("supervisor_messages", [])
    response = await  researcher_model.ainvoke(supervisor_messages)

    return {
        "supervisor_messages": [response],
        "research_iterations": state.get("research_iterations", 0) + 1
    }


#  提取工具内容
def extract_tool_content(messages):
    """从工具调用消息中提取笔记"""
    tool_msg_content = []
    for tool_msg in filter_messages(messages, include_types="tool"):
        content = tool_msg.content
        tool_msg_content.append(content)
    return tool_msg_content
