from typing import Dict, Any, Optional
from core.scrapper_os import scrapper_os

async def check_scrapper_health() -> Dict[str, Any]:
    """Check if Scrapper OS is online and reachable."""
    return await scrapper_os.check_health()

async def list_available_scrapers() -> Dict[str, Any]:
    """Fetch all available scrapers/recipes from Scrapper OS."""
    return await scrapper_os.list_scrapers()

async def run_scrapper_task(scraper_id: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Trigger a specific scraper to run using its ID and optional parameters."""
    return await scrapper_os.run_scraper(scraper_id, params)
