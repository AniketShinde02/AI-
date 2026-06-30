"""
vision/__init__.py
==================
Nexus Vision Domain — Public API
"""
from core.vision.facade import VisionAgent, vision_agent
from core.vision.parser import vision_parser, VisionParser
from core.vision.scraper_bridge import scrapper_os, ScrapperOSBridge

__all__ = [
    "VisionAgent",
    "vision_agent",
    "vision_parser",
    "VisionParser",
    "scrapper_os",
    "ScrapperOSBridge"
]
