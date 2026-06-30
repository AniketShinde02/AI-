"""
session_state.py — Backward Compatibility Shim
==============================================
DO NOT add logic here. All behavior lives in core/workspace/state.py.
"""
from core.workspace.state import SessionState, SessionStateMixin

__all__ = ["SessionState", "SessionStateMixin"]
