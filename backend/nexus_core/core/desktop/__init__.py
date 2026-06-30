"""
desktop/__init__.py
====================
Nexus Desktop Domain — Public API
"""
from core.desktop.facade import DesktopAgent, desktop_agent
from core.desktop.control import pc_controller, PCControl
from core.desktop.discovery import run_discovery, get_app_path, get_all_apps_dict, resolve_system_role

__all__ = [
    "DesktopAgent",
    "desktop_agent",
    "pc_controller",
    "PCControl",
    "run_discovery",
    "get_app_path",
    "get_all_apps_dict",
    "resolve_system_role"
]
