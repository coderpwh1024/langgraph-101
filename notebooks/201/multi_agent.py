import ast
import sys
from pathlib import Path

import sqlite3
from time import process_time_ns
from typing import TypedDict, Annotated, List
from langchain.agents import create_agent
import requests
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.stores import InMemoryStore
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import START, END
from langgraph.graph import add_messages, StateGraph
from langgraph.prebuilt import ToolNode, ToolRuntime
from langgraph.types import interrupt
from langsmith import uuid7
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, StaticPool
from langchain_community.utilities.sql_database import SQLDatabase
from sqlalchemy.orm.base import state_str

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.models import model


# 获取数据库连接
def get_engine_for_chinook_db():
    """拉取 SQL 文件，填充内存数据库，并创建引擎。"""
    url = "https://raw.githubusercontent.com/lerocha/chinook-database/master/ChinookDatabase/DataSources/Chinook_Sqlite.sql"
    response = requests.get(url)
    sql_script = response.text

    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.executescript(sql_script)

    return create_engine(
        "sqlite://",
        creator=lambda: connection,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )


# 创建数据库连接
engine = get_engine_for_chinook_db()
db = SQLDatabase(engine)

# 记忆数据存储
in_memory_store = InMemoryStore()

# 初始化 checkpointer
checkpointer = MemorySaver()

print(
    "-------------------------------------------01-构建-子智能体--------------------------------------------------------")


# 输入
class InputState(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]


# 状态
class State(InputState):
    customer_id: int
    loaded_memory: str
    remaining_steps: int


# 获取专辑
@tool
def get_albums_by_artist(artist: str):
    """获取某位艺术家的专辑"""
    return db.run(
        f"""select Album.Title,Artist.Name FROM  Album JOIN Artist ON Album.ArtistId=Artist.ArtistId WHERE Artist.Name LIKE'%{artist}%' """,
        include_columns=True
    )


# 获取歌曲
@tool
def get_tracks_by_artist(artist: str):
    """按艺术家（或相似艺术家）获取歌曲"""
    return db.run(
        f"""
            SELECT Track.Name as SongName, Artist.Name as ArtistName 
            FROM Album 
            LEFT JOIN Artist ON Album.ArtistId = Artist.ArtistId 
            LEFT JOIN Track ON Track.AlbumId = Album.AlbumId 
            WHERE Artist.Name LIKE '%{artist}%';
            """,
        include_columns=True
    )


# 获取歌曲
@tool
def get_song_by_genre(genre: str):
    """
    从数据库中获取匹配特定流派的歌曲。
    参数:
      genre (str): 要获取的歌曲流派。
    返回:
      list[dict]: 匹配指定流派的歌曲列表。
    """
    # 查询 genre_id
    genre_id_query = f"SELECT GenreId From Genre WHERE NAME LIKE '%{genre}%'"
    genre_ids = db.run(genre_id_query)
    if not genre_ids:
        return f"未找到该流派的歌曲：{genre}"
    genre_ids = ast.literal_eval(genre_ids)
    genre_id_list = ", ".join(str(gid[0]) for gid in genre_ids)

    songs_query = f"""
           SELECT Track.Name as SongName, Artist.Name as ArtistName
           FROM Track
           LEFT JOIN Album ON Track.AlbumId = Album.AlbumId
           LEFT JOIN Artist ON Album.ArtistId = Artist.ArtistId
           WHERE Track.GenreId IN ({genre_id_list})
           GROUP BY Artist.Name
           LIMIT 8;
       """
    songs = db.run(songs_query, include_columns=True)
    if not songs:
        return f"未找到该流派的歌曲：{genre}"
    formatted_songs = ast.literal_eval(songs)
    return [
        {"Song": song["SongName"], "Artist": song["ArtistName"]} for song in formatted_songs
    ]


# 检查 歌曲
@tool
def check_for_songs(song_title):
    """根据歌曲名称检查歌曲是否存在"""
    return db.run(f""" SELECT * FROM Track WHERE Name LIKE '%{song_title}%'""", include_columns=True)


