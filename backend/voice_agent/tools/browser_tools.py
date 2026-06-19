from typing import Dict, Any
from core.browser_agent import browser_agent
from core.capability_registry_def import BROWSER_TOOL_SCHEMAS as BROWSER_TOOLS


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
    # Tab management — routed through browser_tab_management
    elif action in ("browser_tab_new", "browser_tab_close", "browser_tab_switch", "browser_tab_list"):
        _action_map = {
            "browser_tab_new":    "new",
            "browser_tab_close":  "close",
            "browser_tab_switch": "switch",
            "browser_tab_list":   "list",
        }
        tab_action = _action_map[action]
        target = params.get("url") or params.get("target")
        return await browser_agent.browser_tab_management(tab_action, target)
    return {"success": False, "verified": False, "error": f"Unknown browser action: {action}"}
