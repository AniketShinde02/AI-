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
from tools.system import execute_pc_action
from core.execution_hooks import wrap_execution, run_desktop_tool, run_file_tool, run_memory_tool
from tools.task_tools import create_task, create_note
from tools.memory_tools import update_preferences, get_user_memory, delete_user_preference
from tools.file_tools import read_file, write_file, read_directory
from tools.third_party_tools import get_weather

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

            if name == "search_web":
                sim_res = {"success": True, "verified": True, "result": "Nexus search results dummy payload."}
                out = await wrap_execution(name, args.get("query", ""), asyncio.sleep(0.001, result=sim_res), category="other")
                results.append({
                    "query": args.get("query"),
                    "status": "simulated_success",
                    "snippet": "Nexus search results dummy payload.",
                    "output": out
                })
            elif name in ["pc_open_app", "pc_close_app", "pc_type_text", "pc_press_shortcut", "pc_take_screenshot"]:
                out = await run_desktop_tool(name, args.get("app_name", args.get("target", "")), execute_pc_action(name, args))
                results.append({"action": name, "output": out})
            elif name == "create_task":
                out = await wrap_execution(name, args.get("title", ""), create_task(args.get("title", ""), args.get("priority", "medium"), args.get("due_date")), category="other")
                results.append({"title": args.get("title"), "output": out})
            elif name == "create_note":
                out = await wrap_execution(name, args.get("title", ""), create_note(args.get("title", ""), args.get("content", "")), category="other")
                results.append({"title": args.get("title"), "output": out})
            elif name == "update_preferences":
                out = await run_memory_tool(name, str(args.get("preferences", "")), update_preferences(args.get("preferences", {})))
                results.append({"preferences": args.get("preferences"), "output": out})
            elif name == "get_user_memory":
                out = await run_memory_tool(name, "", get_user_memory())
                results.append({"output": out})
            elif name == "delete_user_preference":
                out = await run_memory_tool(name, f"{args.get('category')}:{args.get('key')}", delete_user_preference(args.get("category", ""), args.get("key", "")))
                results.append({"category": args.get("category"), "key": args.get("key"), "output": out})
            elif name == "read_file":
                out = await run_file_tool(name, args.get("file_path", ""), read_file(args.get("file_path", "")))
                results.append({"file_path": args.get("file_path"), "output": out})
            elif name == "write_file":
                out = await run_file_tool(name, args.get("file_name", ""), write_file(args.get("file_name", ""), args.get("content", "")))
                results.append({"file_name": args.get("file_name"), "output": out})
            elif name == "read_directory":
                out = await run_file_tool(name, args.get("directory_path", ""), read_directory(args.get("directory_path", "")))
                results.append({"directory_path": args.get("directory_path"), "output": out})
            elif name == "get_weather":
                out = await wrap_execution(name, args.get("city", ""), get_weather(args.get("city", "")), category="other")
                results.append({"city": args.get("city"), "output": out})
            elif name == "ingest_codebase":
                if rag_oracle_module.oracle_instance:
                    out = await wrap_execution(name, args.get("dir_path", ""), rag_oracle_module.oracle_instance.ingest_codebase(args.get("dir_path", "")), category="other")
                    results.append({"dir_path": args.get("dir_path"), "output": out})
                else:
                    results.append({"error": "RAG Oracle not initialized"})
            elif name == "consult_oracle":
                if rag_oracle_module.oracle_instance:
                    out = await wrap_execution(name, args.get("query", ""), rag_oracle_module.oracle_instance.consult_oracle(args.get("query", "")), category="other")
                    results.append({"query": args.get("query"), "output": out})
                else:
                    results.append({"error": "RAG Oracle not initialized"})
            else:
                results.append({"status": "unknown_tool"})

        return {"status": "success", "results": results}
    except Exception as e:
        logger.exception(f"❌ Tool Execution failed: {e}")
        return {"status": "error", "error": str(e)}
