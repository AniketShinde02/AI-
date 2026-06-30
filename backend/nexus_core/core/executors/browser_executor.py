from typing import Dict, Any, List
from core.executors.base import BaseExecutor
from core.browser.facade import browser_agent

class BrowserExecutor(BaseExecutor):
    def get_capabilities(self) -> List[str]:
        return [
            "browser_open_url", "browser_download", "browser_upload", "browser_search",
            "browser_click", "browser_extract", "browser_screenshot", "browser_type",
            "browser_submit", "browser_tab_new", "browser_tab_close", "browser_tab_switch",
            "browser_tab_list", "browser_agentic_task"
        ]

    async def execute(self, capability: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Routes browser_* capabilities to the underlying BrowserAgent."""
        session_id = params.get("session_id")
        
        if capability == "browser_open_url":
            return await browser_agent.open_url(params.get("url", ""), session_id=session_id)
        elif capability == "browser_search":
            return await browser_agent.search(params.get("query", ""), session_id=session_id)
        elif capability == "browser_click":
            return await browser_agent.click(params.get("selector", ""), session_id=session_id)
        elif capability == "browser_extract":
            return await browser_agent.extract(params.get("url", ""), session_id=session_id)
        elif capability == "browser_screenshot":
            return await browser_agent.screenshot(params.get("url"), session_id=session_id)
        elif capability == "browser_download":
            return await browser_agent.download(params.get("url", ""), params.get("dest", ""), session_id=session_id)
        elif capability == "browser_upload":
            return await browser_agent.upload(params.get("selector", ""), params.get("file_path", ""), session_id=session_id)
        elif capability == "browser_type":
            return await browser_agent.browser_type(params.get("selector", ""), params.get("text", ""), session_id=session_id)
        elif capability == "browser_submit":
            return await browser_agent.browser_submit(params.get("selector", ""), session_id=session_id)
        elif capability in ("browser_tab_new", "browser_tab_close", "browser_tab_switch", "browser_tab_list"):
            _action_map = {
                "browser_tab_new": "new",
                "browser_tab_close": "close",
                "browser_tab_switch": "switch",
                "browser_tab_list": "list",
            }
            tab_action = _action_map[capability]
            target = params.get("url") or params.get("target")
            return await browser_agent.browser_tab_management(tab_action, target, session_id=session_id)
        elif capability == "browser_agentic_task":
            goal: str = params.get("goal") or params.get("query") or params.get("target") or ""
            return await browser_agent.run_agentic_task(goal=goal, session_id=session_id)
            
        return {"success": False, "verified": False, "error": f"Unknown browser capability {capability}"}