# 工具集合
music_tools = [get_albums_by_artist, get_tracks_by_artist, get_song_by_genre, check_for_songs]
llm_with_music_tools = model.bind_tools(music_tools)

# 工具节点
music_tool_node = ToolNode(music_tools)


# 音乐助理提示词
def generate_music_assistant_prompt(memory: str = "None") -> str:
    return f"""
    <important_background>
    你是助理团队的一员，你的具体职责是帮助客户在我们的数字目录中发现和了解音乐。
    如果你找不到与某位艺术家相关的播放列表、歌曲或专辑，这没有关系。
    只需回复目录中没有与该艺术家相关的任何播放列表、歌曲或专辑即可。
    你还掌握了已保存的用户偏好信息，可据此为你的回复量身定制。
    重要提示：你与客户的交互是通过自动化系统完成的。你并非直接与客户对话，因此请避免闲聊或追问，专注于纯粹地用必要信息来响应请求。

    <core_responsibilities>
    - 搜索并提供关于歌曲、专辑、艺术家和播放列表的准确信息
    - 根据客户兴趣提供相关推荐
    - 处理音乐相关查询时注重细节
    - 帮助客户发现他们可能喜欢的新音乐
    - 仅当遇到与音乐目录相关的问题时才会路由到你这里；忽略其他问题。
    </core_responsibilities>

    <guidelines>
    1. 在断定某项内容不存在之前，务必进行彻底的搜索
    2. 如果找不到精确匹配，请尝试：
       - 检查其他拼写方式
       - 查找相似的艺术家名称
       - 按部分匹配进行搜索
       - 检查不同的版本/混音版
    3. 提供歌曲列表时：
       - 每首歌曲都附上艺术家名称
       - 在相关时注明所属专辑
       - 注明它是否属于任何播放列表
       - 标明是否存在多个版本
    </guidelines>

    下面提供了附加上下文：

    已保存的用户偏好：{memory}

    消息历史记录也一并附上。
    """


# 音乐助理
def music_assistant(state: State):
    memory = "None"
    if "loaded_memory" in state:
        memory = state["loaded_memory"]
    # 提示词中加载记忆
    music_assistant_prompt = generate_music_assistant_prompt(memory)
    # 请求大模型
    response = llm_with_music_tools.invoke([SystemMessage(music_assistant_prompt)] + state["messages"])
    return {"messages": [response]}


# edge 临界值
def should_continue(state: State):
    messages = state["messages"]
    last_message = messages[-1]
    if not last_message.tool_calls:
        return "end"
    else:
        return "continue"


# 构建音乐流程
music_workflow = StateGraph(State)

# 添加node
music_workflow.add_node("music_assistant", music_assistant)
music_workflow.add_node("music_tool_node", music_tool_node)

# 添加 edge
music_workflow.add_edge(START, "music_assistant")

#  添加条件 edge
music_workflow.add_conditional_edges("music_assistant", should_continue,
                                     {
                                         "continue": "music_tool_node",
                                         "end": END
                                     })

music_workflow.add_edge("music_tool_node", "music_assistant")

# 编译
music_catalog_subagent = music_workflow.compile(name="music_catalog_subagent", checkpointer=checkpointer,
                                                store=in_memory_store)

question = "我喜欢滚石乐队(The Rolling Stones)。你能推荐一些他们的歌,或者其他我可能会喜欢的艺术家的歌吗?"
config = {"configurable": {"thread_id": uuid7()}}

result = music_catalog_subagent.invoke({"messages": [HumanMessage(content=question)]}, config=config)

for message in result["messages"]:
    message.pretty_print()

print("\n")
print("\n")
print(
    "-------------------------------------------01-1.2-是用LangChain 的create_agent 构建智能体--------------------------------------------------------")
print("\n")


