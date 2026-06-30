"""
capabilities.py — Backward Compatibility Shim
=============================================
DO NOT add logic here. All behavior lives in core/orchestrator/capabilities.py.
"""
from core.orchestrator.capabilities import registry, CapabilityRegistry

__all__ = ["registry", "CapabilityRegistry"]
