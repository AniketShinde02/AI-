import logging
import json
from typing import Dict, Any
from core.memory_manager import update_memory, load_memory, delete_memory

logger = logging.getLogger("nexus.tools.memory")

async def update_preferences(preferences: Dict[str, Any]) -> str:
    """
    Updates the user's persistent preferences and facts.
    We iterate through the dict and try to place them into appropriate categories.
    """
    for key, value in preferences.items():
        # Heuristic to place into categories
        category = "assistant_rules"
        k_lower = key.lower()
        if "lang" in k_lower or "speak" in k_lower or "tone" in k_lower:
            category = "communication"
        elif "name" in k_lower or "job" in k_lower or "project" in k_lower:
            category = "identity"
        elif "like" in k_lower or "interest" in k_lower or "hobby" in k_lower:
            category = "interests"
        
        update_memory(category, key, value)
        
    return f"SUCCESS: Preferences updated to {preferences}. Saved to long-term memory."

async def get_user_memory() -> str:
    mem = load_memory()
    return json.dumps(mem, indent=2)

async def delete_user_preference(category: str, key: str) -> str:
    res = delete_memory(category, key)
    return res["message"]

MEMORY_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "update_preferences",
            "description": "Save important facts or preferences about the user to long-term memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "preferences": {
                        "type": "object",
                        "description": "Key-value pairs of user preferences or facts."
                    }
                },
                "required": ["preferences"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_memory",
            "description": "Retrieve all saved long-term user preferences.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_user_preference",
            "description": "Delete a saved user preference.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "key": {"type": "string"}
                },
                "required": ["category", "key"]
            }
        }
    }
]
