from langchain.agents import create_agent
from langchain_core.messages import AnyMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph import add_messages
from langgraph.prebuilt import ToolRuntime
from sqlalchemy.sql.annotation import Annotated
from typedict import TypeDict

from agents.music_store import invoice_agent
from agents.music_store.music_agenty import graph as music_agent
from agents.utils.models import model


class InputState(TypeDict):
    messages: Annotated[list[AnyMessage], add_messages]


class State(InputState):
    customer_id: int
    loaded_memory: str
    remaining_steps: int


supervisor_prompt = """你是一名数字音乐商店的专业客服助手。你可以处理与音乐目录或发票相关的问题，包括过往购买记录、歌曲或专辑是否可用等。

  你致力于提供卓越服务，并确保客户问题得到全面解答。你拥有一个由多个子代理组成的团队，可以调用它们来协助回答客户问题。

  你的主要职责是作为这个多代理团队的主管/规划者，帮助回答客户的查询。始终通过总结对话来回复客户，并包含各个子代理的独立回复。

  如果问题与音乐或发票无关，请礼貌提醒客户你的工作范围。不要回答无关问题。

  你的团队由两个可用于回答客户请求的子代理组成：
  1. music_catalog_information_subagent：该子代理可以访问用户保存的音乐偏好。它还可以从数据库中检索数字音乐商店的音乐目录信息，包括专辑、曲目、歌曲等。该子代理可以访问用户的记忆档案和音乐偏好，并会自动
  从记忆档案中推断用户的音乐偏好。不需要向该子代理传递客户标识符。
  2. invoice_information_subagent：该子代理可以从数据库中检索客户的过往购买记录或发票信息。

  根据消息中已经执行过的步骤，你的职责是基于用户查询调用合适的子代理"""


@tool(name_or_callable="invoice_information_subagent", description="""
          一个可以协助处理所有发票相关查询的智能体。它可以检索客户过往购买记录或发票的信息。
          """)
def call_invoice_information_subagent(runtime: ToolRuntime, query: str):
    print('made it here')
    print(f"invoice subagent input:{query}")
    result = invoice_agent.invoke({
        "messages": [HumanMessage(content=query)],
        "customer_id": runtime.state.get("customer_id", {})
    })
    subagent_response = result["messages"][-1].content
    return subagent_response


# 音乐目录子 agent
@tool(name_or_callable="music_catalog_subagent", description="""
          一个可以协助处理所有音乐相关查询的智能体。该智能体可以访问用户已保存的音乐偏好，
          也可以从数据库中检索数字音乐商店的音乐目录信息，
          包括专辑、曲目、歌曲等。
          """)
def call_music_catalog_subagent(runtime: ToolRuntime, query: str):
    result = music_agent.invoke({
        "messages": [HumanMessage(content=query)],
        "load_memory": runtime.state.get("loaded_memory", {})
    })
    subagent_response = result["messages"][-1].content
    return subagent_response


# 构建监督者 agent
supervisor = create_agent(
    model=model,
    tools=[call_music_catalog_subagent, call_invoice_information_subagent],
    name="supervisor",
    system_prompt=supervisor_prompt,
    state_schema=State
)