# 获取指定客户的发票(按日期排序
@tool
def get_invoices_by_customer_sorted_by_date(runtime: ToolRuntime) -> list[dict]:
    """
    使用客户 ID 查询该客户的所有发票。客户 ID 存放在状态(state)变量中,因此你不会在消息历史中看到它。
    发票按发票日期降序排列,这在客户想查看最近/最早的发票,或想查看特定日期范围内的发票时很有帮助。
    Returns:
    list[dict]: 该客户的发票列表。
    """
    customer_id = runtime.state.get("customer_id", {})
    return db.run(f"SELECT * FROM Invoice WHERE CustomerId = {customer_id} ORDER BY InvoiceDate DESC;")


# 获取发票(按时间排序)
@tool
def get_invoices_sorted_by_unit_price(runtime: ToolRuntime) -> list[dict]:
    """
     当客户想根据发票的单价(unit price)/费用查询某张发票的详细信息时,使用此工具。
     此工具会查询该客户的所有发票,并按单价从高到低排序。要找到与客户关联的发票,
     我们需要知道客户 ID。客户 ID 存放在状态(state)变量中,因此你不会在消息历史中看到它。

     Returns:
         list[dict]: 按单价排序的发票列表。
     """
    customer_id = runtime.state.get("customer_id", {})
    query = f"""
        SELECT Invoice.*, InvoiceLine.UnitPrice
        FROM Invoice
        JOIN InvoiceLine ON Invoice.InvoiceId = InvoiceLine.InvoiceId
        WHERE Invoice.CustomerId = {customer_id}
        ORDER BY InvoiceLine.UnitPrice DESC;
    """
    return db.run(query)


# 根据发票和客户获取(负责的)员工
@tool
def get_employee_by_invoice_and_customer(runtime: ToolRuntime, invoice_id: int) -> dict:
    """
    此工具接收发票 ID 和客户 ID,返回与该发票关联的员工信息。
    客户 ID 存放在状态(state)变量中,因此你不会在消息历史中看到它。

    Args:
        invoice_id (int): 指定发票的 ID。

    Returns:
        dict: 与该发票关联的员工信息。
    """
    customer_id = runtime.state.get("customer_id", {})
    query = f"""
            SELECT Employee.FirstName, Employee.Title, Employee.Email
            FROM Employee
            JOIN Customer ON Customer.SupportRepId = Employee.EmployeeId
            JOIN Invoice ON Invoice.CustomerId = Customer.CustomerId
            WHERE Invoice.InvoiceId = ({invoice_id}) AND Invoice.CustomerId = ({customer_id});
        """
    employee_info = db.run(query, include_columns=True)

    if not employee_info:
        return f"未找到与发票 ID {invoice_id} 和客户 ID {customer_id} 关联的员工"
    return employee_info


# 工具集合
invoice_tools = [get_invoices_by_customer_sorted_by_date, get_invoices_sorted_by_unit_price,
                 get_employee_by_invoice_and_customer]

# 提示词部分
invoice_subagent_prompt = """
    <important_background>
    你是一支助手团队中的子智能体(subagent)。你专门负责检索和处理发票信息。
    发票包含诸如歌曲购买记录和账单历史等信息。只有当问题以某种方式涉及账单、发票或购买时,才作出回应。
    如果你无法检索到发票信息,请回复说你无法获取该信息。
    重要:你与客户的交互是通过一个自动化系统进行的。你并非直接与客户对话,因此请避免闲聊或追问,只需专注于用必要的信息来回应请求。
    </important_background>

    <tools>
    你可以使用三个工具。这些工具能让你从数据库中检索和处理发票信息。工具如下:
    - get_invoices_by_customer_sorted_by_date:该工具检索某位客户的所有发票,并按发票日期排序。
    - get_invoices_sorted_by_unit_price:该工具检索某位客户的所有发票,并按单价排序。
    - get_employee_by_invoice_and_customer:该工具检索与某张发票和某位客户相关联的员工信息。
    </tools>

   <core_responsibilities>
    - 从数据库中检索和处理发票信息
    - 当客户提出要求时,提供有关发票的详细信息,包括客户详情、发票日期、总金额、与发票关联的员工等。
    - 在回应中始终保持专业、友好和耐心的态度。
    </core_responsibilities>

    你可能会获得一些额外的上下文信息,应当用它来帮助回答客户的查询。该信息将提供在下方:
    """

