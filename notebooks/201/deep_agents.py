import sys
import tempfile
from datetime import datetime
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend, CompositeBackend, StateBackend, StoreBackend
import tempfile
import shutil
import os

from langchain.agents.middleware import wrap_tool_call
from langchain_community.tools import EdenAiTextModerationTool
from langchain_core.stores import InMemoryStore
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langsmith import uuid7
from numpy.testing.print_coercion_tables import print_new_cast_table
from openevals import create_async_trajectory_match_evaluator
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
api_key = os.getenv("TAVILY_API_KEY")
if not api_key:
    raise RuntimeError(
        "未检测到 TAVILY_API_KEY，请在 .env 中配置后再运行；"
        "否则会进入 keyless 匿名模式并很快被限流。"
    )
tavily_client = TavilyClient(api_key)


# 搜索工具
@tool(parse_docstring=True)
def tavily_search(query: str) -> str:
    """在网络上搜索给定查询的相关信息。

    Args:
        query: 要执行的搜索查询（search query）。
    """
    search_results = tavily_client.search(
        query, max_results=3, topic="general", search_depth="basic"
    )
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
    default=StateBackend(),
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

    引用文件路径时，请使用反引号格式，如 `path/file.md`，而不是 Markdown 链接,必须用中文回答。                                                                                                                          
    """,
    backend=composite_backend,
    checkpointer=checkpointer
)

config = {"configurable": {"thread_id": uuid7()}}

# result = agent_composite.invoke(
#     {
#         "messages": [
#             {
#                 "role": "user",
#                 "content":"""写入两个文件：
#   1. /workspace/persistent.txt，内容为「I will survive!」（我会活下来！）
#   2. /scratch.txt，内容为「I am ephemeral」（我是临时的）
# 然后列出这两个文件的位置。"""
#             }
#         ]
#     },
#     config=config
# )
# print("\n")
# print("返回的结果:",result["messages"][-1].content)
# print("\n")

# for path,data in result.get("files",{}).items():
#     if isinstance(data,dict) and "content" in data:
#         content="\n".join(data["content"])
#     else:
#         content=str(data)
#     print(f" `{path}`:{content}")

print("\n")
print("\n")

### StoreBackend

agent = create_deep_agent(
    backend=CompositeBackend(
        default=StateBackend(),
        routes={
            "/memories/": StoreBackend(),
        }
    ),
    store=InMemoryStore()
)

shutil.rmtree(sandbox_dir, ignore_errors=True)
shutil.rmtree(workspace_dir, ignore_errors=True)
print("✅ 临临时目录已清")
print("\n")
print(
    "-------------------------------------------04-子 Agent-------------------------------------------------------")

current_date = datetime.now().strftime("%Y-%m-%d")

# 提示词
RESEARCHER_INSTRUCTIONS = f"""你是一名负责开展研究的研究助理。今天的日期是 {current_date}。

 <任务>
 使用工具收集与研究主题相关的信息。
 </任务>

 <硬性限制>
 - 简单查询：最多使用 2-3 次搜索工具调用
 - 复杂查询：最多使用 5 次搜索工具调用
 </硬性限制>

 <输出格式>
 请按以下结构组织你的发现：
 - 清晰的标题
 - 行内引用 [1]、[2]、[3]
 - 末尾附上来源部分
 </输出格式>

 引用文件路径时，请使用反引号格式，例如 `path/file.md`，不要使用 Markdown 链接。
 """

# 子代理
research_subagent = {
    "name": "research_subagent",
    "description": "委派研究任务。一次只给一个主题",
    "system_prompt": RESEARCHER_INSTRUCTIONS,
    "tools": [tavily_search],
}

print("\n")
print("搜索子代理")
print("\n")
print(f"名称:{research_subagent['name']}")
print("\n")
print(f"  工具: {[t.name for t in research_subagent['tools']]}")
print("\n")

ORCHESTRATOR_INSTRUCTIONS = """你是一名研究协调员（research coordinator）                                                                                                                                                           
 当被要求研究某个主题时：                                                                                                                                                                                                               
 1. 使用 write_todos 来规划你的研究任务                                                                                                                                                                                                 
 2. 通过 task() 工具将研究任务委派给 research-agent 子代理（subagent）                                                                                                                                                                  
 3. 切勿直接搜索——始终委派给 research-agent                                                                                                                                                                                             
 4. 综合研究发现，并将报告写入 /final_report.md                                                                                                                                                                                         
 research-agent 将处理所有的网络搜索（web search），并返回汇总后的研究发现。                                                                                                                                                            
 在引用文件路径时，请使用反引号格式，如 `path/file.md`，而不是 markdown 链接。                                                                                                                                                          
 """

