"""
core/workspace/__init__.py
==========================
Public API for the Workspace Awareness Engine.

Usage:
    from core.workspace import workspace_manager, WorkspaceState

    state = await workspace_manager.get(session_id)
    workspace_manager.update_execution(status="running", active_capability="browser_click")
"""
from core.workspace.workspace_manager import workspace_manager
from core.workspace.workspace_state import (
    WorkspaceState,
    DesktopState,
    BrowserState,
    ExecutionState,
    MemoryState,
    ProviderState,
    SystemState,
)

__all__ = [
    "workspace_manager",
    "WorkspaceState",
    "DesktopState",
    "BrowserState",
    "ExecutionState",
    "MemoryState",
    "ProviderState",
    "SystemState",
]
