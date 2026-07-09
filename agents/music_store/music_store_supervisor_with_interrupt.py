import ast

from langchain_community.utilities import SQLDatabase
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from langgraph.managed import RemainingSteps
from typedict import TypeDict
from typing import Annotated, Optional, NotRequired

from agents.utils.models import model
from agents.utils.utils import get_engine_for_chinook_db
from pydantic import BaseModel, Field

# 数据库
engine = get_engine_for_chinook_db()
db = SQLDatabase(engine)


class InputState(TypeDict):
    messages: Annotated[list[AnyMessage], add_messages]


class State(InputState):
    customer_id: NotRequired[str]
    loaded_memory: NotRequired[str]
    remaining_steps: NotRequired[RemainingSteps]


class UserInput(BaseModel):
    """用于解析用户提供的账户信息的 schema"""
    identifier: str = Field(description="")


#
structured_system_prompt = """你是一名客服代表，负责提取客户标识符。
  只从消息历史中提取客户的账户信息。
  如果客户尚未提供相关信息，则将该字段返回为空字符串。"""

structured_llm = model.with_structured_output(schema=UserInput)


# 获取客户 ID
def get_customer_id_from_identifier(identifier: str) -> Optional[int]:
    """
    使用标识符检索客户 ID，该标识符可以是客户 ID、邮箱或手机号。

    Args:
         identifier: 标识符，可以是客户 ID、邮箱或手机号。

    Returns:
           如果找到则返回 CustomerId，否则返回 None。
    """
    if identifier.isdigit():
        return int(identifier)
    elif identifier[0] == "+":
        query = f"SELECT CustomerId FROM Customer WHERE Phone = '{identifier}';"
        result = db.run(query)
        formatted_result = ast.literal_eval(result)
        if formatted_result:
            return formatted_result[0][0]
    elif "@" in identifier:
        query = f"SELECT CustomerId FROM Customer WHERE Email = '{identifier}';"
        result = db.run(query)
        formatted_result = ast.literal_eval(result)
        if formatted_result:
            return formatted_result[0][0]
    return None
