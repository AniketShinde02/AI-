"""
output_processor.py — Backward Compatibility Shim
=================================================
DO NOT add logic here. All behavior lives in core/planner/processor.py.
"""
from core.planner.processor import output_processor, RuntimeOutputProcessor

__all__ = ["output_processor", "RuntimeOutputProcessor"]
