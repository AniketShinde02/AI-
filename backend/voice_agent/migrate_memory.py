import os
import json
import asyncio
from core.database import db

MEMORY_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".nexus_states", "user_memory.json"))

async def migrate():
    print(f"Looking for memory file at {MEMORY_FILE}")
    if not os.path.exists(MEMORY_FILE):
        print("No user_memory.json found. Nothing to migrate.")
        return

    with open(MEMORY_FILE, "r") as f:
        data = json.load(f)

    count = 0
    for category, items in data.items():
        if isinstance(items, dict):
            for key, value in items.items():
                await db.update_memory(category, key, value)
                count += 1
                print(f"Migrated {category}.{key}")
        else:
            await db.update_memory("core", category, items)
            count += 1
            print(f"Migrated core.{category}")

    print(f"Successfully migrated {count} memory records to SQLite.")

if __name__ == "__main__":
    asyncio.run(migrate())
