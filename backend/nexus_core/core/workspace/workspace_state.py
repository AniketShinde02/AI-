"""
workspace_state.py
==================
Single canonical Pydantic schema for all Nexus workspace state.

This is the ONLY place WorkspaceState is defined. All subsystems
(browser, desktop, execution, memory, provider, system) consume
this exact shape. Never duplicate these fields elsewhere.

Design rules:
- All fields have defaults — collection failures never crash consumers.
- Pydantic BaseModel with model_config = {"frozen": False} for in-place updates.
- Timestamps are Unix floats.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field
import time


# ---------------------------------------------------------------------------
# Desktop sub-state
# ---------------------------------------------------------------------------

class DesktopState(BaseModel):
    active_window: str = ""
    active_app: str = ""
    pid: Optional[int] = None
    monitor_count: int = 1
    screen_width: int = 1920
    screen_height: int = 1080
    clipboard: Optional[str] = None   # Only populated on explicit request
    collected_at: float = Field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Browser sub-state
# ---------------------------------------------------------------------------

class BrowserState(BaseModel):
    current_url: str = "about:blank"
    page_title: str = ""
    total_tabs: int = 1
    current_tab_index: int = 0
    session_state: str = "idle"     # idle|navigating|interacting|completed|error
    last_action: str = ""
    last_action_target: str = ""
    step_count: int = 0
    screenshot_b64: Optional[str] = None   # TTL-cached, None if stale
    collected_at: float = Field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Execution sub-state (DAG + tool hooks)
# ---------------------------------------------------------------------------

class ExecutionState(BaseModel):
    current_task: Optional[str] = None
    active_capability: Optional[str] = None
    status: str = "idle"                 # idle|running|retrying|completed|failed|rate_limit_cooldown
    verification_state: Optional[str] = None
    last_result: Optional[str] = None
    execution_time: Optional[str] = None
    dag_graph_id: Optional[str] = None
    dag_active_node: Optional[str] = None
    dag_retries: int = 0
    updated_at: float = Field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Memory sub-state
# ---------------------------------------------------------------------------

class MemoryState(BaseModel):
    session_id: str = ""
    recent_turns: int = 0
    active_project: Optional[str] = None
    collected_at: float = Field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Provider sub-state
# ---------------------------------------------------------------------------

class ProviderState(BaseModel):
    active_provider: str = "unknown"
    active_model: str = "unknown"
    is_healthy: bool = True
    rpm_used: int = 0
    rpm_limit: int = 30
    tpm_used: int = 0
    tpm_limit: int = 6000
    collected_at: float = Field(default_factory=time.time)


# ---------------------------------------------------------------------------
# System sub-state
# ---------------------------------------------------------------------------

class SystemState(BaseModel):
    cpu_percent: float = 0.0
    ram_percent: float = 0.0
    gpu_percent: Optional[float] = None   # None if GPU not available (deferred V1)
    network_online: bool = True
    timestamp: float = Field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Root WorkspaceState — the single source of truth
# ---------------------------------------------------------------------------

class WorkspaceState(BaseModel):
    """
    The canonical workspace state for all Nexus subsystems.

    Consumed by:
      - Action Router (context injection into LLM system prompt)
      - Planner / Compiler (goal decomposition with awareness)
      - Executor (DAG context)
      - Gemini Live (injected into system instruction refresh)
      - Frontend via broadcast_workspace_state()
    """
    desktop: DesktopState = Field(default_factory=DesktopState)
    browser: BrowserState = Field(default_factory=BrowserState)
    execution: ExecutionState = Field(default_factory=ExecutionState)
    memory: MemoryState = Field(default_factory=MemoryState)
    provider: ProviderState = Field(default_factory=ProviderState)
    system: SystemState = Field(default_factory=SystemState)

    def to_broadcast_dict(self) -> dict:
        """
        Produces the minimal dict for WebSocket broadcast.
        Excludes large fields (screenshot) from default broadcast.
        """
        return {
            "current_task": self.execution.current_task,
            "active_capability": self.execution.active_capability,
            "tool_target": self.execution.dag_active_node,
            "execution_time": self.execution.execution_time,
            "last_result": self.execution.last_result,
            "status": self.execution.status,
            "verification_state": self.execution.verification_state,
            "active_window": self.desktop.active_window,
            "browser_screenshot": self.browser.screenshot_b64,
            "browser_memory": self.browser.model_dump(exclude={"screenshot_b64"}),
            "system": self.system.model_dump(),
            "provider": self.provider.model_dump(),
        }
