import logging
from typing import Dict, Any, List
from core.pc_control import pc_controller

logger = logging.getLogger("nexus.tools.system")

async def execute_pc_action(action: str, params: Dict[str, Any]) -> str:
    """Wrapper for PC actions, meant to be called after permission validation."""
    try:
        if action == "pc_open_app":
            res = await pc_controller.open_app(params.get("app_name", ""))
        elif action == "pc_close_app":
            res = await pc_controller.close_app(params.get("app_name", ""))
        elif action == "pc_type_text":
            res = await pc_controller.type_text(params.get("text", ""))
        elif action == "pc_press_shortcut":
            res = await pc_controller.press_shortcut(params.get("keys", []))
        elif action == "pc_take_screenshot":
            res = await pc_controller.take_screenshot()
        else:
            return "Error: Unknown PC action."
            
        return res.get("message", res.get("error", "Unknown outcome"))
    except Exception as e:
        return f"Error executing PC action: {e}"

# Define the tool metadata for the LLM Model Router
SYSTEM_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "pc_open_app",
            "description": "Open a Windows application or file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {"type": "string", "description": "Name of the app (e.g. 'notepad', 'chrome')"}
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "pc_close_app",
            "description": "Close a running Windows application by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {"type": "string", "description": "Name of the app to close (e.g. 'notepad', 'chrome')"}
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "pc_type_text",
            "description": "Simulate keyboard typing for the provided text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The exact text to type"}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "pc_press_shortcut",
            "description": "Simulate a keyboard shortcut (e.g. ['ctrl', 'c']).",
            "parameters": {
                "type": "object",
                "properties": {
                    "keys": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of keys to press together."
                    }
                },
                "required": ["keys"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "pc_take_screenshot",
            "description": "Take a screenshot of the primary display.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]
