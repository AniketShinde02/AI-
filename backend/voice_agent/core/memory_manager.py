import os
import json

MEMORY_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".nexus_states", "user_memory.json"))

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {
            "communication": {},
            "identity": {},
            "interests": {},
            "assistant_rules": {}
        }
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading memory: {e}")
        return {
            "communication": {},
            "identity": {},
            "interests": {},
            "assistant_rules": {}
        }

def save_memory(data):
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    try:
        with open(MEMORY_FILE, "w") as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving memory: {e}")
        return False

def update_memory(category, key, value):
    mem = load_memory()
    if category not in mem:
        mem[category] = {}
    mem[category][key] = value
    save_memory(mem)
    return {"status": "success", "message": f"Updated {category}.{key}"}

def delete_memory(category, key):
    mem = load_memory()
    if category in mem and key in mem[category]:
        del mem[category][key]
        save_memory(mem)
        return {"status": "success", "message": f"Deleted {category}.{key}"}
    return {"status": "not_found", "message": "Key not found"}
