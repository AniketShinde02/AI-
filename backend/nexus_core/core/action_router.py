"""
action_router.py — Backward Compatibility Shim
==============================================
DO NOT add logic here. All behavior lives in core/planner/action_router.py.
"""
from core.planner.action_router import action_router, ActionRouter

__all__ = ["action_router", "ActionRouter"]
