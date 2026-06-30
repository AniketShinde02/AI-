"""
provider_governor.py — Backward Compatibility Shim
==================================================
DO NOT add logic here. All behavior lives in core/provider/governor.py.
"""
from core.provider.governor import governor, ProviderGovernor

__all__ = ["governor", "ProviderGovernor"]
