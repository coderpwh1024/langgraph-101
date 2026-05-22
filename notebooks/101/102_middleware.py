import sys
from idlelib.colorizer import prog_group_name_to_tag
from pathlib import Path

from langchain_core.messages.tool import tool_call
from langchain_core.tools import tool
from langgraph.types import interrupt

project_root = Path().resolve().parent.parent

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.models import model


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
