from typing import Dict, Any, List
from core.executors.base import BaseExecutor
from core.desktop.control import pc_controller

class DesktopExecutor(BaseExecutor):
    def get_capabilities(self) -> List[str]:
        return [
            "pc_open_app", "pc_close_app", "pc_minimize_app", "pc_maximize_app",
            "pc_focus_app", "pc_switch_window", "pc_file_explorer", "pc_take_screenshot",
            "pc_type_text", "pc_press_shortcut", "pc_move_mouse", "pc_click",
            "pc_drag", "pc_scroll", "pc_clipboard_read", "pc_clipboard_write"
        ]

    async def execute(self, capability: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Routes pc_* capabilities to the underlying PCController."""
        target = params.get("target", "")
        
        if capability == "pc_open_app":
            return await pc_controller.open_app(target)
        elif capability == "pc_close_app":
            return await pc_controller.close_app(target)
        elif capability == "pc_minimize_app":
            return await pc_controller.minimize_app(target)
        elif capability == "pc_maximize_app":
            return await pc_controller.maximize_app(target)
        elif capability == "pc_focus_app":
            return await pc_controller.focus_app(target)
        elif capability == "pc_switch_window":
            return await pc_controller.switch_window(target)
        elif capability == "pc_file_explorer":
            return await pc_controller.file_explorer(target)
        elif capability == "pc_take_screenshot":
            return await pc_controller.take_screenshot()
        elif capability == "pc_type_text":
            return await pc_controller.type_text(params.get("text", ""))
        elif capability == "pc_press_shortcut":
            return await pc_controller.press_shortcut(params.get("keys", ""))
        elif capability == "pc_move_mouse":
            return await pc_controller.move_mouse(int(params.get("x", 0)), int(params.get("y", 0)))
        elif capability == "pc_click":
            return await pc_controller.click(
                int(params.get("x", 0)), 
                int(params.get("y", 0)), 
                params.get("button", "left"), 
                bool(params.get("double", False))
            )
        elif capability == "pc_drag":
            return await pc_controller.drag(
                int(params.get("start_x", 0)), int(params.get("start_y", 0)),
                int(params.get("end_x", 0)), int(params.get("end_y", 0))
            )
        elif capability == "pc_scroll":
            return await pc_controller.scroll(int(params.get("clicks", 0)))
        elif capability == "pc_clipboard_read":
            return await pc_controller.clipboard_read()
        elif capability == "pc_clipboard_write":
            return await pc_controller.clipboard_write(params.get("text", ""))
            
        return {"success": False, "verified": False, "error": f"Unknown capability {capability}"}
