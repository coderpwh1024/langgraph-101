import sys
from pathlib import Path

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
from langsmith import uuid7

project_root = Path().resolve().parent.parent

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.models import model


# 发送邮件工具
@tool
def send_mail(to: str, subject: str, body: str) -> str:
    """向收件人发送一封邮件"""

    approval = interrupt({
        "action": "send_mail",
        "to": to,
        "subject": subject,
        "body": body,
        "message": "你想要发送邮件吗？"
    })

    if approval.get("approved"):
        return f"邮件已发送给{to},主题是{subject},内容是{body}"
    else:
        return "邮件发送被拒绝"


print("tool工具已创建成功")
print(f"工具的名称:{send_mail.name}")
print(f"工具描述:{send_mail.description}")

# 创建代理
checkpointer = MemorySaver()
agent = create_agent(
    model=model,
    tools=[send_mail],
    system_prompt="你是一个乐于助人的邮件助手。当被要求发送邮件时，请使用 send_email 工具",
    checkpointer=checkpointer,
)

config = {"configurable": {"thread_id": uuid7()}}

result = agent.invoke(
    {"messages": [HumanMessage(content="给 alice@example.com 发一封邮件，主题为明天的会议，正文为我们下午3点见。")]},
    config=config)

# 检查是否被中断
if "__interrupt__" in result:
    print("agent 被中断")
    interrupt_info = result["__interrupt__"][0]
    print(f" To:{interrupt_info.value['to']}")
    print(f" Subject:{interrupt_info.value['subject']}")
    print(f" Body:{interrupt_info.value['body']}")
    print(f" Message:{interrupt_info.value['message']}")
else:
    print("Agent 没有被中断")

result = agent.invoke(Command(resume={"approved": True}), config=config)
print("最终的响应")
print("\n")
print(result["messages"][-1].content)

config_2 = {"configurable": {"thread_id": uuid7()}}

result = agent.invoke(
    {
        "messages": [HumanMessage(content="给 bob@example.com 发一封邮件，内容是‘你好！’")]
    },
    config=config_2
)

result = agent.invoke(
    Command(resume={"approved": False}),
    config=config_2
)
print("最终的响应")
print("\n")
print(result["messages"][-1].content)

print("--------------------------------------------------------------------------------------------")