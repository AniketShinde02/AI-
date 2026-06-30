import os
import subprocess
import logging
import pyautogui
import psutil
import time
import random
from PIL import ImageGrab
from typing import Dict, Any, List, Optional, Tuple
from rapidfuzz import fuzz, process
logger = logging.getLogger("nexus.pc_control")

def _get_dpi_and_resolution() -> Tuple[int, int, float]:
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2) # PROCESS_PER_MONITOR_DPI_AWARE
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    
    try:
        user32 = ctypes.windll.user32
        # SM_CXVIRTUALSCREEN = 78, SM_CYVIRTUALSCREEN = 79
        w = user32.GetSystemMetrics(78)
        h = user32.GetSystemMetrics(79)
        
        # Fallback if virtual screen fails
        if w == 0 or h == 0:
            w = user32.GetSystemMetrics(0) # SM_CXSCREEN
            h = user32.GetSystemMetrics(1) # SM_CYSCREEN
            
        hdc = user32.GetDC(0)
        gdc = ctypes.windll.gdi32.GetDeviceCaps
        logical_dpi = 96
        physical_dpi = gdc(hdc, 88) # LOGPIXELSX = 88
        user32.ReleaseDC(0, hdc)
        
        dpr = physical_dpi / logical_dpi
        return w, h, dpr
    except Exception:
        return 1920, 1080, 1.0

def _bezier_curve(x1: int, y1: int, x2: int, y2: int, steps: int = 20) -> List[Tuple[int, int]]:
    dx = x2 - x1
    dy = y2 - y1
    
    ctrl_x1 = x1 + dx * random.uniform(0.1, 0.4)
    ctrl_y1 = y1 + dy * random.uniform(-0.2, 0.5)
    
    ctrl_x2 = x1 + dx * random.uniform(0.6, 0.9)
    ctrl_y2 = y1 + dy * random.uniform(0.5, 1.2)
    
    points = []
    for i in range(steps + 1):
        t = i / steps
        t_ease = t * t * (3 - 2 * t)
        
        x = (1 - t_ease)**3 * x1 + 3 * (1 - t_ease)**2 * t_ease * ctrl_x1 + 3 * (1 - t_ease) * t_ease**2 * ctrl_x2 + t_ease**3 * x2
        y = (1 - t_ease)**3 * y1 + 3 * (1 - t_ease)**2 * t_ease * ctrl_y1 + 3 * (1 - t_ease) * t_ease**2 * ctrl_y2 + t_ease**3 * y2
        points.append((int(x), int(y)))
    return points

# Safety Configuration
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5 # Add half-second delay between actions

