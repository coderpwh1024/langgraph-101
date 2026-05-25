import sys
from pathlib import Path
from typing import TypedDict

from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, dynamic_prompt
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

print("\n")
print("-------------------------------------------02-高级模式-------------------------------------------------")


# 发送邮件工具
@tool
def send_email_v2(to: str, subject: str, body: str) -> str:
    """向收件人发送一封邮件。"""
    response = interrupt({
        "action": "send_email",
        "to": to,
        "subject": subject,
        "body": body,
        "message": "请审阅这封邮件。你可以批准、拒绝或编辑它"
    })
    if response["type"] == "approve":
        return f"邮件发送给{to},主题:{subject}"
    elif response["type"] == "reject":
        return f"邮件被拒绝"
    elif response["type"] == "edit":
        to = response.get("to")
        subject = response.get("subject")
        body = response.get("body")
        return f"邮件修改成功，新的邮件已发送给{to},主题:{subject},内容:{body}"

    return "不知道返回的结果"


# 创建代理
agnet_v2 = create_agent(
    model=model,
    tools=[send_email_v2],
    system_prompt="""你是一个邮件助手""",
    checkpointer=MemorySaver()
)

config_3 = {"configurable": {"thread_id": uuid7()}}

result = agnet_v2.invoke(
    {
        "messages": [HumanMessage(content="给 team@example.com 发一封关于会议的邮件")]
    },
    config=config_3
)
print("已暂停,等待审核")

result = agnet_v2.invoke(
    Command(resume={
        "type": "edit",
        "subject": "紧急：今天下午2点开会",
        "body": "这是编辑后的邮件正文，包含更多详细信息"
    }),
    config=config_3
)
print("最终的结果")
print("\n")
print(result.get("messages")[-1].content)

print("-------------------------------------------03-中间件-------------------------------------------------")


# 创建上下文
class Context(TypedDict):
    user_role: str


@dynamic_prompt
def dynamic_prompt_middleware(request: ModelRequest) -> str:
    """根据用户角色调整系统提示词"""
    user_role = request.runtime.context.get("user_role", "general")

    if user_role == "expert":
        return "你是面向专家的 AI 助手。请提供包含代码示例的详细技术性回答。"
    elif user_role == "beginner":
        return "你是面向初学者的 AI 助手。请用简单的方式解释概念，避免使用专业术语。"
    else:
        return "你是一个AI智能助手";
