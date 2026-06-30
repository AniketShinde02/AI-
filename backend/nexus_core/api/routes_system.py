"""
routes_system.py
----------------
Responsibility: OS-level REST endpoints (mouse, keyboard, window, screenshot, tool executor).
Extracted from rest_routes.py to isolate system-automation concerns.
"""
import asyncio
import base64
import io
import json
import logging
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import core.rag_oracle as rag_oracle_module
from core.planner.executor import get_executor

try:
    from PIL import ImageGrab
except ImportError:
    ImageGrab = None

try:
    import pyautogui
except ImportError:
    pyautogui = None

try:
    import pygetwindow as gw
except ImportError:
    gw = None

logger = logging.getLogger("nexus_ws")
system_router = APIRouter()


# ------------------------------------------------------------------
# Pydantic schemas
# ------------------------------------------------------------------

class MouseMove(BaseModel):
    x: int
    y: int

class MouseClick(BaseModel):
    button: str = "left"

class KeyboardType(BaseModel):
    text: str

class KeyboardPress(BaseModel):
    keys: list

class WindowFocus(BaseModel):
    title: str


# ------------------------------------------------------------------
# Mouse
# ------------------------------------------------------------------

@system_router.post("/mouse/move")
async def move_mouse(req: MouseMove):
    if not pyautogui:
        raise HTTPException(status_code=501, detail="pyautogui not installed")
    await asyncio.to_thread(pyautogui.moveTo, req.x, req.y, duration=0.2)
    return {"status": "success", "action": "mouse_move", "x": req.x, "y": req.y}

@system_router.post("/mouse/click")
async def click_mouse(req: MouseClick):
    if not pyautogui:
        raise HTTPException(status_code=501, detail="pyautogui not installed")
    await asyncio.to_thread(pyautogui.click, button=req.button)
    return {"status": "success", "action": "mouse_click", "button": req.button}


# ------------------------------------------------------------------
# Keyboard
# ------------------------------------------------------------------

@system_router.post("/keyboard/type")
async def type_keyboard(req: KeyboardType):
    if not pyautogui:
        raise HTTPException(status_code=501, detail="pyautogui not installed")
    await asyncio.to_thread(pyautogui.write, req.text, interval=0.01)
    return {"status": "success", "action": "keyboard_type"}

@system_router.post("/keyboard/press")
async def press_keyboard(req: KeyboardPress):
    if not pyautogui:
        raise HTTPException(status_code=501, detail="pyautogui not installed")
    await asyncio.to_thread(pyautogui.hotkey, *req.keys)
    return {"status": "success", "action": "keyboard_press", "keys": req.keys}


# ------------------------------------------------------------------
# Window management
# ------------------------------------------------------------------

@system_router.get("/window/list")
async def list_windows():
    if not gw:
        raise HTTPException(status_code=501, detail="pygetwindow not installed")
    def _get_titles():
        return [t for t in gw.getAllTitles() if t.strip()]  # type: ignore
    titles = await asyncio.to_thread(_get_titles)
    return {"windows": titles}

@system_router.post("/window/focus")
async def focus_window(req: WindowFocus):
    if not gw:
        raise HTTPException(status_code=501, detail="pygetwindow not installed")
    def _focus():
        win = gw.getWindowsWithTitle(req.title)  # type: ignore
        if not win:
            raise Exception("Window not found")
        win[0].activate()
    try:
        await asyncio.to_thread(_focus)
        return {"status": "success", "window": req.title}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------
# Screenshot
# ------------------------------------------------------------------

@system_router.get("/screenshot")
async def take_screenshot():
    if not ImageGrab:
        raise HTTPException(status_code=501, detail="Pillow ImageGrab not installed")
    def _grab():
        screenshot = ImageGrab.grab()
        screenshot.thumbnail((1280, 720))
        buffer = io.BytesIO()
        screenshot.save(buffer, format="JPEG", quality=70)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    try:
        img_str = await asyncio.to_thread(_grab)
        return {"status": "success", "image_base64": img_str}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------
# Gemini Live tool executor
# ------------------------------------------------------------------

@system_router.post("/execute-tool")
async def execute_tool(request: dict):
    """
    Handle tool execution requests forwarded from the Gemini Live frontend.
    Routes to the central tool registry based on function name.
    """
    try:
        function_calls = request.get("functionCalls", [])
        results = []
        for call in function_calls:
            name = call.get("name")
            args = call.get("args", {})
            logger.info(f"🛠️ Executing tool: {name} with args: {args}")

            executor = get_executor(name)
            if executor:
                is_desktop = name.startswith("pc_")
                out = await executor.run(name, args, max_retries=1, visual_verification=is_desktop)
                results.append({"action": name, "output": out})
            else:
                results.append({"status": "unknown_tool", "tool": name})

        return {"status": "success", "results": results}
    except Exception as e:
        logger.exception(f"❌ Tool Execution failed: {e}")
        return {"status": "error", "error": str(e)}
