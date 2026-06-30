"""
pc_control.py — Backward Compatibility Shim
===========================================
DO NOT add logic here. All behavior lives in core/desktop/control.py.
"""
from core.desktop.control import PCControl, pc_controller

__all__ = ["PCControl", "pc_controller"]
