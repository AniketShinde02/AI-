import os
import sys
import json
import asyncio

# Reconfigure stdout/stderr to support unicode output on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')  # type: ignore

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(backend_dir, "backend"))
sys.path.append(os.path.join(backend_dir, "backend", "nexus_core"))

from core.database import db

async def migrate():
    json_path = os.path.join(backend_dir, "backend", ".nexus_states", "user_memory.json")
    if not os.path.exists(json_path):
        print(f"No legacy memory file found at {json_path}")
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        print("Migrating memory from JSON file to SQLite...")
        for category, items in data.items():
            if not isinstance(items, dict):
                continue
            for key, value in items.items():
                print(f"Migrating: [{category}] {key}")
                await db.update_memory(category, key, value)
        
        print("Migration complete!")
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())

