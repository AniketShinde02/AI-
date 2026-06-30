"""
model_router.py — Backward Compatibility Shim
=============================================
DO NOT add logic here. All behavior lives in core/provider/router.py.
"""
from core.provider.router import model_router, ModelRouter, TaskClass, AgentTier

__all__ = ["model_router", "ModelRouter", "TaskClass", "AgentTier"]
