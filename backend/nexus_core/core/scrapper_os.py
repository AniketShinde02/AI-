"""
scrapper_os.py — Backward Compatibility Shim
============================================
DO NOT add logic here. All behavior lives in core/vision/scraper_bridge.py.
"""
from core.vision.scraper_bridge import ScrapperOSBridge, scrapper_os

__all__ = ["ScrapperOSBridge", "scrapper_os"]
