from typing import Dict, Any, Optional
from core.browser_agent import browser_agent
import json

async def execute_browser_action(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    if action == "browser_open_url":
        return await browser_agent.open_url(params.get("url", ""))
    elif action == "browser_search":
        return await browser_agent.search(params.get("query", ""))
    elif action == "browser_click":
        return await browser_agent.click(params.get("selector", ""))
    elif action == "browser_extract":
        return await browser_agent.extract(params.get("url", ""))
    elif action == "browser_screenshot":
        return await browser_agent.screenshot(params.get("url"))
    return {"success": False, "verified": False, "error": f"Unknown browser action: {action}"}

BROWSER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "browser_open_url",
            "description": "Open a specific URL in the browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The full URL to open (e.g. https://google.com)"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_search",
            "description": "Search the web for a specific query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search term"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_extract",
            "description": "Extract visible text from a webpage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to extract text from"}
                },
                "required": ["url"]
            }
        }
    }
]
