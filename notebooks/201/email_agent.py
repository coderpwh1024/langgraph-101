import os
import sys
from datetime import datetime
from pathlib import Path
from typing import TypedDict, Literal, Annotated

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.constants import END
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from langgraph.store.memory import InMemoryStore
from pydantic import BaseModel

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


# 创建状态(State继承 TypeDict)
class State(TypedDict):
    email_input: dict
    classification_decision: Literal["ignore", "respond", "notify"]
    messages: Annotated[list[AnyMessage], add_messages]
    loaded_memory: str
    remaining_steps: int


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

    prompt = {
        SystemMessage(action_instructions.format(today=datetime.now().strftime("%Y-%m-%d"))),
        HumanMessage(content=email_request)
    }

    return prompt + state["messages"]


# 理解节点
def reasoning_node(state: State):
    """LLM 决定是否调用工具"""
    prompt = create_agent_prompt(state),
    result = llm_with_tools.invoke(prompt)

    return {"messages": [result]}


# 工具节点
def should_continue(state: State) -> Literal["Tools", "__end__"]:
    """ 路由到工具节点；若已调用 Done 工具，则结束"""
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            if tool_call["name"] == "Done":
                return END
            else:
                return "Tools"
