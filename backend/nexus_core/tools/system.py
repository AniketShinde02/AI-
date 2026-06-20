import logging
from typing import Dict, Any, List
from core.pc_control import pc_controller

logger = logging.getLogger("nexus.tools.system")

async def execute_pc_action(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for PC actions, meant to be called after permission validation."""
    session_id = params.get("session_id")
    try:
        if action == "pc_open_app":
            res = await pc_controller.open_app(params.get("app_name", ""), session_id=session_id)
        elif action == "pc_close_app":
            res = await pc_controller.close_app(params.get("app_name", ""), session_id=session_id)
        elif action == "pc_minimize_app":
            res = await pc_controller.minimize_app(params.get("app_name", ""), session_id=session_id)
        elif action == "pc_maximize_app":
            res = await pc_controller.maximize_app(params.get("app_name", ""), session_id=session_id)
        elif action == "pc_focus_app":
            res = await pc_controller.focus_app(params.get("app_name", ""), session_id=session_id)
        elif action == "pc_switch_window":
            res = await pc_controller.switch_window(params.get("app_name"), session_id=session_id)
        elif action == "pc_type_text":
            res = await pc_controller.type_text(params.get("text", ""), session_id=session_id)
        elif action == "pc_press_shortcut":
            res = await pc_controller.press_shortcut(params.get("keys", []), session_id=session_id)
        elif action == "pc_move_mouse":
            res = await pc_controller.move_mouse(params.get("x", 0), params.get("y", 0), session_id=session_id)
        elif action == "pc_click":
            res = await pc_controller.click(
                x=params.get("x"),
                y=params.get("y"),
                button=params.get("button", "left"),
                double=params.get("double", False),
                session_id=session_id
            )
        elif action == "pc_drag":
            res = await pc_controller.drag(
                params.get("x1", 0),
                params.get("y1", 0),
                params.get("x2", 0),
                params.get("y2", 0),
                session_id=session_id
            )
        elif action == "pc_scroll":
            res = await pc_controller.scroll(params.get("clicks", 0), session_id=session_id)
        elif action == "pc_clipboard_read":
            res = await pc_controller.clipboard_read(session_id=session_id)
        elif action == "pc_clipboard_write":
            res = await pc_controller.clipboard_write(params.get("text", ""), session_id=session_id)
        elif action == "pc_take_screenshot":
            res = await pc_controller.take_screenshot(session_id=session_id)
        else:
            return {"success": False, "verified": False, "result": "", "error": "Error: Unknown PC action."}
            
        return res
    except Exception as e:
        return {"success": False, "verified": False, "result": "", "error": f"Error executing PC action: {e}"}


# Tool schemas sourced from the single capability registry definition.
# Do NOT add tool schemas here — update core/capability_registry_def.py instead.
from core.capability_registry_def import PC_TOOL_SCHEMAS as SYSTEM_TOOLS

async def get_dynamic_system_tools() -> List[Dict[str, Any]]:
    import copy
    from core.app_discovery import get_all_apps
    tools = copy.deepcopy(SYSTEM_TOOLS)
    try:
        apps = await get_all_apps()
        if apps:
            app_list = ", ".join(apps)
            tools[0]["function"]["description"] = f"Open a Windows application or file. Available applications installed locally: {app_list}."
    except Exception as e:
        logger.error(f"Failed to inject dynamic app inventory: {e}")
    return tools
