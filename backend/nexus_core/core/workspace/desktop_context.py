"""
desktop_context.py
==================
Collects desktop / OS state with TTL-cached queries.

Cache TTLs:
  - Active window: 2.0s  (changes frequently, fast to query)
  - Process list:  10.0s (expensive psutil.process_iter)
  - Monitor info:  60.0s (almost never changes)

Design rules:
  - NEVER import from voice_session.py or execution_hooks.py (circular)
  - All methods are async-safe (blocking ctypes wrapped in asyncio.to_thread)
  - Failures return safe defaults, never raise
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional, Tuple

from core.workspace.workspace_state import DesktopState

logger = logging.getLogger("nexus.workspace.desktop")

# ---------------------------------------------------------------------------
# TTL constants
# ---------------------------------------------------------------------------
_TTL_WINDOW = 2.0
_TTL_MONITOR = 60.0


class DesktopContext:
    """
    Gathers desktop state.  Consumed only by WorkspaceManager.
    """

    def __init__(self) -> None:
        self._window_cache: Optional[DesktopState] = None
        self._window_ts: float = 0.0
        self._monitor_cache: Optional[Tuple[int, int, int]] = None  # (w, h, count)
        self._monitor_ts: float = 0.0

    # ------------------------------------------------------------------
    # Public collect
    # ------------------------------------------------------------------

    async def collect(self) -> DesktopState:
        now = time.monotonic()
        # Fast path — full cache hit
        if self._window_cache and (now - self._window_ts) < _TTL_WINDOW:
            return self._window_cache

        window_title, app_name, pid = await self._get_active_window()
        w, h, count = await self._get_monitor_info()

        state = DesktopState(
            active_window=window_title,
            active_app=app_name,
            pid=pid,
            monitor_count=count,
            screen_width=w,
            screen_height=h,
            clipboard=None,   # Only on explicit request
        )
        self._window_cache = state
        self._window_ts = now
        return state

    async def get_clipboard(self) -> Optional[str]:
        """Called explicitly (on voice command), NOT polled."""
        return await asyncio.to_thread(self._read_clipboard_sync)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_active_window(self) -> Tuple[str, str, Optional[int]]:
        return await asyncio.to_thread(self._get_active_window_sync)

    def _get_active_window_sync(self) -> Tuple[str, str, Optional[int]]:
        try:
            import pygetwindow as gw
            win = gw.getActiveWindow()
            if win:
                title = win.title or ""
                # Derive app name from title (best effort)
                app = title.split(" - ")[-1] if " - " in title else title
                return title, app, None
        except Exception as e:
            logger.debug(f"Active window query failed: {e}")
        return "", "", None

    async def _get_monitor_info(self) -> Tuple[int, int, int]:
        now = time.monotonic()
        if self._monitor_cache and (now - self._monitor_ts) < _TTL_MONITOR:
            return self._monitor_cache
        result = await asyncio.to_thread(self._get_monitor_info_sync)
        self._monitor_cache = result
        self._monitor_ts = now
        return result

    def _get_monitor_info_sync(self) -> Tuple[int, int, int]:
        try:
            import ctypes
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                pass
            user32 = ctypes.windll.user32
            w = user32.GetSystemMetrics(78)   # SM_CXVIRTUALSCREEN
            h = user32.GetSystemMetrics(79)   # SM_CYVIRTUALSCREEN
            if w == 0 or h == 0:
                w = user32.GetSystemMetrics(0)
                h = user32.GetSystemMetrics(1)
            # Count monitors
            monitors = []
            def _cb(hMonitor, hdcMonitor, lprcMonitor, dwData):
                monitors.append(hMonitor)
                return 1
            MonitorEnumProc = ctypes.WINFUNCTYPE(
                ctypes.c_bool, ctypes.POINTER(ctypes.c_ulong),
                ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_long), ctypes.POINTER(ctypes.c_long)
            )
            ctypes.windll.user32.EnumDisplayMonitors(None, None, MonitorEnumProc(_cb), 0)
            return w, h, max(1, len(monitors))
        except Exception as e:
            logger.debug(f"Monitor info query failed: {e}")
        return 1920, 1080, 1

    def _read_clipboard_sync(self) -> Optional[str]:
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                    data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                    return str(data)[:500]  # Truncate large clipboard data
            finally:
                win32clipboard.CloseClipboard()
        except ImportError:
            # win32clipboard not available, try pyperclip fallback
            try:
                import subprocess
                result = subprocess.run(
                    ["powershell", "-command", "Get-Clipboard"],
                    capture_output=True, text=True, timeout=2
                )
                return result.stdout.strip()[:500] if result.stdout else None
            except Exception:
                pass
        except Exception as e:
            logger.debug(f"Clipboard read failed: {e}")
        return None
