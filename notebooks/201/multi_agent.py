import sys
from pathlib import Path

import sqlite3
from typing import TypedDict, Annotated, List

import requests
from langchain_core.messages import AnyMessage
from langchain_core.stores import InMemoryStore
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import add_messages
from sqlalchemy import create_engine, StaticPool
from langchain_community.utilities.sql_database import SQLDatabase

project_root = Path().resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.models import model


# 获取数据库连接
def get_engine_for_chinook_db():
    """拉取 SQL 文件，填充内存数据库，并创建引擎。"""
    url = "https://raw.githubusercontent.com/lerocha/chinook-database/master/ChinookDatabase/DataSources/Chinook_Sqlite.sql"
    response = requests.get(url)
    sql_script = response.text

    connection = sqlite3.connect(":memory", check_same_thread=False)
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
