import operator
import sys
from datetime import datetime
from pathlib import Path
from typing import Annotated
from typing import TypeDict

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, MessageLikeRepresentation, SystemMessage
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


research_system_prompt = """你是一名研究助理，负责围绕用户输入的主题开展研究。作为背景信息，今天的日期是 {date}。

  <Task>
  你的任务是使用工具收集与用户输入主题相关的信息。
  你可以使用提供给你的任意工具，查找有助于回答研究问题的资料。
  </Task>

  <Available Tools>
  你可以使用以下工具：
  1. **Web search**：执行网络搜索以收集信息
  2. **think_tool**：在研究过程中进行反思和策略规划

  **关键要求：每次搜索后都必须使用 think_tool 反思搜索结果，并规划下一步行动。**
  </Available Tools>

  <Instructions>
  像一名时间有限的人类研究员一样思考：

  1. **仔细阅读问题**——用户具体需要哪些信息？
  2. **从宽泛搜索开始**——首先使用覆盖面广、综合性强的搜索查询
  3. **每次搜索后暂停并评估**——现有信息是否足以回答问题？还缺少什么？
  4. **随着信息逐渐完善，执行更精准的搜索**——补齐信息缺口
  5. **能够自信回答时立即停止**——不要为了追求完美而继续搜索
  </Instructions>

  <Hard Limits>
  **工具调用预算**：
  - **简单问题**：最多调用搜索工具 2～3 次
  - **复杂问题**：最多调用搜索工具 4 次
  - **必须停止**：调用搜索工具 4 次后，即使仍未找到合适的资料，也必须停止搜索

  **出现以下情况时立即停止**：
  - 已经能够全面回答用户的问题
  - 已经找到 3 个以上与问题相关的示例或信息来源
  - 最近两次搜索返回了相似的信息
  </Hard Limits>
  """


#  研究节点
async def researcher(state: ResearcherState, confnig):
    """执行研究工作的主研究员节点"""
    researcher_messages = state.get("researcher_messages")

    # 获取所有的工具
    tools = get_all_tools()

    # 提示词
    researcher_prompt = research_system_prompt.format(data=get_today_str())

    research_model = (
        get_model().bind_tools(tools).with_retry(stop_after_attempt=MAX_STRUCTURED_OUTPUT_RETRIES)
    )

    messages = [SystemMessage(content=researcher_prompt)] + researcher_messages

    response = await research_model.ainvoke(messages)

    return {
        "researcher_messages": [response],
        "tool_call_iterations": state.get("tool_call_iterations", 0) + 1
    }
