import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import final

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend, CompositeBackend, StateBackend, StoreBackend
import tempfile
import shutil
import os

from deepagents.backends.utils import create_file_data
from langchain.agents.middleware import wrap_tool_call
from langchain_community.agent_toolkits.openapi.planner_prompt import API_CONTROLLER_TOOL_NAME
from langchain_community.tools import EdenAiTextModerationTool
from langgraph.store.memory import InMemoryStore
from langchain_core.tools import tool
from langgraph.types import Command

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
    "critical_operation": {"allowed_decisions": ["approve"]}
}

# 创建 agent
# agent_with_hitl = create_deep_agent(
#     model=model,
#     tools=[tavily_search],
#     system_prompt="你是一个乐于助人的研究助手。在引用文件路径时，请使用反引号格式，如 `path/file.md`，而不是 Markdown 链接,所有的回答必须使用中文",
#     subagents=[research_subagent],
#     checkpointer=MemorySaver(),
#     interrupt_on={
#         "write_file": True,
#         "edit_file": True,
#     }
# )

# config = {"configurable": {"thread_id": uuid7()}}


# result = agent_with_hitl.invoke(
#     {
#         "messages": [
#             {
#                 "role": "user",
#                 "content": "写入一个名为 /test.md 的文件，内容为 'Hello World'"
#             }
#         ]
#     },
#     config=config
# )


# if result.get("__interrupt__"):
#     print("🛑 中断已触发！\n")
#     interrupt_value = result["__interrupt__"][0].value
#     action_requests = interrupt_value["action_requests"]
#     review_configs = interrupt_value["review_configs"]
#
#     for action,review in zip(action_requests,review_configs):
#         print(f"  工具:{action['name']}")
#         print(f"  工具参数:{action['args']}")
#         print(f"  允许的决策:{review['allowed_decisions']}")
#
# else:
#    print("没有触发中断！")
#    print(result["messages"][-1].content)


# print("\n")
# if result.get("__interrupt__"):
#     result=agent_with_hitl.invoke(
#         Command(resume={"decisions": [{"type": "approve"}]}),
#         config=config
#     )
#     print("✅ 已获批准，继续执行！")
#     print(result["messages"][-1].content)


print("\n")
print(
    "-------------------------------------------07-Long-term-Memory------------------------------------------------------")
print("\n")

