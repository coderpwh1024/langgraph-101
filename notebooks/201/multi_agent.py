import ast
import sys
from pathlib import Path

import sqlite3
from typing import TypedDict, Annotated, List

import requests
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage
from langchain_core.stores import InMemoryStore
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import START, END
from langgraph.graph import add_messages, StateGraph
from langgraph.prebuilt import ToolNode, ToolRuntime
from langsmith import uuid7
from sqlalchemy import create_engine, StaticPool
from langchain_community.utilities.sql_database import SQLDatabase

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


print(
    "-------------------------------------------01-1.2-是用LangChain 的create_agent 构建智能体--------------------------------------------------------")










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
