"""
vision/facade.py
================
Nexus Vision Domain — VisionAgent Facade

Single Responsibility: Public API surface for the vision domain.
Orchestrates SoM parsing and external scraper bridging.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from core.vision.parser import vision_parser, VisionParser
from core.vision.scraper_bridge import scrapper_os, ScrapperOSBridge

logger = logging.getLogger("nexus.vision.facade")

class VisionAgent:
    """
    Public facade for the Nexus vision domain.
    Delegates commands to the underlying VisionParser and ScrapperOSBridge tools.
    """
    
    @property
    def parser(self) -> VisionParser:
        return vision_parser
        
    @property
    def scrapper(self) -> ScrapperOSBridge:
        return scrapper_os

    # --- Vision Parsing ---
    async def analyze_screenshot(self, base64_image: str, prompt: str, use_som: bool = False) -> str:
        return await vision_parser.analyze_screenshot(base64_image, prompt, use_som)

    # --- External Scraper / ScrapperOS ---
    async def check_health(self) -> Dict[str, Any]:
        return await scrapper_os.check_health()
        
    async def list_scrapers(self) -> Dict[str, Any]:
        return await scrapper_os.list_scrapers()
        
    async def run_scraper(self, scraper_id: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return await scrapper_os.run_scraper(scraper_id, params)

vision_agent = VisionAgent()
