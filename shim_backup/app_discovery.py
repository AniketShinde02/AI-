"""
app_discovery.py — Backward Compatibility Shim
==============================================
DO NOT add logic here. All behavior lives in core/desktop/discovery.py.
"""
from core.desktop.discovery import (
    run_discovery,
    get_app_path,
    get_all_apps,
    get_all_apps_dict,
    resolve_system_role,
    SYSTEM_ROLES
)

__all__ = [
    "run_discovery",
    "get_app_path",
    "get_all_apps",
    "get_all_apps_dict",
    "resolve_system_role",
    "SYSTEM_ROLES"
]
