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
from langchain_core.stores import BaseStore
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

engine = get_engine_for_chinook_db()
db = SQLDatabase(engine)


class InputState(TypedDict):
    """音乐商店客服图的输入状态。"""

    messages: Annotated[list[AnyMessage], add_messages]


class State(InputState):
    """音乐商店客服图在执行过程中维护的完整状态。"""

    customer_id: NotRequired[int]
    loaded_memory: NotRequired[str]
    remaining_steps: NotRequired[RemainingSteps]


class UserInput(BaseModel):
    """用于解析用户提供的账户信息。"""

    identifier: str = Field(
        description="客户标识符，可以是 customer ID、邮箱或电话号码；未提供时返回空字符串。"
    )


class UserProfile(BaseModel):
    """客户长期记忆档案。"""

    customer_id: str = Field(description="客户 ID。")
    music_preferences: list[str] = Field(description="客户明确表达过的音乐偏好列表。")


STRUCTURED_SYSTEM_PROMPT = """你是一名客户服务代表，负责提取客户标识符。
只从消息历史中提取客户的账户信息。
如果客户尚未提供相关信息，则将 identifier 返回为空字符串。"""


CREATE_MEMORY_PROMPT = """你是一名专家分析师，正在观察一段客户与客户支持助手之间已经发生的对话。
该客户支持助手服务于一家数字音乐商店，并使用了一个多智能体团队来回答客户的请求。

你的任务是分析客户与客户支持助手之间已经发生的对话，并更新与该客户关联的记忆档案。
你需要特别关注客户在对话中分享的任何音乐兴趣，尤其是他们的音乐偏好，并将其保存到记忆档案中。

<core_instructions>
1. 记忆档案可能为空。如果为空，你应该始终为该客户创建新的记忆档案。
2. 你应该识别客户在对话中表达的任何音乐兴趣，并在这些信息尚未存在时将其添加到记忆档案中。
3. 对于记忆档案中的每个键，如果没有新的信息，不要更新对应的值，保持现有值不变。
4. 只有在存在新信息时，才更新记忆档案中的值。
</core_instructions>

<expected_format>
客户的记忆档案应包含以下字段：
- customer_id: 客户的客户 ID
- music_preferences: 客户的音乐偏好

重要：确保你的响应是一个包含这些字段的对象。
</expected_format>

<important_context>
以下是重要上下文。

你需要分析的客户与客户支持助手之间的对话如下：
{conversation}

与该客户关联、需要你基于对话更新或创建的现有记忆档案如下：
{memory_profile}
</important_context>

提醒：请深呼吸，并在回复前仔细思考。
"""


structured_llm = model.with_structured_output(schema=UserInput)


def get_customer_id_from_identifier(identifier: str) -> int | None:
    """使用客户标识符检索客户 ID。

    Args:
        identifier: 客户标识符，可以是 customer ID、邮箱或电话号码。

    Returns:
        如果找到客户则返回 CustomerId，否则返回 None。
    """
    normalized_identifier = identifier.strip()
    if not normalized_identifier:
        return None

    if normalized_identifier.isdigit():
        return int(normalized_identifier)

    if normalized_identifier.startswith("+"):
        # 注意：教学示例沿用 SQL 拼接；生产环境应改用参数化查询以防 SQL 注入。
        query = (
            "SELECT CustomerId FROM Customer "
            f"WHERE Phone = '{normalized_identifier}';"
        )
    elif "@" in normalized_identifier:
        # 注意：教学示例沿用 SQL 拼接；生产环境应改用参数化查询以防 SQL 注入。
        query = (
            "SELECT CustomerId FROM Customer "
            f"WHERE Email = '{normalized_identifier}';"
        )
    else:
        return None

    result = db.run(query)
    try:
        formatted_result = ast.literal_eval(result)
    except (SyntaxError, ValueError):
        return None

    if formatted_result:
        return formatted_result[0][0]
    return None


