import os
import subprocess
import logging
import pyautogui
import psutil
import time
from PIL import ImageGrab
from typing import Dict, Any, List

logger = logging.getLogger("nexus.pc_control")

# Safety Configuration
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5 # Add half-second delay between actions

def _create_contract(success: bool, tool: str, target: str, verification: str, execution_time: str) -> Dict[str, Any]:
    return {
        "success": success,
        "tool": tool,
        "target": target,
        "verification": verification,
        "execution_time": execution_time
    }

class PCControl:
    """
    Implements real OS control for Windows.
    All actions MUST be wrapped by the CapabilityRegistry permission checks before calling.
    """
    
    # --- APP MANAGEMENT ---
    # Dynamic App Discovery handles alias mappings now.

    async def open_app(self, app_name: str) -> Dict[str, Any]:
        import asyncio
        from rapidfuzz import fuzz, process
        from core.app_discovery import get_app_path, get_all_apps_dict
        
        start_time = time.perf_counter()
        logger.info(f"PC Control: Opening '{app_name}'")
        try:
            # 1. Clean the incoming slang
            clean_target = app_name.lower().strip()
            # Remove slang / conversational filler common in Hindi/Hinglish
            for slang in ["kro", "karo", "kar", "do", "bhai", "please", "app", "open"]:
                clean_target = clean_target.replace(slang, "")
            clean_target = clean_target.strip()
            
            if not clean_target:
                clean_target = app_name.lower().strip() # fallback if we stripped everything

            # 2. Get full DB
            app_db = await get_all_apps_dict()
            matched_key = None
            
            # 3. Exact alias match
            if clean_target in app_db:
                matched_key = clean_target
            
            # 4. RapidFuzz token_set_ratio
            if not matched_key:
                best_match = process.extractOne(
                    clean_target, 
                    app_db.keys(), 
                    scorer=fuzz.token_set_ratio, 
                    score_cutoff=60
                )
                if best_match:
                    matched_key = best_match[0]
                    logger.info(f"🎯 Nexus AI resolved approximate phrase '{app_name}' to installed app: '{matched_key}' (score: {best_match[1]})")

            if matched_key:
                target = app_db[matched_key]
            else:
                # Absolute fallback to let OS startfile try
                target = await get_app_path(clean_target)
                if not target:
                    target = app_name

            # Determine process name for verification
            if target.startswith("shell:AppsFolder"):
                proc_name = clean_target
            else:
                proc_name = os.path.basename(target).replace(".exe", "").replace(".lnk", "").lower()

            # Handle Windows URI scheme / shell:AppsFolder
            if target.endswith(":") or target.startswith("shell:AppsFolder"):
                subprocess.Popen(["cmd", "/c", "start", "", target], shell=False)
                t = f"{time.perf_counter() - start_time:.2f}s"
                return _create_contract(True, "pc_open_app", app_name, "Launched via shell URI", t)

            # Use OS startfile for absolute paths and shortcuts
            if os.path.isabs(target) or target.endswith(".lnk"):
                try:
                    os.startfile(target)
                except Exception as e:
                    subprocess.Popen(f"start \"\" \"{target}\"", shell=True)
            else:
                # Direct Popen - more reliable than `start` shell command
                try:
                    subprocess.Popen(target, shell=True)
                except FileNotFoundError:
                    # Fallback: use `start` shell dispatch (handles PATH-based apps)
                    subprocess.Popen(f"start \"\" \"{target}\"", shell=True)

            # Deep verification: poll psutil asynchronously
            verified = False
            for _ in range(7):  # 7 * 0.5s = 3.5 seconds
                await asyncio.sleep(0.5)
                # Check processes in thread to avoid blocking loop
                def _check_psutil():
                    for proc in psutil.process_iter(["name"]):
                        pname = (proc.info["name"] or "").lower()
                        if proc_name in pname:
                            return True
                    return False
                
                if await asyncio.to_thread(_check_psutil):
                    verified = True
                    break

            t = f"{time.perf_counter() - start_time:.2f}s"
            if verified:
                # Add a 1.5s artificial UI sync delay so Nexus confirmation feels synced with the app rendering
                await asyncio.sleep(1.5)
                return _create_contract(True, "pc_open_app", app_name, "PID detected", t)
            else:
                return _create_contract(True, "pc_open_app", app_name, "Process not detected (may be starting)", t)
        except Exception as e:
            t = f"{time.perf_counter() - start_time:.2f}s"
            return _create_contract(False, "pc_open_app", app_name, str(e), t)

    async def close_app(self, app_name: str) -> Dict[str, Any]:
        logger.info(f"PC Control: Closing {app_name}")
        start_time = time.perf_counter()
        try:
            import pygetwindow as gw
            import asyncio
            closed = 0
            
            clean_target = app_name.lower().strip()
            for slang in ["kro", "karo", "kar", "do", "bhai", "please", "app", "close"]:
                clean_target = clean_target.replace(slang, "")
            clean_target = clean_target.strip()
            
            # Graceful WM_CLOSE via pygetwindow
            for win in gw.getAllWindows():
                if win.title and clean_target in win.title.lower():
                    win.close()
                    closed += 1
                    
            t = f"{time.perf_counter() - start_time:.2f}s"
            if closed > 0:
                return _create_contract(True, "pc_close_app", app_name, f"Closed {closed} windows gracefully", t)
                
            # Fallback to hard process kill
            killed = 0
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] and clean_target in proc.info['name'].lower():
                    proc.kill()
                    killed += 1
            if killed > 0:
                return _create_contract(True, "pc_close_app", app_name, f"Killed {killed} processes", t)
            return _create_contract(False, "pc_close_app", app_name, "No running processes found", t)
        except Exception as e:
            t = f"{time.perf_counter() - start_time:.2f}s"
            return _create_contract(False, "pc_close_app", app_name, str(e), t)

    async def minimize_app(self, app_name: str) -> Dict[str, Any]:
        logger.info(f"PC Control: Minimizing {app_name}")
        start_time = time.perf_counter()
        try:
            import pygetwindow as gw
            clean_target = app_name.lower().strip()
            for slang in ["kro", "karo", "kar", "do", "bhai", "please", "app", "minimize"]:
                clean_target = clean_target.replace(slang, "")
            clean_target = clean_target.strip()
            
            minimized = 0
            for win in gw.getAllWindows():
                if win.title and clean_target in win.title.lower() and not win.isMinimized:
                    win.minimize()
                    minimized += 1
            t = f"{time.perf_counter() - start_time:.2f}s"
            if minimized > 0:
                return _create_contract(True, "pc_minimize_app", app_name, f"Minimized {minimized} windows", t)
            return _create_contract(False, "pc_minimize_app", app_name, "No matching windows found", t)
        except Exception as e:
            t = f"{time.perf_counter() - start_time:.2f}s"
            return _create_contract(False, "pc_minimize_app", app_name, str(e), t)

    async def maximize_app(self, app_name: str) -> Dict[str, Any]:
        logger.info(f"PC Control: Maximizing {app_name}")
        start_time = time.perf_counter()
        try:
            import pygetwindow as gw
            clean_target = app_name.lower().strip()
            for slang in ["kro", "karo", "kar", "do", "bhai", "please", "app", "maximize"]:
                clean_target = clean_target.replace(slang, "")
            clean_target = clean_target.strip()
            
            maximized = 0
            for win in gw.getAllWindows():
                if win.title and clean_target in win.title.lower():
                    win.maximize()
                    maximized += 1
            t = f"{time.perf_counter() - start_time:.2f}s"
            if maximized > 0:
                return _create_contract(True, "pc_maximize_app", app_name, f"Maximized {maximized} windows", t)
            return _create_contract(False, "pc_maximize_app", app_name, "No matching windows found", t)
        except Exception as e:
            t = f"{time.perf_counter() - start_time:.2f}s"
            return _create_contract(False, "pc_maximize_app", app_name, str(e), t)

    # --- INPUT AUTOMATION ---
    async def type_text(self, text: str) -> Dict[str, Any]:
        start_time = time.perf_counter()
        try:
            pyautogui.write(text, interval=0.01)
            t = f"{time.perf_counter() - start_time:.2f}s"
            return _create_contract(True, "pc_type_text", "Screen", f"Typed {len(text)} chars", t)
        except Exception as e:
            t = f"{time.perf_counter() - start_time:.2f}s"
            return _create_contract(False, "pc_type_text", "Screen", str(e), t)

    async def press_shortcut(self, keys: List[str]) -> Dict[str, Any]:
        start_time = time.perf_counter()
        target = "+".join(keys)
        try:
            pyautogui.hotkey(*keys)
            t = f"{time.perf_counter() - start_time:.2f}s"
            return _create_contract(True, "pc_press_shortcut", target, "Shortcut pressed", t)
        except Exception as e:
            t = f"{time.perf_counter() - start_time:.2f}s"
            return _create_contract(False, "pc_press_shortcut", target, str(e), t)

    async def move_mouse(self, x: int, y: int) -> Dict[str, Any]:
        start_time = time.perf_counter()
        target = f"({x}, {y})"
        try:
            pyautogui.moveTo(x, y, duration=0.5)
            t = f"{time.perf_counter() - start_time:.2f}s"
            return _create_contract(True, "pc_move_mouse", target, "Mouse moved", t)
        except Exception as e:
            t = f"{time.perf_counter() - start_time:.2f}s"
            return _create_contract(False, "pc_move_mouse", target, str(e), t)

    async def click(self, button: str = "left") -> Dict[str, Any]:
        start_time = time.perf_counter()
        try:
            pyautogui.click(button=button)
            t = f"{time.perf_counter() - start_time:.2f}s"
            return _create_contract(True, "pc_click", button, "Clicked", t)
        except Exception as e:
            t = f"{time.perf_counter() - start_time:.2f}s"
            return _create_contract(False, "pc_click", button, str(e), t)

    # --- SYSTEM EXTRAS ---
    async def take_screenshot(self) -> Dict[str, Any]:
        start_time = time.perf_counter()
        try:
            save_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "screenshots")
            os.makedirs(save_path, exist_ok=True)
            import uuid
            filename = f"nexus_capture_{uuid.uuid4().hex[:8]}.png"
            full_path = os.path.join(save_path, filename)
            
            img = ImageGrab.grab()
            img.save(full_path)
            
            t = f"{time.perf_counter() - start_time:.2f}s"
            # Verify file exists
            if os.path.exists(full_path):
                return _create_contract(True, "pc_take_screenshot", "Screen", f"File written: {filename}", t)
            return _create_contract(True, "pc_take_screenshot", "Screen", "File missing", t)
        except Exception as e:
            t = f"{time.perf_counter() - start_time:.2f}s"
            return _create_contract(False, "pc_take_screenshot", "Screen", str(e), t)

pc_controller = PCControl()
