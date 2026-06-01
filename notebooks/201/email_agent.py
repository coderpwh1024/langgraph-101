import os
import sys
from datetime import datetime
from pathlib import Path
from typing import TypedDict, Literal, Annotated

from langchain_core.tools import tool
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.checkpoint.memory import MemorySaver
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


# 创建状态
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