def verify_info(state: State) -> dict:
    """验证客户身份，未通过时引导客户继续提供账户信息。

    Args:
        state: 当前图状态。

    Returns:
        包含验证结果消息和可选 customer_id 的状态增量。
    """
    if state.get("customer_id") is not None:
        return {}

    system_instructions = """你是一个音乐商店客服智能体，当前客服流程的第一步是验证客户身份。
只有在客户账户通过验证后，你才能继续帮助他们解决问题。
为了验证身份，客户需要提供 customer ID、邮箱或电话号码中的任意一种。
如果客户尚未提供标识符，请向他们索要。
如果客户已经提供了标识符但无法查到对应账户，请让他们修改后重新提供。"""

    user_input = state["messages"][-1]
    parsed_info = structured_llm.invoke(
        [SystemMessage(content=STRUCTURED_SYSTEM_PROMPT), user_input]
    )
    customer_id = get_customer_id_from_identifier(parsed_info.identifier)

    if customer_id is not None:
        intent_message = AIMessage(
            content=(
                "Thank you for providing your information! I was able to "
                f"verify your account with customer id {customer_id}."
            )
        )
        return {
            "customer_id": customer_id,
            "messages": [intent_message],
        }

    response = model.invoke(
        [SystemMessage(content=system_instructions)] + state["messages"]
    )
    return {"messages": [response]}


def human_input(state: State) -> dict:
    """触发人工输入中断，并将恢复输入写回消息历史。

    Args:
        state: 当前图状态。

    Returns:
        包含用户恢复输入的状态增量。
    """
    user_input = interrupt("请提供输入。")
    return {"messages": [HumanMessage(content=user_input)]}


def should_interrupt(state: State) -> Literal["continue", "interrupt"]:
    """根据客户身份是否已验证决定后续路由。

    Args:
        state: 当前图状态。

    Returns:
        已验证时返回 ``continue``，否则返回 ``interrupt``。
    """
    if state.get("customer_id") is not None:
        return "continue"
    return "interrupt"


def format_user_memory(user_data: dict) -> str:
    """格式化用户的音乐偏好。

    Args:
        user_data: 从长期记忆 store 读取出的用户记忆数据。

    Returns:
        可注入提示词的音乐偏好文本；没有偏好时返回空字符串。
    """
    profile = user_data.get("memory", {})

    if isinstance(profile, dict):
        music_preferences = profile.get("music_preferences", [])
    else:
        music_preferences = getattr(profile, "music_preferences", [])

    if isinstance(music_preferences, str):
        return music_preferences.strip()
    if music_preferences:
        return f"Music Preferences: {', '.join(music_preferences)}"
    return ""


def load_memory(state: State, store: BaseStore) -> dict:
    """加载当前客户的长期音乐偏好记忆。

    Args:
        state: 当前图状态。
        store: LangGraph 长期记忆存储。

    Returns:
        包含 loaded_memory 的状态增量。
    """
    user_id = str(state["customer_id"])
    namespace = ("memory_profile", user_id)
    existing_memory = store.get(namespace, "user_memory")

    formatted_memory = ""
    if existing_memory and existing_memory.value:
        formatted_memory = format_user_memory(existing_memory.value)

    return {"loaded_memory": formatted_memory}


def create_memory(state: State, store: BaseStore) -> dict:
    """基于当前对话更新客户长期记忆。

    Args:
        state: 当前图状态。
        store: LangGraph 长期记忆存储。

    Returns:
        空状态增量。
    """
    user_id = str(state["customer_id"])
    namespace = ("memory_profile", user_id)
    formatted_system_message = SystemMessage(
        content=CREATE_MEMORY_PROMPT.format(
            conversation=state["messages"],
            memory_profile=state.get("loaded_memory", ""),
        )
    )
    user_prompt = HumanMessage(content="请根据指令分析对话内容，并更新客户的记忆画像。")
    updated_memory = model.with_structured_output(schema=UserProfile).invoke(
        [formatted_system_message, user_prompt]
    )
    store.put(namespace, "user_memory", {"memory": updated_memory.model_dump()})
    return {}


multi_agent_final = StateGraph(State, input_schema=InputState)

multi_agent_final.add_node("verify_info", verify_info)
multi_agent_final.add_node("human_input", human_input)
multi_agent_final.add_node("load_memory", load_memory)
multi_agent_final.add_node("supervisor", supervisor)
multi_agent_final.add_node("create_memory", create_memory)

multi_agent_final.add_edge(START, "verify_info")
multi_agent_final.add_conditional_edges(
    "verify_info",
    should_interrupt,
    {
        "continue": "load_memory",
        "interrupt": "human_input",
    },
)
multi_agent_final.add_edge("human_input", "verify_info")
multi_agent_final.add_edge("load_memory", "supervisor")
multi_agent_final.add_edge("supervisor", "create_memory")
multi_agent_final.add_edge("create_memory", END)

agent = multi_agent_final.compile(name="multi_agent_final")
