import os
import subprocess
import logging
import pyautogui
import psutil
from PIL import ImageGrab
from typing import Dict, Any, List

logger = logging.getLogger("nexus.pc_control")

# Safety Configuration
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5 # Add half-second delay between actions

class PCControl:
    """
    Implements real OS control for Windows.
    All actions MUST be wrapped by the CapabilityRegistry permission checks before calling.
    """
    
    # --- APP MANAGEMENT ---
    async def open_app(self, app_name: str) -> Dict[str, Any]:
        logger.info(f"PC Control: Opening {app_name}")
        try:
            # Simple start command for Windows
            aliases = {
                "browser": "msedge",
                "chrome": "chrome",
                "edge": "msedge",
                "code": "code",
                "vscode": "code",
                "notepad": "notepad",
                "calculator": "calc",
                "calc": "calc",
                "explorer": "explorer",
                "terminal": "wt"
            }
            target = aliases.get(app_name.lower(), app_name)
            subprocess.Popen(f"start {target}", shell=True)
            return {"success": True, "message": f"Launched {target}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def close_app(self, app_name: str) -> Dict[str, Any]:
        logger.info(f"PC Control: Closing {app_name}")
        try:
            killed = 0
            for proc in psutil.process_iter(['pid', 'name']):
                if app_name.lower() in proc.info['name'].lower():
                    proc.kill()
                    killed += 1
            if killed > 0:
                return {"success": True, "message": f"Killed {killed} processes matching {app_name}"}
            return {"success": False, "error": f"No process found matching {app_name}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- INPUT AUTOMATION ---
    async def type_text(self, text: str) -> Dict[str, Any]:
        try:
            pyautogui.write(text, interval=0.01)
            return {"success": True, "message": f"Typed text ({len(text)} chars)"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def press_shortcut(self, keys: List[str]) -> Dict[str, Any]:
        try:
            pyautogui.hotkey(*keys)
            return {"success": True, "message": f"Pressed shortcut: {'+'.join(keys)}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def move_mouse(self, x: int, y: int) -> Dict[str, Any]:
        try:
            pyautogui.moveTo(x, y, duration=0.5)
            return {"success": True, "message": f"Moved mouse to ({x}, {y})"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def click(self, button: str = "left") -> Dict[str, Any]:
        try:
            pyautogui.click(button=button)
            return {"success": True, "message": f"Clicked {button} mouse button"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- SYSTEM EXTRAS ---
    async def take_screenshot(self) -> Dict[str, Any]:
        try:
            save_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "screenshots")
            os.makedirs(save_path, exist_ok=True)
            import uuid
            filename = f"nexus_capture_{uuid.uuid4().hex[:8]}.png"
            full_path = os.path.join(save_path, filename)
            
            img = ImageGrab.grab()
            img.save(full_path)
            return {"success": True, "path": full_path, "message": "Screenshot saved successfully."}
        except Exception as e:
            return {"success": False, "error": str(e)}

pc_controller = PCControl()
