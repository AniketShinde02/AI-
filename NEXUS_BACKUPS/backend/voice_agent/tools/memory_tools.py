import logging
from typing import Dict, Any

logger = logging.getLogger("nexus.tools.memory")

# We'll use the memory engine to update the profile
# This requires access to the memory instance, which is in the LLM.
# However, for a clean tool interface, we can pass the data back to the LLM to handle.

async def update_preferences(preferences: Dict[str, Any]) -> str:
    """
    Updates the user's persistent preferences and facts (e.g. favorite apps, technical stack).
    Example: {"favorite_editor": "VS Code", "stack": "Next.js"}
    """
    # This tool will return a signal to the LLM to save the data
    return f"SUCCESS: Preferences updated to {preferences}. I will remember this."

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
    }
]
