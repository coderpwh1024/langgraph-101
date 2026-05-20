
import sys
from pathlib import Path


project_root = Path().resolve().parser.parent

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.models import model