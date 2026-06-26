import sys
import tempfile
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend, CompositeBackend, StateBackend
import tempfile
import os
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langsmith import uuid7
from numpy.testing.print_coercion_tables import print_new_cast_table
from tavily import TavilyClient

# 将 notebooks 目录加入 sys.path，以便脚本方式运行时能 import utils.*
# 注意：必须用 Path(__file__) 而非 Path()，后者取当前工作目录，
# 在 PyCharm/调试器中并不固定，会导致 utils.models 无法导入
project_root = Path(__file__).resolve().parent.parent

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.models import model

from dotenv import load_dotenv

load_dotenv(dotenv_path="../../.env", override=True)

import warnings

warnings.filterwarnings('ignore', message='LangSmith now uses UUID v7')

print(
    "-------------------------------------------01-Harness-------------------------------------------------------")

print("\n")
agent = create_deep_agent(
    model=model,
    system_prompt="你是一名乐于助人的研究助理。在引用文件路径时，请使用反引号格式（如 path/file.md），而不要使用 Markdown 链接,回答一律用中文"
)
print("深入研究Agent创建成功")

# result = agent.invoke({
#     "messages": [
#         {"role": "user",
#          "content": "创建一个名为 notes.md 的文件，写入文本 'Hello from Deep Agents!'，然后读取该文件以确认内容"}
#     ]
# })

# print("结果为:", result["messages"][-1].content)
# print("\n")
# print("\n" + "=" * 50)
# print("📁 虚拟文件系统（在内存中，不在磁盘上！）")
# print("\n" + "=" * 50)

# for path, file_data in result.get("files", {}).items():
#     print(f"\n Path:'{path}'")
#     print(" " + "-" * 30)
#
#     if isinstance(file_data, dict) and "content" in file_data:
#         content = "\n".join(file_data["content"])
#         for line in content.split("\n"):
#             print(f" |{line}")
#     else:
#         print(f" |{file_data}")

print(
    "-------------------------------------------02-自定义工具-------------------------------------------------------")

# 初始化 TavilyClient 搜索
tavily_client = TavilyClient()


# 搜索工具
@tool(parse_docstring=True)
def tavily_search(query: str) -> str:
    """在网络上搜索给定查询的相关信息。

    Args:
        query: 要执行的搜索查询（search query）。
    """
    search_results = tavily_client.search(query, max_results=3, topic="general")
    result_texts = []

    for result in search_results.get("results", []):
        url = result.get("url")
        title = result.get("title")
        content = result.get("content", "No content available")
        result_text = f"##{title}\n **URL:**{url}\n\n{content}\n\n---\n"
        result_texts.append(result_text)
    return f"Found{len(result_texts)} result(s) for 'query':\n\n{''.join(result_texts)}"


# 创建 Agent
# agent = create_deep_agent(
#     model=model,
#     tools=[tavily_search],
#     system_prompt="""你是一名乐于助人的研究助理,使用 tavily_search 在网络上查找信息,
#      引用文件路径时，请使用反引号格式（如 `path/file.md`），而不要使用 Markdown 链接,必须用中文回答。
#      """
# )
# print("\n")
# print("搜索工具创建成功")


# result = agent.invoke(
#     {
#         "messages": [
#             {
#                 "role": "user",
#                 "content": "搜索一下2026世界杯梅西与阿根廷，并总结一下"
#             }
#         ]
#     }
# )

# print("结果为:", result["messages"][-1].content)


print(
    "-------------------------------------------03-Backends-------------------------------------------------------")

