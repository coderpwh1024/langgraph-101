import sys
from pathlib import Path

from deepagents import create_deep_agent

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

print("\n")

agent = create_deep_agent(
    model=model,
    system_prompt="你是一名乐于助人的研究助理。在引用文件路径时，请使用反引号格式（如 path/file.md），而不要使用 Markdown 链接,回答一律用中文"
)
print("深入研究Agent创建成功")


result = agent.invoke({
    "messages":[
        {"role":"user","content":"创建一个名为 notes.md 的文件，写入文本 'Hello from Deep Agents!'，然后读取该文件以确认内容"}
    ]
})

print("结果为:",result["messages"][-1].content)
print("\n")