def _create_contract(success: bool, tool: str, target: str, verification: str, execution_time: str) -> Dict[str, Any]:
    return {
        "success": success,
        "verified": success,          # verified = same as success for all PC tools
        "tool": tool,
        "target": target,
        "result": verification,       # execution_hooks expects 'result' key
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

    async def open_app(self, app_name: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        import asyncio
        from core.app_discovery import get_app_path, get_all_apps_dict, resolve_system_role
        from core.guardrails import guardrails
        
        start_time = time.perf_counter()
        logger.info(f"PC Control: Opening '{app_name}' (session: {session_id})")

        # Scan target for safety guardrails
        classification, reason = guardrails.scan_command(app_name)
        if classification == "BLOCKED":
            logger.warning(f"🛡️ [Guardrails] BLOCKED execution: '{app_name}'. Reason: {reason}")
            return _create_contract(False, "pc_open_app", app_name, f"Blocked: {reason}", "0.00s")
            
        if classification == "RESTRICTED" and session_id:
            approved = await guardrails.request_authorization(session_id, app_name)
            if not approved:
                logger.warning(f"🛡️ [Guardrails] RESTRICTED execution Denied by User: '{app_name}'")
                return _create_contract(False, "pc_open_app", app_name, "Access Denied by Admin", "0.00s")
        try:
            # 0. Check semantic system roles mapping first
            system_target = resolve_system_role(app_name)
            if system_target:
                logger.info(f"🎯 Resolved system role '{app_name}' to system default: '{system_target}'")
                target = system_target
                clean_target = system_target.replace(".exe", "")
            else:
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
                    logger.warning(f"os.startfile failed for {target}: {e}. Retrying via shell.")
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

    async def close_app(self, app_name: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        logger.info(f"PC Control: Closing {app_name}")
        start_time = time.perf_counter()
        try:
            import pygetwindow as gw
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

    async def minimize_app(self, app_name: str, session_id: Optional[str] = None) -> Dict[str, Any]:
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

    async def maximize_app(self, app_name: str, session_id: Optional[str] = None) -> Dict[str, Any]:
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

    async def file_explorer(self, target_path: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        logger.info(f"PC Control: Opening File Explorer at {target_path}")
        start_time = time.perf_counter()
        try:
            target = target_path.strip()
            if not target:
                target = "shell:MyComputerFolder" # default
            subprocess.Popen(f'explorer "{target}"')
            t = f"{time.perf_counter() - start_time:.2f}s"
            return _create_contract(True, "pc_file_explorer", target, "File Explorer opened", t)
        except Exception as e:
            t = f"{time.perf_counter() - start_time:.2f}s"
            return _create_contract(False, "pc_file_explorer", target_path, str(e), t)

    # --- COORDINATE TRANSLATION ---
    def scale_coords(self, x: int, y: int) -> Tuple[int, int]:
        """
        Translates normalized task-card coordinates (1280 x 720) into the actual
        logical screen coordinates required by PyAutoGUI, accounting for monitor aspect ratio.
        """
        w, h, dpr = _get_dpi_and_resolution()
        # Scale 1280x720 canvas coordinates directly to logical display resolution
        scaled_x = int((x / 1280.0) * w)
        scaled_y = int((y / 720.0) * h)
        return scaled_x, scaled_y

    # --- INPUT AUTOMATION ---
    async def type_text(self, text: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.perf_counter()
        try:
            for char in text:
                pyautogui.write(char)
                # Introduce typing jitter delay between 30ms and 120ms per character
                time.sleep(random.uniform(0.03, 0.12))
            t = f"{time.perf_counter() - start_time:.2f}s"
            return _create_contract(True, "pc_type_text", "Screen", f"Typed {len(text)} chars", t)
        except Exception as e:
            t = f"{time.perf_counter() - start_time:.2f}s"
            return _create_contract(False, "pc_type_text", "Screen", str(e), t)

    async def press_shortcut(self, keys: List[str], session_id: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.perf_counter()
        target = "+".join(keys)
        try:
            pyautogui.hotkey(*keys)
            t = f"{time.perf_counter() - start_time:.2f}s"
            return _create_contract(True, "pc_press_shortcut", target, "Shortcut pressed", t)
        except Exception as e:
            t = f"{time.perf_counter() - start_time:.2f}s"
            return _create_contract(False, "pc_press_shortcut", target, str(e), t)

    async def move_mouse(self, x: int, y: int, session_id: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.perf_counter()
        target = f"({x}, {y})"
        try:
            # 1. High-DPI coordinate scaling translation
            scaled_x, scaled_y = self.scale_coords(x, y)
            
            # 2. Add target sub-pixel jitter (Gaussian noise perturbation)
            jitter_x = int(random.gauss(0, 0.5))
            jitter_y = int(random.gauss(0, 0.5))
            
            w, h, _ = _get_dpi_and_resolution()
            target_x = max(0, min(w - 1, scaled_x + jitter_x))
            target_y = max(0, min(h - 1, scaled_y + jitter_y))
            
            start_x, start_y = pyautogui.position()
            
            if start_x != target_x or start_y != target_y:
                # 3. Cubic Bezier curve mouse movement tracking
                distance = ((target_x - start_x)**2 + (target_y - start_y)**2)**0.5
                steps = max(10, min(40, int(distance / 15)))
                points = _bezier_curve(start_x, start_y, target_x, target_y, steps=steps)
                
                for px, py in points:
                    pyautogui.moveTo(px, py)
                    # Humanized movement delay per step (5ms - 15ms)
                    time.sleep(random.uniform(0.005, 0.015))
                    
            t = f"{time.perf_counter() - start_time:.2f}s"
            return _create_contract(True, "pc_move_mouse", target, "Mouse moved", t)
        except Exception as e:
            t = f"{time.perf_counter() - start_time:.2f}s"
            return _create_contract(False, "pc_move_mouse", target, str(e), t)

    async def click(self, x: Optional[int] = None, y: Optional[int] = None, button: str = "left", double: bool = False, session_id: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.perf_counter()
        target = f"{button} click"
        try:
            if x is not None and y is not None:
                await self.move_mouse(x, y, session_id=session_id)
                target += f" at ({x}, {y})"
            
            if double:
                pyautogui.doubleClick(button=button)
                target = "Double " + target
            else:
                pyautogui.click(button=button)
                
            t = f"{time.perf_counter() - start_time:.2f}s"
            return _create_contract(True, "pc_click", target, "Clicked", t)
        except Exception as e:
            t = f"{time.perf_counter() - start_time:.2f}s"
            return _create_contract(False, "pc_click", target, str(e), t)

    async def drag(self, x1: int, y1: int, x2: int, y2: int, session_id: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.perf_counter()
        target = f"drag from ({x1}, {y1}) to ({x2}, {y2})"
        try:
            await self.move_mouse(x1, y1, session_id=session_id)
            pyautogui.mouseDown(button="left")
            
            scaled_x2, scaled_y2 = self.scale_coords(x2, y2)
            jitter_x = int(random.gauss(0, 0.5))
            jitter_y = int(random.gauss(0, 0.5))
            
            w, h, _ = _get_dpi_and_resolution()
            target_x2 = max(0, min(w - 1, scaled_x2 + jitter_x))
            target_y2 = max(0, min(h - 1, scaled_y2 + jitter_y))
            
            start_x, start_y = pyautogui.position()
            
            if start_x != target_x2 or start_y != target_y2:
                distance = ((target_x2 - start_x)**2 + (target_y2 - start_y)**2)**0.5
                steps = max(10, min(40, int(distance / 15)))
                points = _bezier_curve(start_x, start_y, target_x2, target_y2, steps=steps)
                
                for px, py in points:
                    pyautogui.moveTo(px, py)
                    # Humanized drag movement delay per step (8ms - 18ms)
                    time.sleep(random.uniform(0.008, 0.018))
                    
            pyautogui.mouseUp(button="left")
            t = f"{time.perf_counter() - start_time:.2f}s"
            return _create_contract(True, "pc_drag", target, "Dragged", t)
        except Exception as e:
            try:
                pyautogui.mouseUp(button="left")
            except Exception:
                pass
            t = f"{time.perf_counter() - start_time:.2f}s"
            return _create_contract(False, "pc_drag", target, str(e), t)

    async def scroll(self, clicks: int, session_id: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.perf_counter()
        target = f"scroll {clicks} ticks"
        try:
            step = 1 if clicks > 0 else -1
            abs_clicks = abs(clicks)
            for _ in range(abs_clicks):
                pyautogui.scroll(step * 100)
                # Introduce randomized micro-delays between scroll ticks
                time.sleep(random.uniform(0.02, 0.08))
            t = f"{time.perf_counter() - start_time:.2f}s"
            return _create_contract(True, "pc_scroll", target, "Scrolled", t)
        except Exception as e:
            t = f"{time.perf_counter() - start_time:.2f}s"
            return _create_contract(False, "pc_scroll", target, str(e), t)

    # --- WINDOW FOCUS & SWITCHING ---

    async def focus_app(self, app_name: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Bring a running application window to the foreground."""
        import asyncio
        start_time = time.perf_counter()
        logger.info(f"PC Control: Focusing '{app_name}'")
        try:
            import pygetwindow as gw
            clean = app_name.lower().strip()
            for slang in ["kro", "karo", "kar", "do", "bhai", "please", "app", "open", "focus", "switch"]:
                clean = clean.replace(slang, "").strip()

            # Collect candidate windows
            all_windows = gw.getAllWindows()
            candidates = [w for w in all_windows if w.title and clean in w.title.lower()]

            if not candidates:
                # RapidFuzz fallback on window titles
                titles = [w.title for w in all_windows if w.title]
                best = process.extractOne(clean, titles, scorer=fuzz.token_set_ratio, score_cutoff=55)
                if best:
                    candidates = [w for w in all_windows if w.title == best[0]]

            if not candidates:
                t = f"{time.perf_counter() - start_time:.2f}s"
                return _create_contract(False, "pc_focus_app", app_name, "No matching window found", t)

            win = candidates[0]
            # Restore if minimized first, then activate
            if win.isMinimized:
                win.restore()
                await asyncio.sleep(0.3)

            # Use win32gui for reliable foreground placement on Windows
            try:
                import ctypes
                hwnd = win._hWnd
                ctypes.windll.user32.ShowWindow(hwnd, 9)   # SW_RESTORE
                ctypes.windll.user32.SetForegroundWindow(hwnd)
                ctypes.windll.user32.BringWindowToTop(hwnd)
            except Exception:
                win.activate()  # pygetwindow fallback

            await asyncio.sleep(0.4)
            t = f"{time.perf_counter() - start_time:.2f}s"
            return _create_contract(True, "pc_focus_app", app_name, f"Focused: '{win.title}'", t)

        except Exception as e:
            t = f"{time.perf_counter() - start_time:.2f}s"
            return _create_contract(False, "pc_focus_app", app_name, str(e), t)

    async def switch_window(self, app_name: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Switch to a specific app window, or cycle through windows with Alt+Tab
        if no app_name is given.
        """
        start_time = time.perf_counter()
        logger.info(f"PC Control: Switching window to '{app_name}'")

        if not app_name or app_name.strip().lower() in ("next", "switch", ""):
            # Cycle via Alt+Tab
            try:
                pyautogui.hotkey("alt", "tab")
                t = f"{time.perf_counter() - start_time:.2f}s"
                return _create_contract(True, "pc_switch_window", "Next window", "Alt+Tab sent", t)
            except Exception as e:
                t = f"{time.perf_counter() - start_time:.2f}s"
                return _create_contract(False, "pc_switch_window", "Next window", str(e), t)

        # Named target → delegate to focus_app
        return await self.focus_app(app_name, session_id=session_id)

    # --- CLIPBOARD ---

    async def clipboard_read(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Read the current contents of the system clipboard with session bridge persistence fallback."""
        start_time = time.perf_counter()
        text = ""
        try:
            import pyperclip
            text = pyperclip.paste() or ""
        except Exception as system_err:
            logger.warning(f"Failed to read from system clipboard: {system_err}")

        # Session bridge sync/persistence fallback
        if session_id:
            import core.global_state as gs
            session = gs.active_sessions.get(session_id)
            if session:
                if not text:
                    text = session.shared_context.get("clipboard", "")
                else:
                    session.shared_context["clipboard"] = text

        t = f"{time.perf_counter() - start_time:.2f}s"
        preview = text[:100].replace("\n", " ") if text else ""
        return _create_contract(True, "pc_clipboard_read", "Clipboard", f"Read {len(text)} chars: {preview}", t)

    async def clipboard_write(self, text: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Write text to the system clipboard and persist it in the session memory bridge."""
        start_time = time.perf_counter()
        success = False
        status = ""
        try:
            import pyperclip
            pyperclip.copy(text)
            readback = pyperclip.paste()
            success = readback == text
            status = "Written and verified" if success else "Written (verification mismatch)"
        except Exception as e:
            status = f"System clipboard write failed: {e}"
            logger.warning(status)

        # Session bridge sync/persistence persistence
        if session_id:
            import core.global_state as gs
            session = gs.active_sessions.get(session_id)
            if session:
                session.shared_context["clipboard"] = text
                if not success:
                    success = True
                    status = "Written to session clipboard bridge"

        t = f"{time.perf_counter() - start_time:.2f}s"
        return _create_contract(success, "pc_clipboard_write", "Clipboard", status, t)

    # --- SYSTEM EXTRAS ---
    async def take_screenshot(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.perf_counter()
        try:
            save_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "screenshots")
            os.makedirs(save_path, exist_ok=True)
            import uuid
            import base64
            from io import BytesIO
            
            filename = f"nexus_capture_{uuid.uuid4().hex[:8]}.png"
            full_path = os.path.join(save_path, filename)
            
            img = ImageGrab.grab(all_screens=True)
            img.save(full_path)
            
            buffered = BytesIO()
            img.convert('RGB').save(buffered, format="JPEG", quality=85)
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            # Send to Vision pipeline
            try:
                from core.vision_parser import vision_parser
                analysis = await vision_parser.analyze_screenshot(
                    img_str, 
                    prompt="Describe the screen concisely. What applications are open? What is currently visible?",
                    use_som=False
                )
            except Exception as e:
                analysis = f"Vision failed: {e}"
            
            t = f"{time.perf_counter() - start_time:.2f}s"
            # Verify file exists
            if os.path.exists(full_path):
                return _create_contract(True, "pc_take_screenshot", "Screen", f"Saved: {filename} | Vision: {analysis}", t)
            return _create_contract(True, "pc_take_screenshot", "Screen", "File missing", t)
        except Exception as e:
            t = f"{time.perf_counter() - start_time:.2f}s"
            return _create_contract(False, "pc_take_screenshot", "Screen", str(e), t)

    async def analyze_screen(self, query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.perf_counter()
        try:
            save_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "screenshots")
            os.makedirs(save_path, exist_ok=True)
            import uuid
            import base64
            from io import BytesIO
            
            filename = f"nexus_capture_{uuid.uuid4().hex[:8]}.png"
            full_path = os.path.join(save_path, filename)
            
            img = ImageGrab.grab(all_screens=True)
            img.save(full_path)
            
            buffered = BytesIO()
            img.convert('RGB').save(buffered, format="JPEG", quality=85)
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            # Send to Vision pipeline with dynamic query
            try:
                from core.vision_parser import vision_parser
                analysis = await vision_parser.analyze_screenshot(img_str, prompt=query, use_som=False)
            except Exception as e:
                analysis = f"Vision failed: {e}"
            
            t = f"{time.perf_counter() - start_time:.2f}s"
            return _create_contract(True, "vision_analyze_screen", query, analysis, t)
        except Exception as e:
            t = f"{time.perf_counter() - start_time:.2f}s"
            return _create_contract(False, "vision_analyze_screen", query, str(e), t)

pc_controller = PCControl()