# 构建子智能体
invoice_information_subagent = create_agent(
    model=model,
    tools=invoice_tools,
    name="invoice_information_subagent",
    system_prompt=invoice_subagent_prompt,
    state_schema=State,
    checkpointer=checkpointer,
    store=in_memory_store
)

question = "我最近的一张发票是什么?当时是哪位员工为我处理的?"
config = {"configurable": {"thread_id": uuid7()}}

# 调用子智能体
result = invoice_information_subagent.invoke({"messages": [HumanMessage(content=question)], "customer_id": 1},
                                             config=config)

print("\n")
print(f"result:{result}")
print("\n")
print("\n")

#  打印结果
for message in result["messages"]:
    message.pretty_print()

print(
    "-------------------------------------------02-构建-多智能体-架构--------------------------------------------------------")

supervisor_prompt = """
  <背景>
  你是一家数字音乐商店的资深客户支持助手。你可以处理与音乐目录相关的问题，
  或与过往购买记录、歌曲或专辑是否有售相关的发票（账单）问题。
  你致力于提供卓越的服务，确保客户的疑问得到全面解答，并且你拥有一支子代理
  （subagent）团队，可以用来协助回答客户的咨询。
  你的主要职责是将任务委派给这个多代理团队，从而解答客户的问题。
  </背景>

  <重要指示>
  回复客户时，务必通过总结各个子代理的回复结果来作答。
  如果问题与音乐或发票无关，请礼貌地提醒客户你的工作范围，不要回答无关的问题。
  根据消息中已经执行过的步骤，你的职责是依据用户的咨询调用合适的子代理。
  </重要指示>

  <工具>
  你有 2 个工具可用于向团队中的子代理委派任务：
  回复客户时，务必通过总结各个子代理的回复结果来作答。
  如果问题与音乐或发票无关，请礼貌地提醒客户你的工作范围，不要回答无关的问题。
  根据消息中已经执行过的步骤，你的职责是依据用户的咨询调用合适的子代理。
  </重要指示>

  <工具>
  你有 2 个工具可用于向团队中的子代理委派任务：
  1. music_catalog_information_subagent（音乐目录信息子代理）：调用此工具可将任务
     委派给音乐子代理。该音乐代理可以访问用户保存的音乐偏好，还能从数据库中检索
     这家数字音乐商店的音乐目录信息（专辑、曲目、歌曲等）。
  2. invoice_information_subagent（发票信息子代理）：调用此工具可将任务委派给发票
     子代理。该子代理能够从数据库中检索客户的历史购买记录或发票信息。
  </工具>
"""


# 调用发票子智能体
@tool(name_or_callable="invoice_information_subagent",
      description="一个能够协助处理所有发票相关查询的智能体。它可以检索关于客户过往购买记录或发票的信息")
def call_invoice_information_subagent(runtime: ToolRuntime, query: str):
    result = invoice_information_subagent.invoke({
        "messages": [HumanMessage(content=query)],
        "customer_id": runtime.state.get("customer_id", {})
    })
    subagent_response = result["messages"][-1].content
    return subagent_response


# 调用音乐子智能体
@tool(name_or_callable="music_catalog_subagent",
      description="一个能够协助处理所有音乐相关查询的智能体。该智能体可以访问用户已保存的音乐偏好。它还能从数据库中检索数字音乐商店的音乐目录信息(专辑、曲目、歌曲等)。")
def call_music_catalog_subagent(query: str):
    result = music_catalog_subagent.invoke({
        "messages": [HumanMessage(content=query)]
    })
    subagent_response = result["messages"][-1].content
    return subagent_response


