"""
desktop/facade.py
==================
Nexus Desktop Domain — DesktopAgent Facade

Single Responsibility: Public API surface for the desktop domain.
Orchestrates OS-level control and app discovery.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, List

from core.desktop.control import pc_controller, PCControl
from core.desktop.discovery import (
    run_discovery, 
    get_app_path, 
    get_all_apps_dict, 
    resolve_system_role
)

logger = logging.getLogger("nexus.desktop.facade")

class DesktopAgent:
    """
    Public facade for the Nexus desktop domain.
    Delegates commands to the underlying PCControl engine and AppDiscovery tools.
    """
    
    @property
    def controller(self) -> PCControl:
        return pc_controller

    # --- App Management ---
    async def open_app(self, app_name: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        return await pc_controller.open_app(app_name, session_id)

    async def close_app(self, app_name: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        return await pc_controller.close_app(app_name, session_id)

    async def minimize_app(self, app_name: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        return await pc_controller.minimize_app(app_name, session_id)

    async def maximize_app(self, app_name: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        return await pc_controller.maximize_app(app_name, session_id)

    async def focus_app(self, app_name: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        return await pc_controller.focus_app(app_name, session_id)

    async def switch_window(self, app_name: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        return await pc_controller.switch_window(app_name, session_id)
        
    async def file_explorer(self, target_path: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        return await pc_controller.file_explorer(target_path, session_id)

    # --- Input Automation ---
    async def type_text(self, text: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        return await pc_controller.type_text(text, session_id)

    async def press_shortcut(self, keys: List[str], session_id: Optional[str] = None) -> Dict[str, Any]:
        return await pc_controller.press_shortcut(keys, session_id)

    async def move_mouse(self, x: int, y: int, session_id: Optional[str] = None) -> Dict[str, Any]:
        return await pc_controller.move_mouse(x, y, session_id)

    async def click(self, x: Optional[int] = None, y: Optional[int] = None, button: str = "left", double: bool = False, session_id: Optional[str] = None) -> Dict[str, Any]:
        return await pc_controller.click(x, y, button, double, session_id)

    async def drag(self, x1: int, y1: int, x2: int, y2: int, session_id: Optional[str] = None) -> Dict[str, Any]:
        return await pc_controller.drag(x1, y1, x2, y2, session_id)

    async def scroll(self, clicks: int, session_id: Optional[str] = None) -> Dict[str, Any]:
        return await pc_controller.scroll(clicks, session_id)

    # --- Clipboard ---
    async def clipboard_read(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        return await pc_controller.clipboard_read(session_id)

    async def clipboard_write(self, text: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        return await pc_controller.clipboard_write(text, session_id)

    # --- Discovery & Observability ---
    async def run_discovery(self) -> None:
        return await run_discovery()

    async def take_screenshot(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        return await pc_controller.take_screenshot(session_id)

    async def analyze_screen(self, query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        return await pc_controller.analyze_screen(query, session_id)

desktop_agent = DesktopAgent()
