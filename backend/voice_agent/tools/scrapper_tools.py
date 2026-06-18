import json
from typing import Dict, Any, Optional
from core.scrapper_os import scrapper_os

async def check_scrapper_health() -> Dict[str, Any]:
    """Check if Scrapper OS is online and reachable."""
    res = await scrapper_os.check_health()
    if res["success"]:
        return {"success": True, "verified": True, "result": "Scrapper OS is online.", "error": None}
    return {"success": False, "verified": False, "result": "", "error": res.get("error", "Offline")}

async def list_available_scrapers() -> Dict[str, Any]:
    """Fetch all available scrapers/recipes from Scrapper OS."""
    res = await scrapper_os.list_scrapers()
    if res["success"]:
        return {"success": True, "verified": True, "result": json.dumps(res.get("scrapers", [])), "error": None}
    return {"success": False, "verified": False, "result": "", "error": res.get("error", "Failed to fetch")}

async def run_scrapper_task(scraper_id: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Trigger a specific scraper to run using its ID and optional parameters."""
    res = await scrapper_os.run_scraper(scraper_id, params)
    if res["success"]:
        return {"success": True, "verified": True, "result": f"Task {scraper_id} completed successfully. Details: {json.dumps(res.get('result', {}))}", "error": None}
    return {"success": False, "verified": False, "result": "", "error": res.get("error", "Failed to run scraper")}

SCRAPPER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_scrapper_health",
            "description": "Check if the Scrapper OS system is online and ready.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_available_scrapers",
            "description": "Fetch a list of all available web scrapers or data extraction bots in the Scrapper OS.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_scrapper_task",
            "description": "Run a specific web scraping task by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scraper_id": {"type": "string", "description": "The ID of the scraper to run."},
                    "params": {"type": "object", "description": "Optional parameters to pass to the scraper."}
                },
                "required": ["scraper_id"]
            }
        }
    }
]
