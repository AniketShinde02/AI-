from typing import Dict, Any, List
from core.executors.base import BaseExecutor
from core.vision.scraper_bridge import scrapper_os
import json

class ResearchExecutor(BaseExecutor):
    def get_capabilities(self) -> List[str]:
        return ["check_scrapper_health", "list_available_scrapers", "run_scrapper_task"]

    async def execute(self, capability: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Routes scrapper capabilities."""
        if capability == "check_scrapper_health":
            res = await scrapper_os.check_health()
            if res["success"]:
                return {"success": True, "verified": True, "result": "Scrapper OS is online.", "error": None}
            return {"success": False, "verified": False, "result": "", "error": res.get("error", "Offline")}
            
        elif capability == "list_available_scrapers":
            res = await scrapper_os.list_scrapers()
            if res["success"]:
                return {"success": True, "verified": True, "result": json.dumps(res.get("scrapers", [])), "error": None}
            return {"success": False, "verified": False, "result": "", "error": res.get("error", "Failed to fetch")}
            
        elif capability == "run_scrapper_task":
            scraper_id = params.get("scraper_id", "")
            res = await scrapper_os.run_scraper(scraper_id, params.get("params"))
            if res["success"]:
                return {"success": True, "verified": True, "result": f"Task {scraper_id} completed successfully.", "error": None}
            return {"success": False, "verified": False, "result": "", "error": res.get("error", "Failed to run scraper")}
            
        return {"success": False, "verified": False, "error": f"Unknown research capability {capability}"}
