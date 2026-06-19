import sys
import os

# Add the directory to sys.path
sys.path.append(os.getcwd())

try:
    from main import app
    for route in app.routes:
        print(f"Path: {route.path}, Name: {route.name}, Methods: {route.methods}")
except Exception as e:
    print(f"Error: {e}")

