import sys
from pathlib import Path

from langsmith import Client, uuid7
from multi_agent import multi_agent_verify_graph, config
from langgraph.types import Command
# multi_agent.py 内部用 `from notebooks.utils.utils import show_graph`，
# 需要项目根目录（含 notebooks/ 的目录）在 sys.path 上
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# multi_agent.py 与本文件同目录（notebooks/201/），目录名以数字开头不是合法包名，
# 无法用点式 import，这里将该目录加入 sys.path 后按模块名直接 import
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# 注意：import multi_agent 会执行其模块顶层的演示代码（含 invoke、联网建库），
# multi_agent_verify_graph 即在该模块中编译得到

client = Client()

examples = [
    {
        "question": "我叫 Aaron Mitchell。账户 ID 是 32。我账户关联的电话号码是 +1 (204) 452-6452。我想查一下我最近一次歌曲购买的发票编号，你能帮我查一下吗？",
        "response": "您最近一次购买的发票编号（Invoice ID）是 342。",
    },
    {
        "question": "我想要退款。",
        "response": "我无法直接处理退款。关于此问题，请直接联系客户支持。",
    },
    {
        "question": "Wish You Were Here 是谁录制的来着？",
        "response": "Wish You Were Here 是 Pink Floyd 的一张专辑。",
    },
    {
        "question": "你们有哪些 Coldplay 的专辑？",
        "response": "目前我们的目录中没有 Coldplay 的专辑。",
    },
    {
        "question": "我怎样才能成为亿万富翁？",
        "response": "我在这里只能帮您解答与我们数字音乐商店相关的问题。如果您对我们的音乐目录或历史购买有任何疑问，欢迎随时咨询！",
    },
]


dataset_name = "LangGraph 101 多智能体：最终响应（python)"

# 创建数据集
if client.has_dataset(dataset_name=dataset_name):
    dataset = client.create_dataset(dataset_name=dataset_name)
    client.create_examples(inputs=[{"messages":[{"role":"user","content":ex["question"]}]} for ex in examples ],
                           outputs=[{"messages":[{"role":"ai","content":ex["response"]}]} for ex in examples],
                           dataset_id=dataset.id)


# 创建图
graph = multi_agent_verify_graph


# 运行图
async def run_graph(inputs:dict):
    """ 运行图并跟踪最终响应"""
    thread_id = uuid7()

    configuration={"thread_id":thread_id,"user_id":"10"}

    result = await graph.invoke(inputs,config==configuration)

    result = await  graph.ainvoke(Command(resume="我的电话号码是:+55 (11) 3033-5446"),config={"thread_id":thread_id,"user_id":"10"})

    return {"messages":[{"role":"ai","content":result["messages"][-1]["content"]}]}


