import json

import requests
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict
from typing import Annotated, List
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.managed.is_last_step import RemainingSteps

from utils.models import model


# 天气查询工具
@tool
def get_weather(latitude: float, longitude: float) -> str:
    """获取指定坐标的当前温度（华氏度）和天气代码。

       参数:
           latitude: 纬度坐标
           longitude: 经度坐标

       返回:
           包含 temperature_fahrenheit 和 weather_code 的 JSON 字符串。
           注意:回复用户时,不要直接输出 weather_code 数字,
           请将其翻译成通俗的中文天气描述(如"晴天"、"小雨"、"雷暴"等),
           温度也建议同时给出摄氏度换算。
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,weather_code",
        "temperature_unit": "fahrenheit"
    }
    weather = requests.get(url, params).json()["current"]
    temperature = weather["temperature_2m"]
    weather_code = weather["weather_code"]
    result = {
        "temperature_fahrenheit": temperature,
        "weather_code": weather_code
    }
    return json.dumps(result)


@tool
def search_movies(genre: str) -> str:
    """按类型搜索电影"""
    movies = {
        "科幻": "沙丘, 星际穿越, 银翼杀手 2049",
        "喜剧": "布达佩斯大饭店, 超级坏, 利刃出鞘",
        "动作": "疯狂的麦克斯：狂暴之路, 疾速追杀, 碟中谍"
    }
    return movies.get(genre, "没有找到此类型的电影")


# 定义状态
class State(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]


# 工具
tools = [search_movies, get_weather]
tool_node = ToolNode(tools)

model_with_tools = model.bind_tools(tools)


# 助手
def assistant(state: State):
    system_prompt = """你是一个有用的助手，可以查询天气并推荐电影""",
    all_messages = [SystemMessage(system_prompt)] + state["messages"]
    response = model_with_tools.invoke(all_messages)
    return {"messages:"[response]}


# 判断是否继续
def should_continue(state: State):
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "continue"
    else:
        return "end"


builder = StateGraph(State)
builder.add_node("assistant", assistant)
builder.add_node("tool_node", tool_node)

builder.add_edge(START, "assistant")

builder.add_conditional_edges(
    "assistant", should_continue,
    {
        "continue": "tool_node",
        "end": END,
    }
)

builder.add_edge("tool_name", "assistant")
agent = builder.compile(name="agent")

question = "今天旧金山（北纬37.77°，西经122.42°）的天气怎么样？有什么好看的科幻电影推荐吗？"
result = agent.invoke({"messages": HumanMessage(content=question)})

for message in result["messages"]:
    message.pretty_print()
