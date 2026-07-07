import ast
from typing import TypedDict, Annotated, NotRequired

from langchain_community.utilities import SQLDatabase
from langchain_core.messages import AnyMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import add_messages
from langgraph.managed import RemainingSteps
from langgraph.prebuilt import ToolNode
from utils.models import model
from utils.utils import get_engine_for_chinook_db

# 数据库
engine = get_engine_for_chinook_db()
db = SQLDatabase()


class InputState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    loaded_memory: NotRequired[str]


class State(InputState):
    customer_id: NotRequired[str]
    remaining_steps: NotRequired[RemainingSteps]


# 根据艺术家获取专辑
@tool
def get_albums_by_artist(artist: str):
    """根据艺术家获取专辑"""
    return db.run(
        f"""
          SELECT Album.Title, Artist.Name
          FROM Album
          JOIN Artist ON Album.ArtistId = Artist.ArtistId
          WHERE Artist.Name LIKE '%{artist}%';
          """,
        include_columns=True
    )


# 根据艺术家或相似艺术家获取歌曲列
@tool
def get_tracks_by_artist(artist: str):
    """根据艺术家或相似艺术家获取歌曲列"""
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


# 根据流派获取歌曲列
@tool
def get_songs_by_genre(genre: str):
    """
     从数据库中获取匹配特定流派的歌曲。

     Args:
         genre: 要查询的歌曲流派。

     Returns:
         匹配指定流派的歌曲列表，每个元素为一首歌曲的信息。
     """

    genre_id_query = f"SELECT GenreId FROM Genre WHERE Name LIKE '%{genre}%'"
    genre_ids = db.run(genre_id_query)
    if not genre_ids:
        return f"No songs found for the genre: {genre}"
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
        return f"No songs found for the genre: {genre}"
    formatted_songs = ast.literal_eval(songs)
    return [
        {"Song": song["SongName"], "Artist": song["ArtistName"]}
        for song in formatted_songs
    ]


# 检查歌曲是否存在
@tool
def check_for_songs(song_title):
    """根据歌曲名称检查歌曲是否存在"""
    return db.run(
        f"""
        SELECT * FROM Track WHERE Name LIKE '%{song_title}%';
        """,
        include_columns=True
    )


music_tools = [get_albums_by_artist, get_tracks_by_artist, get_songs_by_genre, check_for_songs]

# 绑定工具
llm_with_tools = model.bind_tools(music_tools)

# 创建模型
llm_with_music_tools = model.bind_tools(music_tools)

# 创建工具节点
music_tool_node = ToolNode(music_tools)


# 音乐助手
def music_assistant(state: State):
    memory="None"
    if "load_memory" in state:
        memory = state["loaded_memory"]

    music_assistant_prompt = f"""
          你是助手团队的一员，你的具体角色是帮助客户发现并了解我们数字目录中的音乐。
          如果你无法找到与某位艺术家相关的播放列表、歌曲或专辑，这是可以接受的。
          只需要告知客户：目录中没有与该艺术家相关的播放列表、歌曲或专辑。
          你还可以参考已保存的用户偏好，从而更有针对性地调整你的回复。

          核心职责：
          - 搜索并提供关于歌曲、专辑、艺术家和播放列表的准确信息
          - 根据客户兴趣提供相关推荐
          - 细致处理与音乐相关的查询
          - 帮助客户发现他们可能喜欢的新音乐
          - 只有当问题与音乐目录相关时，你才会被路由调用；请忽略其他问题。

          搜索指南：
          1. 在得出某项内容不可用的结论之前，始终要进行充分搜索
          2. 如果没有找到精确匹配，请尝试：
             - 检查是否存在其他拼写方式
             - 查找相似的艺术家名称
             - 使用部分匹配进行搜索
             - 检查不同版本或混音版本
          3. 提供歌曲列表时：
             - 每首歌都包含艺术家名称
             - 在相关时注明所属专辑
             - 说明它是否属于某个播放列表
             - 如果存在多个版本，也要指出

          以下提供了额外上下文：

          之前保存的用户偏好：{memory}

          消息历史也已附加。
          """
    response=llm_with_music_tools.invoke([SystemMessage(music_assistant_prompt)]+state["messages"])

    return {"messages":[response]}
