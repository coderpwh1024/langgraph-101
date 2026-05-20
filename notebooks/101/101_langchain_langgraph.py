import datetime
import sys
from pathlib import Path

from langchain_core.messages import SystemMessage, HumanMessage

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

messages = [
    SystemMessage(content="你是一个乐于助人的 AI 助手，擅长用简单的语言解释技术概念。"),
    HumanMessage(content="什么是智能体（agent）？")
]

resultMessage = model.invoke(messages)
resultMessage.pretty_print();
print("---------------------------------------------------------------------------------")
print("-----------------------------开始回答示列部分---------------------------------------")

# 多轮对话
messages.append(resultMessage)
messages.append(HumanMessage(content="请用中文给我举一个例子"))
resultMessage = model.invoke(messages)
resultMessage.pretty_print();
