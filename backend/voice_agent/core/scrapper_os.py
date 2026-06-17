import os
import httpx
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class ScrapperOSBridge:
    def __init__(self, base_url: str = "http://localhost:3000"):
        self.base_url = base_url.rstrip("/")
        
    async def check_health(self) -> Dict[str, Any]:
        """Check if Scrapper OS is online and reachable."""
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{self.base_url}/api/health", timeout=5.0)
                if res.status_code == 200:
                    return {"success": True, "status": "online", "details": res.json()}
                return {"success": False, "status": "offline", "error": f"HTTP {res.status_code}"}
        except Exception as e:
            logger.warning(f"Scrapper OS health check failed: {e}")
            return {"success": False, "status": "offline", "error": str(e)}

    async def list_scrapers(self) -> Dict[str, Any]:
        """Fetch all available scrapers/recipes from Scrapper OS."""
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{self.base_url}/api/scrapers", timeout=5.0)
                if res.status_code == 200:
                    return {"success": True, "scrapers": res.json()}
                return {"success": False, "error": f"HTTP {res.status_code}"}
        except Exception as e:
            logger.error(f"Failed to list scrapers: {e}")
            return {"success": False, "error": str(e)}

    async def run_scraper(self, scraper_id: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Trigger a specific scraper to run."""
        try:
            payload = params or {}
            async with httpx.AsyncClient() as client:
                res = await client.post(f"{self.base_url}/api/scrapers/{scraper_id}/run", json=payload, timeout=30.0)
                if res.status_code in (200, 201, 202):
                    return {"success": True, "result": res.json()}
                return {"success": False, "error": f"HTTP {res.status_code}: {res.text}"}
        except Exception as e:
            logger.error(f"Failed to run scraper {scraper_id}: {e}")
            return {"success": False, "error": str(e)}

scrapper_os = ScrapperOSBridge(os.environ.get("SCRAPPER_OS_URL", "http://localhost:3000"))