# 构建超级代理
supervisor = create_agent(
    model=model,
    tools=[call_music_catalog_subagent, call_invoice_information_subagent],
    name="supervisor",
    system_prompt=supervisor_prompt,
    state_schema=State,
    checkpointer=checkpointer,
    store=in_memory_store
)

# question = "我最近一次购买花了多少钱?另外你们有哪些滚石乐队的专辑?";

question = "我最喜欢的水果是什么？";
config = {"configurable": {"thread_id": uuid7()}}

result = supervisor.invoke({
    "messages": [HumanMessage(content=question)],
    "customer_id": 1
}, config=config)

print("\n")
print("\n")

for message in result["messages"]:
    message.pretty_print()

print("\n")
print("\n")
print("\n")

print(
    "-------------------------------------------03-添加用户验证-LOOP---------------------------------------------------------")


# 用户验证环节的结构化输出模式：
# 配合 with_structured_output 使用，让 LLM 从对话历史中提取客户手机号，
# 后续节点用提取到的号码去数据库匹配 customer_id，完成账户验证。
# 注意：docstring 和 Field 的 description 都会作为 schema 说明发送给 LLM，
# 写得越具体，模型提取得越准确。
class PhoneNumberExtraction(BaseModel):
    """从客户消息历史中提取手机号，用于账户身份验证。

    如果客户尚未提供手机号，phone_number 应返回空字符串。
    """
    phone_number: str = Field(description="客户的手机号，纯数字；未提供时为空字符串")


structured_llm = model.with_structured_output(schema=PhoneNumberExtraction)

# 结构化返回，提示词部分
structured_system_prompt = """你是一名客服代表,负责提取客户的电话号码。\n 只从消息历史记录中提取客户的账户信息。如果他们尚未提供该信息,则为该字段返回一个空字符串"""


def verify_info(state: State):
    if state.get("customer_id") is not None:
        return
    else:
        user_input = state["messages"][-1]
        parse_info = structured_llm.invoke([SystemMessage(content=structured_system_prompt)] + [user_input])

        identifier = parse_info.phone_number
        customer_id = ""
        if (identifier):
            query = f"SELECT CustomerId FROM Customer where Phone ='{identifier}'"
            result = db.run(query)
            try:
                formatted_result = ast.literal_eval(result)
                if formatted_result:
                    customer_id = formatted_result[0][0]
            except(ValueError, SyntaxError):
                pass

        if customer_id != "":
            intent_message = AIMessage(content=f"感谢您提供的信息！我已成功验证您的账户，客户 ID 为 {customer_id}")
            return {
                "customer_id": customer_id,
                "messages": [intent_message]
            }
        else:
            system_instructions = """
                        你是一名音乐商店客服智能体，你的首要任务是在客户支持流程的第一步验证客户身份。
                        在客户账户通过验证之前，你不能为其提供任何支持服务。
                        为了验证客户身份，请识别他们提供的电话号码。
                        如果客户尚未提供电话号码，请向他们索要。
                        如果客户已提供电话号码但查不到对应的记录，请让他们核对并修改。

                        重要：在客户身份验证通过之前，不要询问任何与他们的需求相关的问题，也不要尝试处理他们的需求。出于安全考虑，你只能询问身份验证相关的信息，这一点至关重要。
                        """
            response = model.invoke([SystemMessage(content=system_instructions)] + state["messages"])

            return {"messages": [response]}


# 添加用户输入
def human_input(state: State):
    """空操作节点,用于在此处触发中断"""
    user_input = interrupt("请提供输入。")
    return {"messages": [HumanMessage(content=user_input)]}


# 是否需要中断
def should_interrupt(state: State):
    if state.get("customer_id") is not None:
        return "continue"
    else:
        return "interrupt"


# 构建多智能体
multi_agent_verify = StateGraph(State,input_schema=InputState)
multi_agent_verify.add_node("verify_info",verify_info)
multi_agent_verify.add_node("human_input",human_input)
multi_agent_verify.add_node("supervisor",supervisor)


