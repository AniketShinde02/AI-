"""
browser/models.py
=================
Nexus Browser Domain — Shared Types

Single Responsibility: House all public models, TypeDicts, Enums, and dataclass
contracts used across the browser domain. Contains NO execution logic.

Dependency Rule: This module has ZERO internal imports. Every other browser module
may import from here freely without risk of circular imports.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


# ---------------------------------------------------------------------------
# Action Result contract
# ---------------------------------------------------------------------------

@dataclass
class ActionResult:
    """Standard return type for every browser action."""
    success: bool
    verified: bool
    tool: str
    target: str
    result: Optional[str] = None
    error: Optional[str] = None
    execution_time: Optional[str] = None
    recovery_level_used: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


# ---------------------------------------------------------------------------
# Browser State Enum (moved here from browser_state.py for domain ownership)
# ---------------------------------------------------------------------------

class BrowserStateEnum(str, Enum):
    """Deterministic state machine states for BrowserAgent."""
    IDLE = "idle"
    INITIALIZING = "initializing"
    NAVIGATING = "navigating"
    VERIFYING = "verifying"
    EXECUTING = "executing"
    WAITING = "waiting"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Browser Memory
# ---------------------------------------------------------------------------

@dataclass
class BrowserMemory:
    """
    In-process memory for a single browser session.
    Holds navigation history, step trace, and contextual hints.
    """
    current_url: str = "about:blank"
    page_title: str = ""
    current_tab_index: int = 0
    total_tabs: int = 1
    last_action: str = ""
    last_action_target: str = ""
    last_action_result: str = ""
    last_successful_action: str = ""
    session_state: str = "idle"
    step_history: List[Dict[str, Any]] = field(default_factory=list)
    nav_history: List[str] = field(default_factory=list)
    focused_element: str = ""
    pending_navigation: bool = False
    downloads: List[str] = field(default_factory=list)
    uploads: List[str] = field(default_factory=list)
    failure_matrix: List[Dict[str, Any]] = field(default_factory=list)
    browser_hint: Optional[str] = None

    def record_step(self, action: str, target: str, result: str, success: bool) -> None:
        self.last_action = action
        self.last_action_target = target
        self.last_action_result = result
        if success:
            self.last_successful_action = action
        self.step_history.append({
            "action": action,
            "target": target,
            "result": result[:200],
            "success": success,
        })
        if len(self.step_history) > 100:
            self.step_history = self.step_history[-100:]

    def record_navigation(self, url: str) -> None:
        if url and url != "about:blank":
            self.nav_history.append(url)
            if len(self.nav_history) > 50:
                self.nav_history = self.nav_history[-50:]

    def to_dict(self) -> Dict[str, Any]:
        d = self.__dict__.copy()
        d["step_count"] = len(d.pop("step_history", []))
        d["failure_count"] = len(d.pop("failure_matrix", []))
        d["nav_history"] = d.get("nav_history", [])[-5:]
        return d