# 状态存储(stateBackends)
checkpointer = MemorySaver()
# agent = create_deep_agent(
#     model=model,
#     tools=[tavily_search],
#     system_prompt="""你作为一名乐于助人的研究助理,使用 tavily_search 在网络上查找信息,
#       引用文件路径时，请使用反引号格式（如 `path/file.md`），而不要使用 Markdown 链接,必须用中文回答。
#       """,
#     checkpointer=checkpointer
# )
#
# thread_id = str(uuid7())
# config = {"configurable": {"thread_id": thread_id}}
#
# # 写的结果,利用状态存储
# result = agent.invoke(
#     {
#         "messages": [
#             {
#                 "role": "user",
#                 "content": "创建一个名为 /research_notes.md 的文件，内容为「My research findings go here」（我的研究成果记录于此）"
#             }
#         ]
#     },
#     config=config
# )
#
# print("文件状态:", list(result.get("files", {}).keys()))
# print("\n")
#
# # 读的结果,利用状态存储
# result = agent.invoke(
#     {
#         "messages": [
#             {
#                 "role": "user",
#                 "content": "Read the file `/research_notes.md`"
#             }
#         ]
#     },
#     config=config
# )
# print("结果为:", result["messages"][-1].content)

# new_config = {"configurable": {"thread_id": uuid7()}};
#
# result = agent.invoke(
#     {
#         "messages": [
#             {
#                 "role": "user",
#                 "content": "List all files with ls /"
#             }
#         ]
#     }
#     , config=new_config
# )
# print("\n")
# print("所有文件结果为:", result["messages"][-1].content)
# print("\n")

#### 文件系统
print("\n")
sandbox_dir = tempfile.mktemp(prefix="deepagents_sandbox_")
print(f"沙盒目录:`{sandbox_dir}`")

# 创建文件系统存储
# fs_backend = FilesystemBackend(root_dir=sandbox_dir, virtual_mode=True)
#
# agent = create_deep_agent(
#     model=model,
#     tools=[tavily_search],
#     system_prompt="""你作为一名乐于助人的研究助理,使用 tavily_search 在网络上查找信息,
#       引用文件路径时，请使用反引号格式（如 `path/file.md`），而不要使用 Markdown 链接,必须用中文回答。
#       """,
#     backend=fs_backend
# )
#
# config = {"configurable": {"thread_id": uuid7()}}
#
# result = agent.invoke(
#     {
#         "messages": [
#             {
#                 "role": "user",
#                 "content": "创建一个名为 notes.txt 的文件，内容为 'Hello from FilesystemBackend!'"
#             }
#         ]
#     },
#     config=config
# )
# print("\n")
# print("文件系统的结果为:", result["messages"][-1].content)
# print("\n")
#
# actual_path = os.path.join(sandbox_dir, "notes.txt")
#
# if os.path.exists(actual_path):
#     with open(actual_path, "r") as f:
#         print(f"\n✅ 文件已存在于盘，路径: `{actual_path}`")
#         print(f"   Content: {f.read()}")
# else:
#     print(f"\n❌ 文件找不到 at: {actual_path}")
#
# print("\n")
# print(f"文件在沙盒({sandbox_dir}):")
# print("\n")
#
# for f in os.listdir(sandbox_dir):
#     print(f" - {f}")

print("\n")
print("\n")

# 组合式
# 工作目录
workspace_dir = tempfile.mktemp(prefix="deepagents_workspace_")
print(f"工作目录:`{workspace_dir}`")

# 创建组合式存储
composite_backend = CompositeBackend(
    default=StateBackend,
    routes={
        "/workspace/": FilesystemBackend(root_dir=workspace_dir, virtual_mode=True),
    }
)

agent_composite = create_deep_agent(
    model=model,
    system_prompt="""你是一个有帮助的助手。                                                                                                                                                               

    存储规则：                                                                                                                                                                                            
    - `/workspace/*` 下的文件会保存到真实磁盘（持久化）                                                                                                                                                   
    - 其他所有文件都是临时的（线程结束时会消失）                                                                                                                                                          

    引用文件路径时，请使用反引号格式，如 `path/file.md`，而不是 Markdown 链接。                                                                                                                           
    """,
    backend=composite_backend,
    checkpointer=checkpointer
)

config = {"configurable": {"thread_id": uuid7()}}

result = agent_composite.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content":""
            }
        ]
    },
    config=config
)