# store = InMemoryStore()
# # 组合式后端
# composite_backend = CompositeBackend(
#     default=StateBackend(),
#     routes={
#         "/memories/": StoreBackend()
#     }
# )
# print("组合式后端已经创建")
#
# agent_with_memory = create_deep_agent(
#     model=model,
#     tools=[tavily_search],
#     system_prompt="""你是一个具备长期记忆能力的研究助手。
#      重要：请把重要的笔记保存到 /memories/ 目录下，以便它们能在多次对话之间持久保留。
#      例如：/memories/research_notes.md
#      不在 /memories/ 目录下的普通文件会在对话结束后消失。
#      当被问到你记得什么或知道什么时，务必先用 ls 和 read_file 查看 /memories/ 目录。
#      不要只依赖当前对话的上下文——记忆会跨线程（thread）持久保留，但对话内容不会。
#      在引用文件路径时，请使用反引号格式（如 `path/file.md`），而不要使用 Markdown 链接。
#      所有的回答必须使用中文回答
#      """,
#     subagents=[research_subagent],
#     backend=composite_backend,
#     store=store,
#     checkpointer=checkpointer
# )
# print("\n")
# print("长期记忆Agent已经创建")
# print("\n")
#
# thread1_config = {"configurable": {"thread_id": uuid7()}}
#
# result = agent_with_memory.invoke(
#     {
#         "messages": [
#             {
#                 "role": "user",
#                 "content": "把重要研究发现「AI agent（智能体）正在快速演进」保存到 /memories/findings.md"
#             }
#         ]
#     },
#     config=thread1_config
# )
# print("线程1:回答结果:\n")
# print(result["messages"][-1].content)
# print("\n")
#
# thread2_config = {"configurable": {"thread_id": uuid7()}}
#
# result = agent_with_memory.invoke({
#     "messages": [
#         {
#             "role": "user",
#             "content": "请查看 /memories/findings.md"
#         }
#     ]
# }, config=thread2_config)
#
# print("线程2:回答结果:\n")
# print(result["messages"][-1].content)
# print("\n")
#
# memory_store = InMemoryStore()
#
# # 创建组合式后端
# advanced_composite_backend = CompositeBackend(
#     default=StateBackend(),
#     routes={
#         "/memories/semantic/": StoreBackend(namespace=lambda rt: ("memories", "semantic")),
#         "/memories/episodic/": StoreBackend(namespace=lambda rt: ("memories", "episodic")),
#         "/memories/procedural/": StoreBackend(namespace=lambda rt: ("memories", "procedural")),
#     }
# )
# print("\n")
# print("已创建高级组合式后端，包含 3 种记忆类型的路由！")
#
# memory_agent = create_deep_agent(
#     model=model,
#     tools=[tavily_search],
#     system_prompt="""你是一个具备结构化长期记忆的智能助手。
#
#     你的记忆分为三种类型：
#     - /memories/semantic/   -> 事实与知识（用户偏好、项目详情）
#     - /memories/episodic/   -> 过往经历（会话日志、交互摘要）
#     - /memories/procedural/ -> 指令与规则（如何撰写报告、编码规范）
#
#     当被要求记住某件事时，将其保存到对应的记忆类型中。
#     普通文件（不在 /memories/ 目录下）是临时的，会话结束后即消失。
#
#     当被问及你记得什么或了解用户的哪些信息时，务必先使用 ls 和 read_file
#     检查记忆目录，不要仅依赖对话上下文。
#
#     引用文件路径时，请使用反引号格式，如 `path/file.md`，而不是 markdown 链接。
#     """,
#     subagents=[research_subagent],
#     backend=advanced_composite_backend,
#     store=memory_store,
#     checkpointer=checkpointer
# )
#
# config_t1 = {"configurable": {"thread_id": uuid7()}}
#
# result = memory_agent.invoke(
#     {
#         "messages": [
#             {
#                 "role": "user",
#                 "content": """请将以下内容保存到相应的记忆类型中：
#   1. 我更喜欢 Python 而非 JavaScript（这是关于我的一个事实）
#   2. 在上一次会话中，我们研究了 LangGraph 并发现它很有用（这是一段过往经历）
#   3. 在研究报告中始终使用行内引用标注 [1]、[2]（这是一条规则）"""
#             }
#         ]
#     },
#     config=config_t1
# )
# print("\n")
# print(result["messages"][-1].content)
# print("\n")
#
# config_t2 = {"configurable": {"thread_id": uuid7()}}
# result = memory_agent.invoke(
#     {
#         "messages": [
#             {
#                 "role": "user",
#                 "content": "我来查看记忆库，看看关于你的记录"
#             }
#         ]
#     },
#     config=config_t2
# )
# print("\n")
# print(result["messages"][-1].content)
# print("\n")
# print("\n")
#
# scoped_store = InMemoryStore()
#
# # 创建范围组合式后端
# scoped_backend = CompositeBackend(
#     default=StateBackend(),
#     routes={
#         "/memories/user/": StoreBackend(
#             namespace=lambda rt: ("user", getattr(rt.context, "user_id", "default"), "filesystem")),
#         "/memories/shared/": StoreBackend(namespace=lambda rt: ("shared", "filesystem")),
#
#     }
# )
#
# scoped_agent = create_deep_agent(
#     model=model,
#     tools=[tavily_search],
#     system_prompt="""你是一个具有分级记忆（scoped memory）能力的助手。
#
#     记忆作用域（MEMORY SCOPES）：
#     - /memories/user/    -> 当前用户私有（仅该用户可见）
#     - /memories/shared/  -> 全体用户共享（所有人可见）
#
#     请把个人偏好保存到 /memories/user/，把团队规范保存到 /memories/shared/。
#
#     当被问到你记得哪些内容时，务必先使用 ls 和 read_file 检查记忆目录。
#
#     引用文件路径时，请使用反引号格式，例如 `path/file.md`，而不要使用 markdown 链接。
#     所有的回答必须是中文
#     """,
#     checkpointer=checkpointer,
#     backend=scoped_backend,
#     store=scoped_store
# )
# print("\n")
# print("分级智能体创建成功：支持用户私有记忆与共享记忆！")
# print("\n")
#
# config_alice = {"configurable": {"thread_id": uuid7(), "user_id": "alice"}}
#
# result = scoped_agent.invoke(
#     {
#         "messages": [
#             {
#                 "role": "user",
#                 "content": """把这两条内容保存下来：
#   1. 保存到我的私有记忆（/memories/user/）：「Alice 偏好深色模式和 Python」
#   2. 保存到共享记忆（/memories/shared/）：「团队规范：始终编写单元测试」"""
#             }
#         ]
#     }, config=config_alice
# )
#
# print("\n")
# print("Alice 画像:", result["messages"][-1].content)
# print("\n")
#
# config_bob = {"configurable": {"thread_id": uuid7(), "user_id": "bob"}}
# result = scoped_agent.invoke(
#     {
#         "messages": [
#             {
#                 "role": "user",
#                 "content": "列出 /memories/user/ 和 /memories/shared/ 目录下的所有文件，以查看你可以访问的内容"
#             }
#         ]
#     }, config=config_bob
# )
# print("\n")
# print("Bob sees:\n", result["messages"][-1].content)
# print("\n" + "=" * 50)
# print("Bob 可以看到共享的指导规范，但看不到 Alice 的私有偏好设置！")


