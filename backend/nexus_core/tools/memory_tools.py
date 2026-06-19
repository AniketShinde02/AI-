import logging
import json
from typing import Dict, Any
from core.database import db

logger = logging.getLogger("nexus.tools.memory")

async def update_preferences(preferences: Dict[str, Any]) -> Dict[str, Any]:
    """
    Updates the user's persistent preferences and facts.
    We iterate through the dict and try to place them into appropriate categories.
    """
    try:
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
            
            await db.update_memory(category, key, value)
            
        return {"success": True, "verified": True, "result": f"SUCCESS: Preferences updated to {preferences}. Saved to long-term memory.", "error": None}
    except Exception as e:
        return {"success": False, "verified": False, "result": "", "error": f"Error updating preferences: {str(e)}"}

async def get_user_memory() -> Dict[str, Any]:
    try:
        mem = await db.get_all_memory()
        return {"success": True, "verified": True, "result": json.dumps(mem, indent=2), "error": None}
    except Exception as e:
        return {"success": False, "verified": False, "result": "", "error": f"Error getting memory: {str(e)}"}

async def delete_user_preference(category: str, key: str) -> Dict[str, Any]:
    try:
        await db.delete_memory(category, key)
        return {"success": True, "verified": True, "result": f"Deleted {category}.{key}", "error": None}
    except Exception as e:
        return {"success": False, "verified": False, "result": "", "error": f"Error deleting memory: {str(e)}"}

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
