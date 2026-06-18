import asyncio
import operator
import sys
from datetime import datetime
from pathlib import Path
from typing import Annotated, List, Literal

from typing_extensions import TypedDict

from langchain_core.messages import (
    HumanMessage,
    MessageLikeRepresentation,
    SystemMessage,
    ToolMessage,
    filter_messages,
)
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

# 将 notebooks 目录加入 sys.path，以便以脚本方式运行时能 import utils
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.models import model

# 全局配置
MAX_REACT_TOOL_CALLS = 10  # 单个 researcher 最多的工具调用轮次
MAX_STRUCTURED_OUTPUT_RETRIES = 3  # 模型调用失败时的重试次数


# 获取日期的函数
def get_today_str() -> str:
    """获取格式化后用于展示的当前日期。"""
    now = datetime.now()
    return f"{now:%a} {now:%b} {now.day} {now:%Y}"


# 获取模型
def get_model():
    """获取统一的聊天模型（走千问 / DashScope，定义见 utils.models）。

    Returns:
        共享的 ChatOpenAI 实例；调用方可在其上 bind_tools / with_retry，
        这些操作返回新的 Runnable，不会修改全局 model。
    """
    return model


print("模型初始化完成")
print("\n")
print("\n")

print(
    "-------------------------------------------01-构建-一个单例搜索 Agent--------------------------------------------------------")

print("\n")


# Researcher 状态
class ResearcherState(TypedDict):
    """单个 researcher agent 的状态。"""
    researcher_messages: Annotated[List[MessageLikeRepresentation], operator.add]
    researcher_topic: str
    tool_call_iterations: int


# Researcher 输出状态
class ResearcherOutputState(TypedDict):
    """研究员的输出——仅保留压缩后的研究发现。"""
    researcher_messages: Annotated[List[MessageLikeRepresentation], operator.add]
    compressed_research: str
    raw_notes: list


@tool(description="表示研究已完成")
def ResearchComplete() -> str:
    """当你已收集到足够信息、能够回答研究问题时，调用此工具。"""
    return "研究已标记为完成"


@tool(description="联网搜索工具：基于千问内置联网搜索能力，检索与查询相关的最新网络信息")
async def web_search(query: str) -> str:
    """使用千问（DashScope）内置联网搜索能力检索网络信息。

    Args:
        query: 要检索的查询内容，应尽量具体、聚焦。

    Returns:
        基于联网搜索结果整理出的文字摘要（含来源说明）；检索异常时返回错误提示。
    """
    # 在共享 model 上临时开启 enable_search，避免在业务文件硬编码 key / base_url；
    # forced_search 强制本轮必须联网检索，而非让模型自行判断是否搜索。
    search_model = model.bind(
        extra_body={"enable_search": True, "search_options": {"forced_search": True}}
    )
    search_prompt = (
        "请联网搜索以下问题，并给出简明、准确的回答，"
        f"同时在结尾以列表形式标注信息来源（含标题与链接）：\n{query}"
    )
    response = await search_model.ainvoke([HumanMessage(content=search_prompt)])
    return str(response.content)


@tool(description="用于研究规划的战略性反思工具")
def think_tool(reflection: str) -> str:
    """每次思考后调用此工具，用于分析当前已知信息并规划后续步骤。

    Args:
        reflection: 对当前研究进展与后续步骤的详细反思。

    Returns:
        回显本次反思内容的字符串。
    """
    return f"已记录反思内容：{reflection}"


# 获取所有的工具
def get_all_tool() -> list:
    """获取所有可用的研究工具。

    Returns:
        工具列表：web_search（千问内置联网搜索）、think_tool（反思规划）、
        ResearchComplete（结束标记）。
    """
    return [web_search, think_tool, ResearchComplete]


# Researcher 系统提示词
research_system_prompt = """你是一名研究助理，负责针对用户输入的主题开展研究。作为背景信息，今天的日期是 {date}。
<Task>
你的任务是使用工具来收集与用户输入主题相关的信息。
你可以使用提供给你的任意工具，去查找有助于回答该研究问题的资料。
</Task>

<Available Tools>
你可以使用以下工具：
1. **web_search**：基于千问内置联网搜索能力，用于进行网页搜索、收集最新信息。
2. **think_tool**：用于在研究过程中进行反思与战略性规划。
3. **ResearchComplete**：当你已能自信作答时，调用它结束研究。

**关键要求：每次 web_search 之后都要使用 think_tool 来反思搜索结果并规划后续步骤。**
</Available Tools>

<Instructions>
像一位时间有限的人类研究员那样思考：

1. **仔细阅读问题**——用户具体需要哪些信息？
2. **从更宽泛的搜索开始**——先使用宽泛、全面的查询。
3. **每次搜索后暂停并评估**——我掌握的信息是否足以作答？还缺少什么？
4. **随着信息积累，逐步收窄搜索**——填补尚存的空白。
5. **能够自信作答时即停止**——调用 ResearchComplete，不要为追求完美而无止境地搜索。
</Instructions>

<Hard Limits>
**工具调用预算（Tool Call Budgets）**：
- **简单查询**：最多使用 2-3 次 web_search 工具调用。
- **复杂查询**：最多使用 4 次 web_search 工具调用。
- **务必停止**：若在 4 次搜索后仍未找到合适资料，也要停止。

**遇到以下情况立即停止**：
- 你已能全面地回答用户的问题。
- 你已就该问题获得 3 个及以上相关来源。
- 你最近 2 次搜索返回的信息高度相似。
</Hard Limits>
"""


