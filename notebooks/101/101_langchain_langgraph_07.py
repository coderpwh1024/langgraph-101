import requests
from langchain.agents import create_agent
from langchain_core.tools import tool
import json

from langgraph.checkpoint.memory import MemorySaver
from langsmith import uuid7

from utils.models import model


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


# 用户偏好设置工具
@tool
def get_user_preferences(user_id: str) -> str:
    """获取用户已保存的偏好设置"""
    preferences = {
        "alice": "喜欢科幻电影，偏爱温暖天气的旅行目的地",
        "bob": "喜欢喜剧片，旅行偏好寒冷气候"
    }
    return preferences.get(user_id.lower(), "未找到偏好设置")


# 电影推荐工具
@tool
def book_recommendation(genre: str, user_preferences: str = "") -> str:
    """根据类型和用户偏好获取个性化电影推荐 """
    recommendations = {
        "sci-fi": "根据您的偏好，推荐尝试：《降临》、《机械姬》或《火星救援》",
        "comedy": "根据您的偏好，推荐尝试：《谋杀绿脚趾》、《王牌播音员》或《伴娘》"
    }
    return recommendations.get(genre.lower(), "未找到此类别")


assistant = create_agent(
    model=model,
    tools=[get_user_preferences, book_recommendation, get_weather],
    system_prompt="""你是一个乐于助人的个人助理。

    你可以：
    - 查询任意城市的天气
    - 查找用户偏好设置
    - 根据偏好推荐电影

    请始终保持友好的态度，并根据用户偏好对回复进行个性化处理。""",
    checkpointer=MemorySaver()
)

config = {"configurable":{"thread_id":uuid7()}}

print("="*50)
print("开始进行对话")
print("=" * 50 + "\n")

print("用户：你好，我是 Alice。能帮我查一下我的偏好设置并推荐一部电影吗？\n")

result =assistant.invoke(
    {"messages":[{"role":"user","content":"另外，旧金山的天气怎么样？（北纬37.另外，旧金山的天气怎么样？（北纬37.77°，西经122.42°）"}]},
    config=config
)
print(f"AI助手回复:{result['messages'][-1].content}")
print("\n")