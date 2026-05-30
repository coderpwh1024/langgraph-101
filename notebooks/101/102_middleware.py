import sys
from idlelib.colorizer import prog_group_name_to_tag
from pathlib import Path
from typing import TypedDict, Any, Callable
from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import ModelRequest, dynamic_prompt, AgentMiddleware, ModelResponse
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import state
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


# 创建工具
@tool
def explain_concept(concept: str) -> str:
    """解释一个编程概念"""
    explanations = {
        "async": "异步编程允许代码在不阻塞的情况下运行",
        "recursion": "递归是指一个函数调用自身"
    }
    return explanations.get(concept.lower(), "未找到 Concept 的解释")


# 创建 代理
agent_with_middleware = create_agent(
    model=model,
    tools=[explain_concept],
    middleware=[dynamic_prompt_middleware],
    context_schema=Context
)
print("代理已创建成功")
print("专家用户")
print("=" * 50)

result = agent_with_middleware.invoke(
    {
        "messages": [HumanMessage(content="解释一下 async 编程")]
    },
    context={"user_role": "expert"}
)
print("结果为:\n")
print(result["messages"][-1].content)

print("\n")
print("\n")


class RequestLoggerMiddleware(AgentMiddleware):
    """ 记录所有模型请求以便调试 """

    # 执行模型前
    def before_model(self, state: AgentState, runtime) -> dict[str, Any] | None:
        """执行模型前记录日志"""
        message_count = len(state.get("messages", []))
        print(f"正在处理第 {message_count} 条消息")
        return None

    # 执行模型后
    def warp_model_call(self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]) -> ModelResponse:
        """ 记录模型请求的详细信息，然后调用 handler"""
        print(f"[Model REQUEST]")
        print(f"Model:{request.model if hasattr(request, 'model') else 'default'}")
        print(f"有效工具:{len(request.tools) if request.tools else 0}")
        return handler(request)

    def after_model(self, state: AgentState, runtime) -> dict[str, Any] | None:
        """执行模型后记录日志"""
        last_message = state["messages"][-1]
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            print(f"[AFTER MODEL] 模型请求{len(last_message.tool_calls)} tool call(s)")
        else:
            print(f"[AFTER MODEL] 模型最终返回")
        return None


# 创建代理
agent_with_logger = create_agent(
    model=model,
    tools=[explain_concept],
    middleware=[RequestLoggerMiddleware()],
)
print("代理已创建成功")

print("\n" + "=" * 50)
print("Agent 已经运行")
print("=" * 50 + "\n")

result = agent_with_logger.invoke(
    {"messages": [{"role": "user", "content": "解释递归"}]}
)
print("\n" + "=" * 50)
print("最终返回:\n")
print("=" * 50)
print(result["messages"][-1].content)

print("----------------------------------------------04-LOOP------------------------------------------------")


# 创建工具
@tool
def delete_database(database_name: str) -> str:
    """删除数据库,这是一个危险的操作!"""
    response = interrupt(
        {
            "action": "delete_databases",
            "databases_name": database_name,
            "warning": "这将永久删除数据库",
            "message": "你确定吗？"
        })

    if response.get("confirmed"):
        return f"Database '{database_name}' 已经删除（模拟)"
    else:
        return "操作取消"


# 创建代理
class SafetyMiddleware(AgentMiddleware):
    """添加安全检查和日志记录"""
    name = "safety_checker"

    def after_model(self, state: AgentState) -> dict[str, Any] | None:
        """检查模型输出并记录日志"""
        last_message = state["messages"][-1]

        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            for tool_call in last_message.tool_calls:
                if "delete" in tool_call["name"].lower():
                    print(f"[SAFETY] 检测到危险操作")
                    print(f" 工具:{tool_call['name']}")
                    print(f" 参数:{tool_call['args']}")

        return None


# 创建代理
production_agent = create_agent(
    model=model,
    tools=[delete_database],
    middleware=[SafetyMiddleware()],
    checkpointer=MemorySaver()
)

config_4 = {"configurable": {"thread_id": uuid7()}}

print("代理已创建成功")
print("\n" + "=" * 50)
print("检测危险操作")
print("=" * 50 + "\n")

result = production_agent.invoke({
    "messages": [HumanMessage(content="删除生产数据库")]
},
    config=config_4
)

if "_interrupt_" in result:
    interrupt_info = result["_interrupt_"][0]
    print("\n 用户授权请求")
    print(f"{interrupt_info.value["warning"]}")
    print(f" 数据库:{interrupt_info.value["databases_name"]}")

print("\n（在实际应用中，会由人工审核后才继续执行）")
