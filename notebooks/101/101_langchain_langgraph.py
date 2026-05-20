import json
import sys
from http.client import responses
from pathlib import Path

from langchain.agents import create_agent
from langchain_core.tools import tool
import requests
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from requests_toolbelt.multipart.encoder import to_list

project_root = Path().resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.models import model

import warnings

warnings.filterwarnings('ignore', message="LangSmith now uses UUID v7")

# begin = datetime.datetime.now()
# result = model.invoke("解释一下什么是智能体?")
# result.pretty_print();

# end = datetime.datetime.now()
# print(f"耗时:{end-begin}")
print("---------------------------------------------------------------------------------")

# messages = [
#     SystemMessage(content="你是一个乐于助人的 AI 助手，擅长用简单的语言解释技术概念。"),
#     HumanMessage(content="什么是智能体（agent）？")
# ]

# resultMessage = model.invoke(messages)
# resultMessage.pretty_print();
print("---------------------------------------------------------------------------------")
print("-----------------------------02开始回答示列部分---------------------------------------")

# 多轮对话
# messages.append(resultMessage)
# messages.append(HumanMessage(content="请用中文给我举一个例子"))
# resultMessage = model.invoke(messages)
# resultMessage.pretty_print();

print("-----------------------------03开始进行Tool工具部分---------------------------------------")


# 电影搜索工具
@tool
def search_movies(genre: str) -> str:
    """按类型搜索电影"""
    movies = {
        "科幻": "沙丘, 星际穿越, 银翼杀手 2049",
        "喜剧": "布达佩斯大饭店, 超级坏, 利刃出鞘",
        "动作": "疯狂的麦克斯：狂暴之路, 疾速追杀, 碟中谍"
    }
    return movies.get(genre, "没有找到此类型的电影")


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


print(get_weather.invoke({"latitude": 37.77, "longitude": 122.42}))

tools = [search_movies, get_weather]
model_with_tools = model.bind_tools(tools)
message = "西雅图的天气怎么样？（西雅图的坐标大约是北纬 47.6°，西经 122.33°）"
resultTool = model_with_tools.invoke(message)
print("工具:", resultTool.tool_calls)

if resultTool.tool_calls:
    tool_call = resultTool.tool_calls[0]

    if tool_call["name"] == "get_weather":
        result = get_weather.invoke(tool_call["args"])
    elif tool_call["name"] == "search_movies":
        result = search_movies.invoke(tool_call["args"])

    tool_message = ToolMessage(
        content=result,
        tool_call_id=tool_call["id"]
    )

    final_response = model_with_tools.invoke([
        HumanMessage(content=message),
        resultTool,
        tool_message])
    final_response.pretty_print()

print("\n")
print("-----------------------------04部分构建 Agent---------------------------------------")

anget = create_agent(
    model=model,
    tools=[get_weather, search_movies],
    system_prompt="""你是一个能查询天气和推荐电影的智能助手"""
)

agentResult = anget.invoke({
    "messages": [HumanMessage(content="纽约的天气怎么样?(北纬 40.71°,西经 74.01°)另外推荐几部科幻电影")]
})

for message in agentResult["messages"]:
    message.pretty_print()

print("\n")
print("-----------------------------05 Agent 记忆与状态---------------------------------------")

checkpointer = MemorySaver();

agent_with_memory = create_agent(
    model=model,
    tools=[get_weather, search_movies],
    system_prompt="你是一个智能助手!",
    checkpointer=checkpointer
)

config ={};
