"""
vision_parser.py — Backward Compatibility Shim
==============================================
DO NOT add logic here. All behavior lives in core/vision/parser.py.
"""
from core.vision.parser import VisionParser, vision_parser

__all__ = ["VisionParser", "vision_parser"]
