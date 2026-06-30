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
        import time
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{self.base_url}/api/health", timeout=5.0)
                t = f"{time.perf_counter() - start:.2f}s"
                if res.status_code == 200:
                    return {"success": True, "tool": "check_health", "target": "ScrapperOS", "verification": "HTTP 200", "execution_time": t, "details": res.json()}
                return {"success": False, "tool": "check_health", "target": "ScrapperOS", "verification": f"HTTP {res.status_code}", "execution_time": t}
        except Exception as e:
            t = f"{time.perf_counter() - start:.2f}s"
            logger.warning(f"Scrapper OS health check failed: {e}")
            return {"success": False, "tool": "check_health", "target": "ScrapperOS", "verification": str(e), "execution_time": t}

    async def list_scrapers(self) -> Dict[str, Any]:
        """Fetch all available scrapers/recipes from Scrapper OS."""
        import time
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{self.base_url}/api/scrapers", timeout=5.0)
                t = f"{time.perf_counter() - start:.2f}s"
                if res.status_code == 200:
                    return {"success": True, "tool": "list_scrapers", "target": "ScrapperOS", "verification": f"Found scrapers", "execution_time": t, "scrapers": res.json()}
                return {"success": False, "tool": "list_scrapers", "target": "ScrapperOS", "verification": f"HTTP {res.status_code}", "execution_time": t}
        except Exception as e:
            t = f"{time.perf_counter() - start:.2f}s"
            logger.error(f"Failed to list scrapers: {e}")
            return {"success": False, "tool": "list_scrapers", "target": "ScrapperOS", "verification": str(e), "execution_time": t}

    async def run_scraper(self, scraper_id: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Trigger a specific scraper to run."""
        import time
        start = time.perf_counter()
        try:
            payload = params or {}
            async with httpx.AsyncClient() as client:
                res = await client.post(f"{self.base_url}/api/scrapers/{scraper_id}/run", json=payload, timeout=30.0)
                t = f"{time.perf_counter() - start:.2f}s"
                if res.status_code in (200, 201, 202):
                    return {"success": True, "tool": "run_scraper", "target": scraper_id, "verification": "Job submitted/completed", "execution_time": t, "result": res.json()}
                return {"success": False, "tool": "run_scraper", "target": scraper_id, "verification": f"HTTP {res.status_code}", "execution_time": t}
        except Exception as e:
            t = f"{time.perf_counter() - start:.2f}s"
            logger.error(f"Failed to run scraper {scraper_id}: {e}")
            return {"success": False, "tool": "run_scraper", "target": scraper_id, "verification": str(e), "execution_time": t}

scrapper_os = ScrapperOSBridge(os.environ.get("SCRAPPER_OS_URL", "http://localhost:3000"))