# 执行研究
async def researcher(state: ResearcherState, config) -> dict:
    """主研究节点，负责调用模型并产出下一步（含工具调用）。"""
    researcher_messages = state.get("researcher_messages", [])

    # 获取工具
    tools = get_all_tool()
    # 获取研究提示词
    research_prompt = research_system_prompt.format(date=get_today_str())
    # 模型绑定工具
    research_model = (
        get_model().bind_tools(tools).with_retry(stop_after_attempt=MAX_STRUCTURED_OUTPUT_RETRIES)
    )
    # 上下文（提示词 + 历史消息）
    messages = [SystemMessage(content=research_prompt)] + researcher_messages
    response = await research_model.ainvoke(messages)

    return {
        "researcher_messages": [response],
        "tool_call_iterations": state.get("tool_call_iterations", 0) + 1
    }


# 工具异步执行
async def execute_tool_safely(tool, args):
    """安全地执行工具，并进行错误处理。

    Args:
        tool: 待执行的工具对象。
        args: 传给工具的参数字典。

    Returns:
        工具执行结果；执行异常时返回描述异常的字符串。
    """
    try:
        return await tool.ainvoke(args)
    except Exception as e:  # 占位实现：教学示例统一兜底，避免单个工具异常中断整图
        print(f"工具调用错误：{e}")
        return f"工具调用异常: {str(e)}"


# 工具调度
async def researcher_tools(
    state: ResearcherState, config
) -> Command[Literal["researcher", "compress_research"]]:
    """执行 researcher（研究员）发起的工具调用，并决定下一步走向。"""
    most_recent_message = state["researcher_messages"][-1]

    # 无工具调用，说明模型已直接作答，进入压缩节点
    if not most_recent_message.tool_calls:
        return Command(goto="compress_research")

    tools = get_all_tool()
    tools_by_name = {tool.name: tool for tool in tools}

    tool_calls = most_recent_message.tool_calls

    tool_execution_tasks = [
        execute_tool_safely(tools_by_name[tc["name"]], tc["args"]) for tc in tool_calls
    ]
    # 并发执行工具
    observations = await asyncio.gather(*tool_execution_tasks)

    tool_outputs = [
        ToolMessage(content=observation, name=tc["name"], tool_call_id=tc["id"])
        for observation, tc in zip(observations, tool_calls)
    ]

    exceed_iterations = state.get("tool_call_iterations", 0) >= MAX_REACT_TOOL_CALLS
    research_complete = any(
        tc["name"] == "ResearchComplete" for tc in tool_calls
    )

    if exceed_iterations or research_complete:
        return Command(goto="compress_research", update={"researcher_messages": tool_outputs})

    return Command(goto="researcher", update={"researcher_messages": tool_outputs})


# 压缩研究系统提示词
compress_research_system_prompt = """你是一名研究助理，已经针对某个主题完成了研究。你的任务是整理这些研究发现。

  <Task>
  整理从思考与工具调用中收集到的信息。所有相关信息都必须逐字保留、原样重复。
  本步骤的目的仅仅是移除明显无关或重复的信息。
  </Task>

  <Guidelines>
  1. 你的输出应当完整全面，包含收集到的全部信息和来源
  2. 为每个来源添加行内引用标注，如 [1]、[2] 等
  3. 在结尾处包含一个 "Sources" 章节，列出所有来源及其引用编号
  4. 务必包含所有来源——后续会有另一个 LLM 将本报告与其他报告合并
  </Guidelines>
  """


# 压缩研究发现
async def compress_research(state: ResearcherState, config) -> dict:
    """压缩并综合研究发现。"""
    researcher_messages = state.get("researcher_messages", [])
    researcher_messages.append(
        HumanMessage(content="请整理这些结果，但不要进行概括——必须逐字、完整地保留所有相关信息。")
    )

    # 上下文（压缩提示词 + 历史消息）
    messages = [SystemMessage(content=compress_research_system_prompt)] + researcher_messages
    response = await get_model().ainvoke(messages)

    raw_notes_content = "\n".join([
        str(message.content)
        for message in filter_messages(researcher_messages, include_types=["tool", "ai"])
    ])

    return {
        "compressed_research": str(response.content),
        "raw_notes": [raw_notes_content]
    }


# 构建 researcher 子图
researcher_builder = StateGraph(ResearcherState, output_schema=ResearcherOutputState)

# 添加节点
researcher_builder.add_node("researcher", researcher)
researcher_builder.add_node("researcher_tools", researcher_tools)
researcher_builder.add_node("compress_research", compress_research)

# 添加边
researcher_builder.add_edge(START, "researcher")
researcher_builder.add_edge("researcher", "researcher_tools")
researcher_builder.add_edge("compress_research", END)

# 编译
researcher_graph = researcher_builder.compile()

test_query = "使用大语言模型（LLM）进行提示词工程（prompt engineering）有哪些最佳实践?"

# 初始化状态
initial_state = {
    "researcher_messages": [HumanMessage(content=test_query)],
    "researcher_topic": test_query,
    "tool_call_iterations": 0
}


async def main() -> None:
    """以脚本方式运行 researcher 子图的端到端调用示例。"""
    result = await researcher_graph.ainvoke(initial_state)
    print("=" * 60)
    print("研究的历史消息:\n")
    print("=" * 60)

    for message in result["researcher_messages"]:
        message.pretty_print()

    print("\n" + "=" * 60)
    print("研究结果:")
    print("=" * 60)
    print(result["compressed_research"])


if __name__ == "__main__":
    asyncio.run(main())
