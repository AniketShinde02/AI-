import os
import sys
from pathlib import Path

# Setup paths
current_file = Path(__file__).resolve()
backend_dir = current_file.parent
sys.path.insert(0, str(backend_dir))

from main import app

for route in app.routes:
    print(f"{route.path} [{','.join(route.methods)}]")
