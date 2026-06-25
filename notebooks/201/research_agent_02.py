import asyncio
import operator
from typing import Annotated, Literal, NotRequired, TypedDict

from langchain_core.messages import (
    HumanMessage,
    MessageLikeRepresentation,
    ToolMessage,
    filter_messages, SystemMessage,
)
from langchain_core.tools import tool
from langgraph.constants import START
from langgraph.graph import END, StateGraph
from langgraph.types import Command

from notebooks.utils.utils import show_graph
# 复用 research_agent 中已编译好的 researcher 子图与共享工具
from research_agent import (
    MAX_STRUCTURED_OUTPUT_RETRIES,
    ResearchComplete,
    get_model,
    researcher_graph,
    think_tool, get_today_str,
)

# 全局配置
MAX_RESEARCHER_ITERATIONS = 3  # supervisor 委派研究的最大轮次
MAX_CONCURRENT_RESEARCH_UNITS = 3  # 每轮最多并行的 researcher 子 Agent 数


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


# 提示词
lead_researcher_prompt = """你是一名研究主管（research supervisor）。你的工作是通过调用 "ConductResearch" 工具来开展研究。

  <Task>
  调用 "ConductResearch" 工具来委派研究任务。当你对研究结果感到满意时，调用 "ResearchComplete"。
  </Task>

  <Available Tools>
  1. **ConductResearch**：将研究任务委派给专门的子 Agent（sub-agent）
  2. **ResearchComplete**：表示研究已完成
  3. **think_tool**：用于反思与策略规划

  **关键：在调用 ConductResearch 之前先用 think_tool 做规划，调用之后再用它评估进展。**
  </Available Tools>

  <Instructions>
  像一名研究经理（research manager）那样思考：

  1. **仔细阅读问题** —— 究竟需要哪些具体信息？
  2. **决定如何委派** —— 是否可以同时探索多个相互独立的角度？
  3. **每次调用 ConductResearch 之后都要评估** —— 我掌握的信息够了吗？还缺什么？
  </Instructions>

  <Hard Limits>
  - **限制工具调用次数** —— 如果找不到合适的信息源，在 {max_researcher_iterations} 次工具调用后停止
  - **每轮迭代最多 {max_concurrent_research_units} 个并行 Agent**
  </Hard Limits>

  <Scaling Rules>
  **简单查询** —— 使用单个子 Agent
  **对比类任务** —— 为每个待对比的对象分配一个子 Agent
  **重要**：调用 ConductResearch 时，要提供完整、可独立执行的指令
  </Scaling Rules>
  """


# Supervisor agent
async def supervisor(state: SupervisorState, config):
    """委派研究任务的 Supervisor agent"""
    lead_researcher_tools = [ConductResearch, ResearchComplete, think_tool]

    research_model = (
        get_model().bind_tools(lead_researcher_tools).with_retry(stop_after_attempt=MAX_STRUCTURED_OUTPUT_RETRIES)
    )

    supervisor_messages = state.get("supervisor_messages", [])
    response = await research_model.ainvoke(supervisor_messages)

    return {
        "supervisor_messages": [response],
        "research_iterations": state.get("research_iterations", 0) + 1
    }


# 笔记提取
def extract_tool_content(messages):
    """从工具调用消息中提取笔记"""
    return [tool_msg.content for tool_msg in filter_messages(messages, include_types="tool")]


# 构建 Supervisor工具
async def supervisor_tools(state: SupervisorState, config) -> Command[Literal["supervisor", "__end__"]]:
    """执行由 supervisor（监督者）发起的工具调用"""

    supervisor_messages = state.get("supervisor_messages", [])
    research_iterations = state.get("research_iterations", 0)
    most_recent_message = supervisor_messages[-1]

    exceeded_iterations = research_iterations > MAX_RESEARCHER_ITERATIONS
    no_tool_calls = not most_recent_message.tool_calls

    research_complete = any(tc["name"] == "ResearchComplete" for tc in most_recent_message.tool_calls)

    if exceeded_iterations or no_tool_calls or research_complete:
        return Command(
            goto=END,
            update={
                "notes": extract_tool_content(supervisor_messages),
                "research_brief": state.get("research_brief", "")
            }
        )

    all_tool_messages = []
    update_payload = {"supervisor_messages": []}

    for tc in most_recent_message.tool_calls:
        if tc["name"] == "think_tool":
            all_tool_messages.append(
                ToolMessage(
                    content=f"反思已记录:{tc['args']['reflection']}",
                    name="think_tool",
                    tool_call_id=tc["id"],
                )
            )

    conduct_research_calls = [tc for tc in most_recent_message.tool_calls if tc["name"] == "ConductResearch"]

    if conduct_research_calls:
        try:
            allowed_calls = conduct_research_calls[:MAX_CONCURRENT_RESEARCH_UNITS]
            overflow_calls = conduct_research_calls[MAX_CONCURRENT_RESEARCH_UNITS:]

            research_task = [ConductResearch.ainvoke(tc["args"]) for tc in allowed_calls]

            tool_results = await asyncio.gather(*research_task)

            for observation_dict, tc in zip(tool_results, allowed_calls):
                all_tool_messages.append(
                    ToolMessage(content=observation_dict.get("compressed_research", "Error in research"),
                                name=tc["name"],
                                tool_call_id=tc["id"]
                                ))

            for overflow_call in overflow_calls:
                all_tool_messages.append(
                    ToolMessage(content=f"错误:已超过允许的最大并发数量({MAX_CONCURRENT_RESEARCH_UNITS})",
                                name="ConductResearch",
                                tool_call_id=overflow_call["id"]
                                ))

            raw_notes_concat = "\n".join([
                "\n".join(obs.get("raw_notes", []))
                for obs in tool_results
            ])
            if raw_notes_concat:
                update_payload["raw_notes"] = [raw_notes_concat]
        except Exception as e:
            return Command(
                goto=END,
                update={
                    "notes": extract_tool_content(supervisor_messages),
                    "research_brief": state.get("research_brief", "")
                }
            )

    update_payload["supervisor_messages"] = all_tool_messages
    return Command(goto="supervisor", update=update_payload)


# 构建 Supervisor 状态图
supervisor_builder = StateGraph(SupervisorState)

# 添加node
supervisor_builder.add_node(supervisor, "supervisor")
supervisor_builder.add_node(supervisor_tools, "supervisor_tools")

# 添加 edge
supervisor_builder.add_edge(START, "supervisor")
supervisor_builder.add_edge("supervisor", "supervisor_tools")

# 编译状态图
supervisor_graph = supervisor_builder.compile()
show_graph(supervisor_graph, xray=True)

research_brief = "推荐一些纽约市（NYC）的中餐厅和印度餐厅"

# 构建系统提示词等
supervisor_system_prompt = lead_researcher_prompt.format(
    date=get_today_str(),
    max_concurrent_research_units=MAX_CONCURRENT_RESEARCH_UNITS,
    max_researcher_iterations=MAX_RESEARCHER_ITERATIONS,
)

initial_sate={
    "supervisor_messages":[
        SystemMessage(content=supervisor_system_prompt),
        HumanMessage(content=research_brief)
    ],
    "research_brief":research_brief,
    "research_iterations":0,
    "notes":[],
    "raw_notes":[]
}

result = await supervisor_graph.ainvoke(initial_sate)

print("="*60)
print("监督者消息历史")
print("="*60)
for i,note in enumerate(result["notes"],1):
    print("f\n --- 搜索发现{i} ---")
    print(note[:500]+"..." if len(note)>500 else note)