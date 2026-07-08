from typing import Annotated, NotRequired, TypedDict

from langchain.agents import create_agent
from langchain_community.utilities import SQLDatabase
from langchain_core.messages import AnyMessage
from langchain_core.tools import tool
from langgraph.graph import add_messages
from langgraph.prebuilt import ToolRuntime

from agents.utils.models import model
from agents.utils.utils import get_engine_for_chinook_db

engine = get_engine_for_chinook_db()
db = SQLDatabase(engine)


class InputState(TypedDict):
    """发票智能体的输入状态。"""

    messages: Annotated[list[AnyMessage], add_messages]


class State(InputState):
    """发票智能体运行时状态。"""

    customer_id: NotRequired[int]
    loaded_memory: NotRequired[str]


@tool
def get_invoices_by_customer_sorted_by_date(runtime: ToolRuntime) -> list[dict]:
    """根据客户 ID 查询该客户的所有发票。

    客户 ID 存储在 state 变量中，因此不会出现在消息历史中。
    发票按开票日期降序排序，这有助于客户查看最近或最早的发票，
    也便于按特定日期范围查看发票。

    Returns:
        该客户的发票列表。
    """
    customer_id = runtime.state.get("customer_id")
    # 注意：教学示例，customer_id 直接拼进 SQL，生产环境应改用参数化查询。
    return db.run(
        f"""
        SELECT *
        FROM Invoice
        WHERE CustomerId = {customer_id}
        ORDER BY InvoiceDate DESC;
        """
    )


@tool
def get_invoices_sorted_by_unit_price(runtime: ToolRuntime) -> list[dict]:
    """按单价从高到低查询客户的发票。

    当客户想根据发票的单价或费用了解某张发票的详细信息时，使用此工具。
    客户 ID 存储在 state 变量中，因此不会出现在消息历史中。

    Returns:
        按单价排序的发票列表。
    """
    customer_id = runtime.state.get("customer_id")
    # 注意：教学示例，customer_id 直接拼进 SQL，生产环境应改用参数化查询。
    query = f"""
        SELECT Invoice.*, InvoiceLine.UnitPrice
        FROM Invoice
        JOIN InvoiceLine ON Invoice.InvoiceId = InvoiceLine.InvoiceId
        WHERE Invoice.CustomerId = {customer_id}
        ORDER BY InvoiceLine.UnitPrice DESC;
    """
    return db.run(query)


@tool
def get_employee_by_invoice_and_customer(runtime: ToolRuntime, invoice_id: int) -> dict:
    """根据发票 ID 和客户 ID 查询关联员工信息。

    此工具接收发票 ID 和客户 ID，并返回与该发票关联的员工信息。
    客户 ID 存储在 state 变量中，因此不会出现在消息历史中。

    Args:
        invoice_id: 指定发票的 ID。

    Returns:
        与该发票关联的员工信息。
    """
    customer_id = runtime.state.get("customer_id")
    # 注意：教学示例，invoice_id / customer_id 直接拼进 SQL，生产环境应改用参数化查询。
    query = f"""
        SELECT Employee.FirstName, Employee.Title, Employee.Email
        FROM Employee
        JOIN Customer ON Customer.SupportRepId = Employee.EmployeeId
        JOIN Invoice ON Invoice.CustomerId = Customer.CustomerId
        WHERE Invoice.InvoiceId = ({invoice_id}) AND Invoice.CustomerId = ({customer_id});
    """
    employee_info = db.run(query, include_columns=True)

    if not employee_info:
        return f"未找到与发票 ID {invoice_id} 和客户 ID {customer_id} 关联的员工。"
    return employee_info


invoice_tools = [
    get_invoices_by_customer_sorted_by_date,
    get_invoices_sorted_by_unit_price,
    get_employee_by_invoice_and_customer,
]

invoice_subagent_prompt = """
    你是助手团队中的一个子智能体，专门负责检索和处理发票信息。
    当问题中包含与发票相关的部分时，你会被路由调用，因此只需回应发票相关内容。

    你可以使用三个工具。这些工具可以帮助你从数据库中检索和处理发票信息：
    - get_invoices_by_customer_sorted_by_date：检索某位客户的所有发票，并按发票日期排序。
    - get_invoices_sorted_by_unit_price：检索某位客户的所有发票，并按单价排序。
    - get_employee_by_invoice_and_customer：检索与某张发票和某位客户关联的员工信息。

    如果你无法检索到发票信息，请告知客户你无法获取该信息，并询问他们是否想搜索其他内容。

    核心职责：
    - 从数据库中检索和处理发票信息
    - 当客户询问时，提供发票的详细信息，包括客户详情、发票日期、总金额、与发票关联的员工等。
    - 始终保持专业、友好和耐心的态度

    你可能会获得额外上下文，应使用这些上下文来帮助回答客户的问题。额外上下文如下：
    """

graph = create_agent(
    model,
    tools=invoice_tools,
    name="invoice_information_subagent",
    system_prompt=invoice_subagent_prompt,
    state_schema=State,
)
