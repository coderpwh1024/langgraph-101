import operator
import sys
from datetime import datetime
from pathlib import Path
from typing import Annotated
from typing import TypeDict

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, MessageLikeRepresentation
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

# 将 notebooks 目录加入 sys.path，以便以脚本方式运行时能 import utils
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.models import model

# 研究过程限制
MAX_RESEARCHER_ITERATIONS = 3  # supervisor 最多委派研究的轮次
MAX_REACT_TOOL_CALLS = 10  # 每个 researcher 最多调用工具的次数
MAX_CONCURRENT_RESEARCH_UNITS = 5  # 最多并行运行的 researcher 数量
MAX_STRUCTURED_OUTPUT_RETRIES = 3


def get_today_str() -> str:
    """获取格式化后用于展示的当前日期。

    Returns:
        包含星期、月份、日期和年份的英文日期字符串。
    """
    now = datetime.now()
    return f"{now:%a} {now:%b} {now.day} {now:%Y}"


def get_model() -> BaseChatModel:
    """获取项目统一配置的千问聊天模型。

    模型名称、DashScope API Key 与兼容模式地址统一在
    ``utils.models`` 中配置，业务脚本不重复读取密钥。

    Returns:
        项目共享的千问聊天模型实例。
    """
    return model


@tool(
    description="联网搜索工具：使用千问内置联网搜索能力检索最新网络信息"
)
async def web_search(query: str) -> str:
    """使用千问（阿里云百炼）内置联网搜索能力检索信息。

    Args:
        query: 需要联网检索的问题，应尽量具体、聚焦。

    Returns:
        千问根据联网搜索结果生成的回答，包含来源标题和链接。
    """
    # 在共享模型上临时开启搜索，避免业务脚本重复配置 API Key 和地址。
    search_model = get_model().bind(
        extra_body={
            "enable_search": True,
            "search_options": {"forced_search": True},
        }
    )
    search_prompt = (
        "请联网搜索以下问题并给出简明、准确的回答，"
        "在回答结尾列出信息来源的标题和链接：\n"
        f"{query}"
    )
    response = await search_model.ainvoke([HumanMessage(content=search_prompt)])
    return str(response.content)


def qwen_websearch_called(response: AIMessage) -> bool:
    """判断千问是否发起了 ``web_search`` 工具调用。

    百炼 OpenAI 兼容接口不会返回 OpenAI Responses API 中的
    ``tool_outputs/web_search_call`` 字段，因此应检查 LangChain 解析后的
    ``tool_calls``。真正的联网检索由 ``web_search`` 工具执行。

    Args:
        response: 千问返回的 AI 消息。

    Returns:
        如果消息中包含 ``web_search`` 工具调用则返回 True，否则返回 False。
    """
    return any(
        tool_call.get("name") == web_search.name
        for tool_call in response.tool_calls
    )


print("\n")
print("✓ 已加载项目统一配置的千问模型（阿里云百炼）")
print("\n")

print(
    "--------------------01-构建一个单例搜索 Agent--------------------"
)
print("\n")


# 研究的状态实体类
class ResearcherState(TypeDict):
    """单个研究员智能体的状态"""
    researcher_messages: Annotated[list[MessageLikeRepresentation], operator.add]
    researcher_topic: str
    tool_call_iterations: int


# 输出实体类
class ResearcherOutputState(TypeDict):
    """研究员的输出——仅包含压缩后的研究结果"""
    researcher_messages: Annotated[list[MessageLikeRepresentation], operator.add]
    researcher_research: str
    raw_notes: list


print("\n")


@tool(description="表示研究已完成")
def researcher_complete() -> str:
    """在收集到足够信息后标记研究完成。

    Returns:
        研究已完成的确认信息。
    """
    return "研究已标记为完成"


@tool(description="用于研究规划的战略性反思工具")
def think_tool(reflection: str) -> str:
    """每次搜索后使用此工具分析结果并规划后续步骤。

    Args:
        reflection: 对研究进展和后续步骤的详细反思。

    Returns:
        已记录的研究反思。
    """
    return f"反思已记录：{reflection}"


def get_all_tools() -> list[object]:
    """获取所有可用的研究工具。

    Returns:
        研究阶段可调用的工具列表。
    """
    tools = [researcher_complete, think_tool]
    tools.append({"type": "web_search_preview"})
    return tools
