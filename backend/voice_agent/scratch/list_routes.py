import sys
from pathlib import Path

# Add project root to sys.path
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent # d:\AI\backend\voice_agent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from main import app

for route in app.routes:
    print(f"{route.path} - {route.methods}")
