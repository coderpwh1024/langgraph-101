import os
import sys
from datetime import datetime
from pathlib import Path
from typing import TypedDict, Literal, Annotated

from langchain.agents import create_agent
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.constants import END, START
from langgraph.graph import StateGraph
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from langgraph.store.memory import InMemoryStore
from langsmith import uuid7
from pydantic import BaseModel

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.models import model

# 初始化长期记忆
in_memory_store = InMemoryStore()

# 创建长期记忆保存器
checkpointer = MemorySaver()

print("-----------------------------01-创建 email Agent---------------------------------------")


# 创建状态(State继承 TypeDict)
class State(TypedDict):
    email_input: dict
    classification_decision: Literal["ignore", "respond", "notify"]
    messages: Annotated[list[AnyMessage], add_messages]
    loaded_memory: str


# 创建会议工具
@tool
def schedule_meeting(attendees: list[str], subject: str, duration_minutes: int, preferred_day: datetime,
                     start_time: int) -> str:
    """安排一个日历会议"""
    date_str = preferred_day.strftime("%A,%B %d,%Y")
    return f"会议:'{subject}' 已安排在:{date_str} ,{start_time},时长:{duration_minutes}分钟,共{len(attendees)}位参会者 "


# 创建检查日历可用时间工具
@tool
def check_calendar_availability(day: str) -> str:
    """查询某一天的日历可用时间"""
    return f"{day}的可用时间:上午 9:00,下午 2:00,下午 4:00"


# 创建写邮件工具
@tool
def write_email(to: str, subject: str, content: str) -> str:
    """写邮件并发送"""
    return f"邮件发送给:{to},主题:{subject},内容:{content}"


@tool
class Done(BaseModel):
    """邮件已经发送"""
    done: bool


# 工具集合
tools = [schedule_meeting, check_calendar_availability, write_email, Done]
tools_by_name = {tool.name: tool for tool in tools}

llm_with_tools = model.bind_tools(tools, tool_choice="any")

# 创建工具节点
tool_node = ToolNode(tools)


# 解析邮件
def parse_email(email_input: dict) -> dict:
    return (
        email_input["author"],
        email_input["to"],
        email_input["subject"],
        email_input["email_thread"],
    )


# markdown 格式邮件解析
def format_email_markdown(subject, author, to, email_thread, email_id=None):
    id_section = f"\n**ID**:{email_id}" if email_id else ""
    return f"""
      **主题**:{subject}
      **作者**:{author}
      **来自**: {to}{id_section}
      {email_thread}
      
      ---
     """


# 提示词函数
def create_agent_prompt(state: State):
    action_instructions = """
        < 角色 >
        你是一名顶级的行政助理，致力于帮助你的高管表现得尽可能出色。
        </ 角色 >

        < 工具 >
        你可以使用以下工具来帮助管理沟通和日程安排：

        1. write_email(to, subject, content) - 向指定收件人发送电子邮件
        2. schedule_meeting(attendees, subject, duration_minutes, preferred_day, start_time) - 安排日历会议
        3. check_calendar_availability(day) - 查询某一天的空闲时间段
        4. Done - 邮件已发送
        </ 工具 >

        < 说明 >
        处理邮件时，请遵循以下步骤：
        1. 仔细分析邮件内容和目的
        3. 在回复邮件时，使用 write_email 工具起草一封回复邮件
        4. 对于会议请求，使用 check_calendar_availability 工具查找空闲时间段
        5. 要安排会议，使用 schedule_meeting 工具，并为 preferred_day 参数传入一个 datetime 对象
        - 今天的日期是 {today} —— 安排会议时请据此准确处理
        6. 如果你安排了会议，则使用 write_email 工具起草一封简短的回复邮件
        7. 使用 write_email 工具之后，任务即告完成
        8. 如果你已发送邮件，则使用 Done 工具来表明任务已完成
        </ 说明 >

        < 背景 >
        我是 Robert，LangChain 的一名软件工程师。
        </ 背景 >

        < 回复偏好 >
        使用专业而简洁的语言。如果邮件中提到了截止日期，请务必在回复中明确确认并引用该截止日期。

        在回复需要调查的技术问题时：
        - 明确说明你将进行调查，或者你将询问谁
        - 提供一个预计的时间表，说明你何时能获得更多信息或完成该任务

        在回复活动或会议邀请时：
        - 始终确认提到的任何截止日期（尤其是报名截止日期）
        - 如果提到了研讨会或特定主题，询问有关它们的更具体细节
        - 如果提到了折扣（团体或早鸟折扣），明确请求有关这些折扣的信息
        - 不要做出承诺

        在回复合作或项目相关请求时：
        - 确认提到的任何现有工作或材料（草稿、幻灯片、文档等）
        - 明确提及将在会议之前或会议期间审阅这些材料
        - 安排会议时，清楚说明所提议的具体日期、星期几和时间。

        在回复会议安排请求时：
        - 如果收件人要求确定会议安排，先核实原邮件中提到的所有时间段的可用性，然后根据你的空闲情况通过安排会议来确定其中一个所提议的时间。或者，说明你无法在所提议的时间出席。
        - 如果对方询问的是可用时间，则查询你的日历空闲情况，并在有空时发送一封提议多个时间选项的邮件。不要安排会议。
        - 在回复中提及会议时长，以确认你已正确记录。
        - 在回复中引用会议的目的。
        </ 回复偏好 >

        < 日历偏好 >
        优先安排 30 分钟的会议，但 15 分钟的会议也可以接受。
        一天中较晚的时间更为理想。
        </ 日历偏好 >
        """
    email = parse_email(state["email_input"])
    email_markdown = format_email_markdown(email[2], email[0], email[1], email[3])
    email_request = f"请回复以下邮件：{email_markdown}"

    prompt = [
        SystemMessage(content=action_instructions.format(today=datetime.now().strftime("%Y-%m-%d"))),
        HumanMessage(content=email_request)
    ]

    return prompt + state["messages"]


