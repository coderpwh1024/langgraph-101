
import sys
from pathlib import Path


project_root = Path().resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.models import model


import  warnings
warnings.filterwarnings('ignore',message="LangSmith now uses UUID v7")

result = model.invoke("解释一下什么是智能体?")
result.pretty_print();
