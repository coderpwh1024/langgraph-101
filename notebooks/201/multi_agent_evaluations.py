"""多智能体「最终响应」评估示例。

用 LangSmith 数据集 + openevals 的 LLM-as-judge（correctness 评价器）对
`multi_agent_verify_graph` 的最终回复做正确性评估。

运行依赖：
    - LANGSMITH_API_KEY：创建数据集、运行评估实验
    - DASHSCOPE_API_KEY：LLM 调用（被测图与评价器共用 utils.models.model）

缺少 LANGSMITH_API_KEY 时优雅跳过，避免脚本因缺少凭证而报错。
"""

import asyncio
import os
import sys
from pathlib import Path

# 将项目根目录（含 notebooks/ 的目录）加入 sys.path，
# 以便 import notebooks.utils.models
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# multi_agent.py 与本文件同目录（notebooks/201/），目录名以数字开头不是合法包名，
# 无法用点式 import，这里将该目录加入 sys.path 后按模块名直接 import
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))


# 评估数据集：每条样本含一个用户问题与期望的参考答案（reference output）
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


async def main() -> None:
    """运行多智能体最终响应评估；缺少 LANGSMITH_API_KEY 时跳过。"""
    if not os.getenv("LANGSMITH_API_KEY"):
        print("未检测到 LANGSMITH_API_KEY，跳过多智能体评估示例。")
        return

    # 延迟导入：import multi_agent 会执行其模块顶层的演示代码（联网建库 + 多次 LLM 调用），
    # 因此放在 key 校验之后，避免无凭证时仍触发重型副作用
    from langsmith import Client, uuid7
    from openevals.llm import create_async_llm_as_judge
    from openevals.prompts import CORRECTNESS_PROMPT
    from langgraph.types import Command

    from notebooks.utils.models import model
    from multi_agent import multi_agent_verify_graph

    client = Client()

    # 创建数据集：仅当数据集不存在时才创建，避免重复创建报错
    if not client.has_dataset(dataset_name=dataset_name):
        dataset = client.create_dataset(dataset_name=dataset_name)
        client.create_examples(
            inputs=[
                {"messages": [{"role": "user", "content": ex["question"]}]}
                for ex in examples
            ],
            outputs=[
                {"messages": [{"role": "ai", "content": ex["response"]}]}
                for ex in examples
            ],
            dataset_id=dataset.id,
        )

    graph = multi_agent_verify_graph

    async def run_graph(inputs: dict) -> dict:
        """运行被测图并返回最终响应。

        图以 verify_info 开头，首轮必然因缺少 customer_id 而中断索要电话号；
        这里先用样本问题触发中断，再用固定电话号 resume，让流程跑到 supervisor 回复。

        Args:
            inputs: 数据集样本输入，形如 {"messages": [{"role": "user", ...}]}。

        Returns:
            最终响应，形如 {"messages": [{"role": "ai", "content": ...}]}。
        """
        thread_id = uuid7()
        config = {"configurable": {"thread_id": thread_id}}

        # 首轮触发身份验证中断
        await graph.ainvoke(inputs, config=config)
        # 补电话号，从断点续跑直至 supervisor 给出最终回复
        result = await graph.ainvoke(
            Command(resume="我的电话号码是:+55 (11) 3033-5446"),
            config=config,
        )
        return {
            "messages": [
                {"role": "ai", "content": result["messages"][-1].content}
            ]
        }

    # 创建评价器：用 LLM-as-judge 评估最终回复与参考答案的一致性（correctness）
    correctness_evaluator = create_async_llm_as_judge(
        prompt=CORRECTNESS_PROMPT,
        feedback_key="correctness",
        judge=model,
    )

    # 运行评估实验
    results = await client.aevaluate(
        run_graph,
        data=dataset_name,
        evaluators=[correctness_evaluator],
        experiment_prefix="multi-agent-final-response",
    )
    print(f"评估完成，实验名称：{results.experiment_name}")


if __name__ == "__main__":
    asyncio.run(main())