# 理解节点
def reasoning_node(state: State):
    """LLM 决定是否调用工具"""
    prompt = create_agent_prompt(state)
    result = llm_with_tools.invoke(prompt)

    return {"messages": [result]}


# 条件路由：决定下一步去工具节点还是结束
def should_continue(state: State) -> Literal["tools", "__end__"]:
    """ 路由到工具节点；若本轮已调用 Done 工具，则结束"""
    messages = state["messages"]
    last_message = messages[-1]

    # 兜底：没有工具调用时（理论上 tool_choice="any" 不会发生）直接结束，避免返回 None
    tool_calls = getattr(last_message, "tool_calls", None)
    if not tool_calls:
        return END

    # 只要本轮存在 Done 调用就结束，否则才去执行工具（遍历完所有 tool_call 再判断）
    if any(tool_call["name"] == "Done" for tool_call in tool_calls):
        return END
    return "tools"


# 构建 workflow
agent_builder = StateGraph(State)

# 添加节点
agent_builder.add_node("agent", reasoning_node)
agent_builder.add_node("tools", tool_node)

# 添加边
agent_builder.add_edge(START, "agent")
agent_builder.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        END: END
    }
)
# 构建 agent
agent_builder.add_edge("tools", "agent")
agent = agent_builder.compile(checkpointer=checkpointer, store=in_memory_store)

# recursion_limit 为图的最大执行步数上限：若模型一直不调用 Done，
# agent↔tools 循环到达上限会抛 GraphRecursionError，避免无限循环
config = {"configurable": {"thread_id": uuid7()}, "recursion_limit": 25}
email_input = {
    "to": "徐罗伯特 <Robert@company.com>",
    "author": "团队负责人 <teamlead@company.com>",
    "subject": "季度规划会议",
    "email_thread": "你好，罗伯特：\n\n又到了我们季度规划会议的时间。我想在下周安排一场 90 分钟的会议，讨论我们 Q3 的路线图。\n\n你能告诉我你周一或周三的空闲时间吗？最好是上午 10 点到下午 3点之间。\n\n期待听到你对新功能优先级的意见。\n\n此致\n团队负责人"
}

result = agent.invoke(
    {
        "email_input": email_input
    },
    config=config
)

print("正在回复邮件：")
print(format_email_markdown(email_input["subject"], email_input["author"], email_input["to"],
                            email_input["email_thread"]))

# 输出结果
for message in result["messages"]:
    message.pretty_print()

print("\n")
print("-----------------------------02-创建使用预编制---------------------------------------")

action_instructions = """
< 角色 >
你是一名顶级的行政助理，致力于帮助你的高管表现得尽可能出色。
</ 角色 >

< 工具 >
你可以使用以下工具来帮助管理沟通和日程安排：

1. write_email(to, subject, content) - 向指定收件人发送电子邮件
2. schedule_meeting(attendees, subject, duration_minutes, preferred_day, start_time) - 安排日历会议
3. check_calendar_availability(day) - 查询某一天的空闲时间段
4. Done - 邮件已发送
</ 工具 >

< 说明 >
处理邮件时，请遵循以下步骤：
1. 仔细分析邮件内容和目的
3. 在回复邮件时，使用 write_email 工具起草一封回复邮件
4. 对于会议请求，使用 check_calendar_availability 工具查找空闲时间段
5. 要安排会议，使用 schedule_meeting 工具，并为 preferred_day 参数传入一个 datetime 对象
- 今天的日期是 {today} —— 安排会议时请据此准确处理
6. 如果你安排了会议，则使用 write_email 工具起草一封简短的回复邮件
7. 使用 write_email 工具之后，任务即告完成
8. 如果你已发送邮件，则使用 Done 工具来表明任务已完成
</ 说明 >

< 背景 >
我是 Robert，LangChain 的一名软件工程师。
</ 背景 >

< 回复偏好 >
- 保持回复专业但友好
- 简洁、切中要点
- 如果安排会议，尽可能提议 2-3 个时间选项
</ 回复偏好 >
"""

system_prompt_string = action_instructions.format(today=datetime.now().strftime("%Y-%m-%d"))

email_prebuilt = create_agent(
    model=model,
    tools=tools,
    name="email_prebuilt",
    system_prompt=system_prompt_string,
    state_schema=State,
    checkpointer=checkpointer,
    store=in_memory_store
)

email_prebuilt

config = {"configurable": {"thread_id": uuid7()}}

email_input = {
    "to": "Robert Xu <Robert@company.com>",
    "author": "Team Lead <teamlead@company.com>",
    "subject": "季度规划会议",
    "email_thread": "你好 Robert，\n\n又到了我们季度规划会议的时间了。我想在下周安排一个 90 分钟的会议，讨论我们第三季度（Q3）的路线图。\n\n你能告诉我你周一或周三的空闲时间吗？最好是在上午 10 点到下午 3 点之间。\n\n期待你对新功能优先级的意见。\n\n此致，\nTeam Lead"
}

result = email_prebuilt.invoke({
    "email_input": email_input,
    "messages": [HumanMessage(content=f"""
     请回复以下邮件：

  **主题**：{email_input['subject']}
  **发件人**：{email_input['author']}
  **收件人**：{email_input['to']}
  
  {email_input['email_thread']}
     """)]}, config=config
)

print("\n")
print("正在回复邮件：")
print(format_email_markdown(email_input["subject"], email_input["author"], email_input["to"],
                            email_input["email_thread"]))
# 打印结果
for message in result["messages"]:
    message.pretty_print()
