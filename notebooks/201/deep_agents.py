import  sys
from pathlib import Path

project_root=Path().resolve().parent.parent

if str(project_root) not in sys.path:
     sys.path.insert(0, str(project_root))

from utils.models import model

from dotenv import load_dotenv
load_dotenv(dotenv_path="../../.env", override=True)

import warnings
warnings.filterwarnings('ignore', message='LangSmith now uses UUID v7')