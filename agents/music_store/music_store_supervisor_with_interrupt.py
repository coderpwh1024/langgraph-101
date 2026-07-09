import ast
from typing import Annotated
from typing import Literal
from typing import NotRequired
from typing import TypedDict

from langchain_community.utilities import SQLDatabase
from langchain_core.messages import AIMessage
from langchain_core.messages import AnyMessage
from langchain_core.messages import HumanMessage
from langchain_core.messages import SystemMessage
from langgraph.constants import END
from langgraph.constants import START
from langgraph.graph import StateGraph
from langgraph.graph import add_messages
from langgraph.managed import RemainingSteps
from langgraph.types import interrupt
from pydantic import BaseModel
from pydantic import Field

from agents.music_store.music_store_supervisor import supervisor
from agents.utils.models import model
from agents.utils.utils import get_engine_for_chinook_db

# 数据库
engine = get_engine_for_chinook_db()
db = SQLDatabase(engine)


class InputState(TypedDict):
    """带验证中断的音乐商店客服图输入状态。"""

    messages: Annotated[list[AnyMessage], add_messages]


class State(InputState):
    """带验证中断的音乐商店客服图运行时状态。"""

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
def get_customer_id_from_identifier(identifier: str) -> int | None:
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


# 校验信息
def verify_info(state: State) -> dict:
    """通过解析客户输入并与数据库匹配来验证客户账户。"""

    if state.get("customer_id") is None:
        system_instructions = """你是一个音乐商店智能体，当前正在执行客服流程的第一步：验证客户身份。

          只有在客户账户验证通过后，你才能继续帮助他们解决问题。

          为了验证客户身份，客户需要提供 customer ID、邮箱或手机号中的任意一种。

          如果客户尚未提供标识符，请向他们索要。
          如果客户已经提供了标识符但无法找到对应账户，请要求他们修改后重新提供。"""

        user_input = state["messages"][-1]

        # Parse for customer ID
        parsed_info = structured_llm.invoke([SystemMessage(content=structured_system_prompt)] + [user_input])

        # Extract details
        identifier = parsed_info.identifier

        customer_id = ""
        # Attempt to find the customer ID
        if (identifier):
            customer_id = get_customer_id_from_identifier(identifier)

        if customer_id != "":
            intent_message = AIMessage(
                content=f"Thank you for providing your information! I was able to verify your account with customer id {customer_id}."
            )
            return {
                "customer_id": customer_id,
                "messages": [intent_message]
            }
        else:
            response = model.invoke([SystemMessage(content=system_instructions)] + state['messages'])
            return {"messages": [response]}

    else:
        pass


def human_input(state: State):
    """空操作节点，用于在此处触发中断。"""
    user_input = interrupt("Please provide input.")
    return {"messages": [HumanMessage(content=user_input)]}


def should_interrupt(state: State) -> Literal["continue", "interrupt"]:
    if state.get("customer_id") is not None:
        return "continue"
    else:
        return "interrupt"


multi_agent_verify = StateGraph(State, input_schema=InputState)

# node
multi_agent_verify.add_node("verify_info", verify_info)
multi_agent_verify.add_node("human_input", human_input)
multi_agent_verify.add_node("supervisor", supervisor)

# edge
multi_agent_verify.add_edge(START, "verify_info")
multi_agent_verify.add_conditional_edges(
    "verify_info",
    should_interrupt,
    {
        "continue": "supervisor",
        "interrupt": "human_input",
    },
)

multi_agent_verify.add_edge("human_input", "verify_info")
multi_agent_verify.add_edge("supervisor", END)

# 编译
graph = multi_agent_verify.compile(name="multi_agent_verify")