# 协调代理创建
agent = create_deep_agent(
    model=model,
    tools=[tavily_search],
    system_prompt=ORCHESTRATOR_INSTRUCTIONS,
    subagents=[research_subagent],
    checkpointer=checkpointer,
)
#
# print("\n")
# print("Agent 已经创建了")
#
# config={"configurable":{"thread_id":uuid7()}}


# result= agent.invoke(
#     {
#         "messages":[
#             {
#                 "role":"user",
#                 "content":"轻度研究本周关于 AI 智能体（AI agents）的有趣新闻"
#             }
#         ]
#     }
#     ,config=config
# )
# print("\n")
# print(result["messages"][-1].content[:2000] + "...")

print("\n")
print("\n")

print(
    "-------------------------------------------05-MiddleWare-------------------------------------------------------")

config = {"configurable": {"thread_id": uuid7()}}


# result = agent.invoke(
#     {
#         "messages": [
#             {
#                 "role": "user",
#                 "content": "我来用任务列表创建一个调研机器学习框架的计划"
#             }
#         ]
#     },
#     config=config
# )
#
# print("\n")
# print(result["messages"][-1].content)

# if "todos" in result:
#     print("Agent Todo List:\n")
#     for todo in result["todos"]:
#         status_map = {"completed": "✅", "in_progress": "🔄", "pending": "⬚"}
#         status = todo.get("status", "pending")
#         icon = status_map.get(status, "⬚")
#         content = todo.get("content", str(todo))
#         print(f"{icon} {content}")
# else:
#     print("状态中没有 todos（智能体可能使用了其他方式）")


# 工具调用
@wrap_tool_call
def log_tool_calls(request, handler):
    """记录智能体的每一次工具调用"""
    tool_name = request.tool_call["name"]
    tool_args = request.tool_call["args"]
    print(f"[TOOL CALL] {tool_name}")
    print(f"[TOOL ARGS] {tool_args}")

    result = handler(request)
    print(f"✅ [Tool Done] {tool_name}\n")
    return result


# agent_with_loggin = create_deep_agent(
#     model=model,
#     tools=[tavily_search],
#     system_prompt="你是一个有用的研究助手。在引用文件路径时，请使用反引号格式，如 path/file.md，而不是 markdown 链接。回答必须用中文回答",
#     middleware=[log_tool_calls],
#     checkpointer=MemorySaver()
# )

# config = {"configurable": {"thread_id": uuid7()}}

# result = agent_with_loggin.invoke({
#
#     "messages": [
#         {
#             "role": "user",
#             "content": "什么是 LangGraph？请在你的文件系统中创建一份简短的总结"
#         }
#     ]
# }, config=config)
# print("\n")
# print("\n--- Agent Response ---")
# print(result["messages"][-1].content)
# print("\n")

print("\n")
print(
    "-------------------------------------------06-Human-in-the-Loop-------------------------------------------------------")
print("\n")

# 创建一个中断点
interrupt_on = {
    "delete_file": {"allowed_decisions": ["approve", "edit", "reject"]},
    "write_file": {"allowed_decisions": ["approve", "reject"]},
    "critical_operation": {"allowed_decision": ["approve"]}
}

# 创建 agent
agent_with_hitl = create_deep_agent(
    model=model,
    tools=[tavily_search],
    system_prompt="你是一个乐于助人的研究助手。在引用文件路径时，请使用反引号格式，如 `path/file.md`，而不是 Markdown 链接,所有的回答必须使用中文",
    subagents=[research_subagent],
    checkpointer=MemorySaver(),
    interrupt_on={
        "write_file": True,
        "edit_file": True,
    }
)

config = {"configurable": {"thread_id": uuid7()}}



result = agent_with_hitl.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "写入一个名为 /test.md 的文件，内容为 'Hello World'"
            }
        ]
    },
    config=config
)


if result.get("__interrupt__"):
    print("🛑 中断已触发！\n")
    interrupt_value = result["__interrupt__"][0].value
    action_requests = interrupt_value["action_requests"]
    review_configs = interrupt_value["review_configs"]

    for action,review in zip(action_requests,review_configs):
        print(f"  工具:{action['name']}")
        print(f"  工具参数:{action['args']}")
        print(f"  允许的决策:{review['allowed_decisions']}")

else:
   print("没有触发中断！")
   print(result["messages"][-1].content)





