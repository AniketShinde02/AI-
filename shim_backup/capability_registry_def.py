"""
capability_registry_def.py — Backward Compatibility Shim
========================================================
DO NOT add logic here. All behavior lives in core/orchestrator/registry_def.py.
"""
from core.orchestrator.registry_def import CAPABILITY_DEFINITIONS, CapabilityDef, _make_app_schema

ACTION_ROUTER_TOOL_NAMES = [c.id for c in CAPABILITY_DEFINITIONS]

__all__ = ["CAPABILITY_DEFINITIONS", "CapabilityDef", "_make_app_schema", "ACTION_ROUTER_TOOL_NAMES"]
