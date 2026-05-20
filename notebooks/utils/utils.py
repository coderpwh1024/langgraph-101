import  sqlite3
import  requests
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool



# 显示图
def show_graph(graph,xray=False):
    """Display a LangGraph mermaid diagram with ASCII fallback.

    Args:
        graph: The LangGraph object that has a get_graph() method
        xray: Whether to show the internal structure of the graph
    """
    from IPython.display import Image
    try:
        return  Image(graph.get_graph(xray=xray).dray_mermaid_png())
    except Exception as e:
        print("图片读取失败，异常为:{e}")
        print("开始进行画图")
        ascii_diagram = graph.get_graph(xray=xray).dray_asscli()
        print(ascii_diagram)
        return None