print("\n")
print(
    "-------------------------------------------08-Agent.md&Skills------------------------------------------------------")
print("\n")

agents_md_content = """# 研究助理                                                                                                                                                                       

  你是一名专业的研究助理，能够搜索网络、综合分析研究结果，并产出精良的报告与内容。                                                                                                                        

  ## 工作流程                                                                                                                                                                                             

  1. **规划（Plan）** —— 使用 `write_todos` 将任务拆解为若干步骤                                                                                                                                          
  2. **研究（Research）** —— 使用 tavily_search 搜索信息                                                                                                                                                  
  3. **反思（Reflect）** —— 每次搜索后进行反思，分析研究结果                                                                                                                                              
  4. **综合（Synthesize）** —— 将研究结果整合成一份完整的报告                                                                                                                                             
  5. **撰写（Write）** —— 将最终报告保存到 `/final_report.md`                                                                                                                                             
  6. **记录（Remember）** —— 将关键要点保存到 `/memories/research_notes.md`                                                                                                                               

  ## 规则                                                                                                                                                                                                 

  - 最多使用 2-3 次搜索                                                                                                                                                                                   
  - 合并引用来源 —— 每个唯一 URL 只分配一个编号 [1]、[2]、[3]                                                                                                                                             
  - 报告结尾附上「来源（Sources）」章节                                                                                                                                                                   
  - 当被要求创建特定内容格式时，检查是否有可用的相关技能（skill）                                                                                                                                         
  """
print("Agent.md 已经创建完成")
print("\n")

# 领英 skill md
linkedin_skill_content = """
 ---                                                                                                                                                                                                     
  name: linkedin-post                                                                                                                                                                                     
  description: 基于调研结果或给定主题撰写 LinkedIn 帖子。当被要求创作 LinkedIn 内容、专业帖子或思想领导力文章时使用此技能。                                                                               
  ---                                                                                                                                                                                                     
                                                                                                                                                                                                          
  # LinkedIn 帖子技能                                                                                                                                                                                     
                                                                                                                                                                                                          
  ## 格式                                                                                                                                                                                                 
  - **钩子（Hook）**：以一句醒目的开场白抓住注意力（显示在「查看更多」折叠之前）                                                                                                                          
  - **正文**：3-5 个短段落，每段 1-2 句话                                                                                                                                                                 
  - 段落之间使用换行以提升可读性                                                                                                                                                                          
  - 每段包含 1-2 个相关的表情符号（不要过度使用）                                                                                                                                                         
  - 以行动号召（call-to-action）或提问结尾，以带动互动                                                                                                                                                    
  - 在底部添加 3-5 个相关的话题标签（hashtag）                                                                                                                                                            
                                                                                                                                                                                                          
  ## 语气                                                                                                                                                                                                 
  - 专业但不失口语化                                                                                                                                                                                      
  - 分享洞见，而非仅仅罗列信息                                                                                                                                                                            
  - 在适当的地方使用「我」的表述和个人视角                                                                                                                                                                
                                                                                                                                                                                                          
  ## 篇幅                                                                                                                                                                                                 
  - 理想长度：150-300 字                                                                                                                                                                                  
  - LinkedIn 会在约 210 个字符后截断，因此第一行必须钩住读者
"""
print("\n")
print("领英帖子技能已定义！\n")
print(f"技能名称：linkedin-post\n")
print(f"长度: {len(linkedin_skill_content)} chars")
print("\n")

