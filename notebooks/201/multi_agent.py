import  sys
from pathlib import Path

import  sqlite3
import  requests
from sqlalchemy import create_engine, StaticPool
from langchain_community.utilities.sql_database import SQLDatabase

project_root =Path().resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.models import model



# 获取数据库连接
def get_engine_for_chinook_db():
    """拉取 SQL 文件，填充内存数据库，并创建引擎。"""
    url = "https://raw.githubusercontent.com/lerocha/chinook-database/master/ChinookDatabase/DataSources/Chinook_Sqlite.sql"
    response =  requests.get(url)
    sql_script = response.text

    connection = sqlite3.connect(":memory",check_same_thread=False)
    connection.executescript(sql_script)

    return create_engine(
        "sqlite://",
        creator=lambda:connection,
        poolclass=StaticPool,
        connect_args={"check_same_thread":False}
    )

engine = get_engine_for_chinook_db()
db = SQLDatabase(engine)

