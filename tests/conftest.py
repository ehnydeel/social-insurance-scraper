import os
import sys
from pathlib import Path

# Ensure we're running from the project root
project_root = Path(__file__).resolve().parent.parent
os.chdir(str(project_root))
sys.path.insert(0, str(project_root))