# twitter skill md
twitter_skill_content = """
  ---                                                                                                                                                                                                     
  name: twitter-post                                                                                                                                                                                      
  description: 基于研究发现或给定主题撰写 Twitter/X 帖子或推文串（thread）。当被要求创作推文、X 帖子或社交媒体推文串时使用此技能。                                                                        
  ---                                                                                                                                                                                                     
                                                                                                                                                                                                          
  # Twitter/X 帖子技能                                                                                                                                                                                    
                                                                                                                                                                                                          
  ## 单条推文格式                                                                                                                                                                                         
  - 最多 280 个字符                                                                                                                                                                                       
  - 用最有吸引力的观点开头                                                                                                                                                                                
  - 尽可能使用数字或数据                                                                                                                                                                                  
  - 最多 1-2 个话题标签（hashtag）（可选）                                                                                                                                                                
                                                                                                                                                                                                          
  ## 推文串格式（适用于较长内容）                                                                                                                                                                         
  - 第 1 条推文：钩子 + 预告（例如："关于 X 的推文串："）                                                                                                                                                 
  - 第 2 到 N 条推文：每条一个观点，编号（1/、2/、3/）                                                                                                                                                    
  - 最后一条推文：总结 + 行动号召（call-to-action）                                                                                                                                                       
  - 4-8 条推文是最佳数量                                                                                                                                                                                  
                                                                                                                                                                                                          
  ## 语气                                                                                                                                                                                                 
  - 简洁有力                                                                                                                                                                                              
  - 有鲜明观点的表达比中立的总结表现更好                                                                                                                                                                  
  - 使用通俗易懂的语言——不要用官腔套话                                                                                                                                                                    
"""
print("\n")
print("Twitter/X 帖子技能已定义！\n")
print(f"技能名称：twitter-post\n")
print("\n")

store = InMemoryStore()
# agent 创建
skill_agent = create_deep_agent(
    model=model,
    system_prompt="""你是一名专业的研究助理,所有的回答必须是中文""",
    tools=[tavily_search],
    memory=["/AGENTS.md"],
    skills=["/skills/"],
    checkpointer=checkpointer,
    backend=composite_backend,
    store=store,
)

# skill 与agent 绑定
skill_files = {
    "/AGENT.md": create_file_data(agents_md_content),
    "/skills/linkedin-post/SKILL.md": create_file_data(linkedin_skill_content),
    "/skills/twitter-post/SKILL.md": create_file_data(twitter_skill_content),
}
print("\n")
print("已创建 Agent，包含 AGENTS.md + 2 个 skill！\n")
print(f"  记忆：`/AGENTS.md`（始终加载）\n")
print(f"  Skills：linkedin-post、twitter-post（按需加载）\n")
print("\n")
config = {"configurable": {"thread_id": uuid7()}}

result = skill_agent.invoke({
    "messages":
        [
            {
                "role": "user",
                "content": "研究一下什么是 AI 智能体（AI agents），然后就你的发现写一篇 LinkedIn 帖子"
            }
        ]
    ,
    "files": skill_files,

}, config=config)

print("\n")
print(result["messages"][-1].content)
print("\n")

config = {"configurable": {"thread_id": uuid7()}}

result = skill_agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "现在就同一主题写一个 Twitter/X 推文串（thread）"
            }
        ]
    },
    config=config
)
print("\n")
print(result["messages"][-1].content)
print("\n")

print("\n")
print(
    "-------------------------------------------09-complete research Agent------------------------------------------------------")
print("\n")

final_agent = create_deep_agent(
    model=model,
    tools=[tavily_search],
    system_prompt="""你是一名专业的研究助理,所有的回答必须是中文""",
    memory=["/AGENTS.md"],
    skills=["/skills/"],
    checkpointer=checkpointer,
    backend=composite_backend,
    store=store,
)

final_agent_files = {
    "/AGENTS.md": create_file_data(agents_md_content),
    "/skills/linkedin-post/SKILL.md": create_file_data(linkedin_skill_content),
    "/skills/twitter-post/SKILL.md": create_file_data(twitter_skill_content),
}
print("\n")
print("最终研究 Agent 已创建，包含 AGENTS.md + skills！")
