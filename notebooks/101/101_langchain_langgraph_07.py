from langchain_core.tools import tool



# 用户偏好设置工具
@tool
def get_user_preferences(user_id: str) -> str:
    """获取用户已保存的偏好设置"""
    preferences = {
        "alice": "喜欢科幻电影，偏爱温暖天气的旅行目的地",
        "bob": "喜欢喜剧片，旅行偏好寒冷气候"
    }
    return preferences.get(user_id.lower(),"未找到偏好设置")
