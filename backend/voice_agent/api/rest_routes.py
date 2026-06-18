from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import shutil
import uuid
import logging
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from core.database import db
from core.theme_generator import generate_theme_from_image
import core.global_state as gs
import core.rag_oracle as rag_oracle_module
import asyncio
import base64
import io

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

from tools.system import execute_pc_action
from tools.task_tools import create_task, create_note
from tools.memory_tools import update_preferences, get_user_memory, delete_user_preference
from tools.file_tools import read_file, write_file, read_directory
from tools.third_party_tools import get_weather

logger = logging.getLogger("nexus_ws")
rest_router = APIRouter()

BACKGROUNDS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "themes", "backgrounds")
os.makedirs(BACKGROUNDS_DIR, exist_ok=True)

@rest_router.post("/api/theme/generate")
async def generate_theme(image: UploadFile = File(...)):
    """
    Receives an image, saves it, and asks Gemini Vision to extract a dark-mode theme.
    """
    try:
        # Save the uploaded image
        ext = os.path.splitext(image.filename or ".png")[1]
        filename = f"bg_{uuid.uuid4().hex[:8]}{ext}"
        filepath = os.path.join(BACKGROUNDS_DIR, filename)
        
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
            
        # Get GEMINI_API_KEY from environment
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return {"success": False, "error": "GEMINI_API_KEY not found in backend environment"}
            
        # Call Gemini Vision to generate theme
        theme_json = await generate_theme_from_image(filepath, api_key)
        
        return {
            "success": True,
            "background_url": f"http://localhost:8001/backgrounds/{filename}",
            "theme": theme_json
        }
    except Exception as e:
        logger.error(f"Theme generation failed: {e}")
        return {"success": False, "error": str(e)}



@rest_router.get("/")
async def root():
    """Health check — stops browser probe 404 log noise."""
    return {"status": "ok", "service": "Nexus Voice Backend", "version": "1.0.0"}

@rest_router.get("/health")
async def health_check():
    """Explicit health endpoint for monitoring."""
    return {"status": "ok", "providers": {
        "stt": gs.stt_provider is not None,
        "llm": gs.llm_provider is not None,
        "tts": gs.tts_router is not None,
        "vad": gs.vad_model is not None,
    }}

from typing import List, Dict, Any

@rest_router.get("/memory")
async def get_memory_api():
    """Returns the long-term persistent user memory."""
    return await db.get_all_memory()

@rest_router.delete("/memory/{category}/{key}")
async def delete_memory_api(category: str, key: str):
    """Deletes a specific memory entry."""
    await db.delete_memory(category, key)
    return {"status": "success"}

# --- Agent API ---
class AgentSchema(BaseModel):
    id: str
    name: str
    status: str = "idle"
    description: str = ""
    color: str = "#00FFFF"
    runtime: str = "0.0s"
    calls: int = 0

@rest_router.get("/api/agents")
async def get_agents():
    """Returns all available sub-agents."""
    return await db.get_agents()

@rest_router.post("/api/agents")
async def create_agent(agent: AgentSchema):
    """Creates a new sub-agent."""
    await db.create_agent(agent.model_dump())
    return {"status": "success", "agent_id": agent.id}

@rest_router.put("/api/agents/{agent_id}")
async def update_agent(agent_id: str, agent: AgentSchema):
    """Updates an existing sub-agent."""
    await db.update_agent(agent_id, agent.model_dump())
    return {"status": "success"}

@rest_router.delete("/api/agents/{agent_id}")
async def delete_agent(agent_id: str):
    """Deletes a sub-agent."""
    await db.delete_agent(agent_id)
    return {"status": "success"}

# --- Workflow API ---
from typing import List

class WorkflowSchema(BaseModel):
    id: str
    name: str
    trigger: str
    actions: List[str]
    status: str = "draft"
    runs: int = 0
    lastRun: str = "Never"

@rest_router.get("/api/workflows")
async def get_workflows():
    """Returns all available workflows."""
    return await db.get_workflows()

@rest_router.post("/api/workflows")
async def create_workflow(workflow: WorkflowSchema):
    """Creates a new workflow."""
    await db.create_workflow(workflow.model_dump())
    return {"status": "success", "workflow_id": workflow.id}

@rest_router.put("/api/workflows/{workflow_id}")
async def update_workflow(workflow_id: str, workflow: WorkflowSchema):
    """Updates an existing workflow."""
    await db.update_workflow(workflow_id, workflow.model_dump())
    return {"status": "success"}

@rest_router.delete("/api/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """Deletes a workflow."""
    await db.delete_workflow(workflow_id)
    return {"status": "success"}

# --- RAG Oracle API ---
class RAGIngestRequest(BaseModel):
    dir_path: str

class RAGQueryRequest(BaseModel):
    query: str

@rest_router.post("/api/rag/ingest")
async def rag_ingest(req: RAGIngestRequest):
    if rag_oracle_module.oracle_instance:
        result = await rag_oracle_module.oracle_instance.ingest_codebase(req.dir_path)
        return result
    return {"success": False, "error": "RAG Oracle not initialized"}

@rest_router.post("/api/rag/query")
async def rag_query(req: RAGQueryRequest):
    if rag_oracle_module.oracle_instance:
        result = await rag_oracle_module.oracle_instance.consult_oracle(req.query)
        return result
    return {"success": False, "error": "RAG Oracle not initialized"}

# --- Scrapper OS Bridge API ---
from core.scrapper_os import scrapper_os

@rest_router.get("/api/scrapper-os/health")
async def scrapper_health():
    """Check if Scrapper OS is online and reachable."""
    return await scrapper_os.check_health()

@rest_router.get("/api/scrapper-os/scrapers")
async def list_scrapers():
    """List all available scrapers."""
    return await scrapper_os.list_scrapers()

class RunScraperRequest(BaseModel):
    scraper_id: str
    params: Optional[Dict[str, Any]] = None

@rest_router.post("/api/scrapper-os/run-scraper")
async def run_scraper(req: RunScraperRequest):
    """Trigger a specific scraper."""
    return await scrapper_os.run_scraper(req.scraper_id, req.params)

@rest_router.get("/api/voices")
async def get_available_voices():
    """Returns available TTS voices for the Voice Studio UI."""
    return {
        "voices": {
            "edge": [
                {"id": "en-US-AriaNeural",   "name": "Aria",    "provider": "edge", "gender": "female", "lang": "en-US"},
                {"id": "en-US-GuyNeural",    "name": "Guy",     "provider": "edge", "gender": "male",   "lang": "en-US"},
                {"id": "en-US-JennyNeural",  "name": "Jenny",   "provider": "edge", "gender": "female", "lang": "en-US"},
                {"id": "en-US-SaraNeural",   "name": "Sarah",   "provider": "edge", "gender": "female", "lang": "en-US"},
                {"id": "en-US-DavisNeural",  "name": "Davis",   "provider": "edge", "gender": "male",   "lang": "en-US"},
                {"id": "en-GB-SoniaNeural",  "name": "Sonia",   "provider": "edge", "gender": "female", "lang": "en-GB"},
                {"id": "en-IN-NeerjaNeural", "name": "Neerja",  "provider": "edge", "gender": "female", "lang": "en-IN"},
                {"id": "hi-IN-SwaraNeural",  "name": "Swara",   "provider": "edge", "gender": "female", "lang": "hi-IN"},
            ],
            "gemini": [
                {"id": "Puck",    "name": "Puck",    "provider": "gemini", "gender": "male",   "lang": "en"},
                {"id": "Charon",  "name": "Charon",  "provider": "gemini", "gender": "male",   "lang": "en"},
                {"id": "Kore",    "name": "Kore",    "provider": "gemini", "gender": "female", "lang": "en"},
                {"id": "Fenrir",  "name": "Fenrir",  "provider": "gemini", "gender": "male",   "lang": "en"},
                {"id": "Aoede",   "name": "Aoede",   "provider": "gemini", "gender": "female", "lang": "en"},
            ]
        }
    }

@rest_router.get("/api/history/{session_id}")
async def get_session_history(session_id: str):
    """Returns the conversation history for a specific active session."""
    # Since gs.active_sessions is defined below, we'll access it globally.
    # We can just return empty for now to stop the 404, or actually return it.
    session = gs.active_sessions.get(session_id)
    if not session:
        return {"history": []}
    return {"history": list(session.conversation_history)}

# --- OS Automation Endpoints (Ported from daemon.py) ---
class MouseMove(BaseModel):
    x: int
    y: int

class MouseClick(BaseModel):
    button: str = "left"

class KeyboardType(BaseModel):
    text: str

class KeyboardPress(BaseModel):
    keys: list[str]

class WindowFocus(BaseModel):
    title: str

@rest_router.post("/mouse/move")
async def move_mouse(req: MouseMove):
    if not pyautogui:
        raise HTTPException(status_code=501, detail="pyautogui not installed")
    await asyncio.to_thread(pyautogui.moveTo, req.x, req.y, duration=0.2)
    return {"status": "success", "action": "mouse_move", "x": req.x, "y": req.y}

@rest_router.post("/mouse/click")
async def click_mouse(req: MouseClick):
    if not pyautogui:
        raise HTTPException(status_code=501, detail="pyautogui not installed")
    await asyncio.to_thread(pyautogui.click, button=req.button)
    return {"status": "success", "action": "mouse_click", "button": req.button}

@rest_router.post("/keyboard/type")
async def type_keyboard(req: KeyboardType):
    if not pyautogui:
        raise HTTPException(status_code=501, detail="pyautogui not installed")
    await asyncio.to_thread(pyautogui.write, req.text, interval=0.01)
    return {"status": "success", "action": "keyboard_type"}

@rest_router.post("/keyboard/press")
async def press_keyboard(req: KeyboardPress):
    if not pyautogui:
        raise HTTPException(status_code=501, detail="pyautogui not installed")
    await asyncio.to_thread(pyautogui.hotkey, *req.keys)
    return {"status": "success", "action": "keyboard_press", "keys": req.keys}

@rest_router.get("/window/list")
async def list_windows():
    if not gw:
        raise HTTPException(status_code=501, detail="pygetwindow not installed")
    def _get_titles():
        return [t for t in gw.getAllTitles() if t.strip()] # type: ignore
    titles = await asyncio.to_thread(_get_titles)
    return {"windows": titles}

@rest_router.post("/window/focus")
async def focus_window(req: WindowFocus):
    if not gw:
        raise HTTPException(status_code=501, detail="pygetwindow not installed")
    def _focus():
        win = gw.getWindowsWithTitle(req.title)
        if not win:
            raise Exception("Window not found")
        win[0].activate()
    try:
        await asyncio.to_thread(_focus)
        return {"status": "success", "window": req.title}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@rest_router.get("/screenshot")
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

@rest_router.post("/execute-tool")
async def execute_tool(request: dict):
    """
    Handle tool execution requests forwarded from the Gemini Live frontend.
    """
    try:
        function_calls = request.get("functionCalls", [])
        results = []
        for call in function_calls:
            name = call.get("name")
            args = call.get("args", {})
            logger.info(f"🛠️ Executing tool: {name} with args: {args}")
            
            # Plug into Central Tool Registry
            if name == "search_web":
                results.append({"query": args.get("query"), "status": "simulated_success", "snippet": "Nexus search results dummy payload."})
            if name in ["pc_open_app", "pc_close_app", "pc_type_text", "pc_press_shortcut", "pc_take_screenshot"]:
                out = await execute_pc_action(name, args)
                results.append({"action": name, "output": out})
            elif name == "create_task":
                out = await create_task(args.get("title", ""), args.get("priority", "medium"), args.get("due_date"))
                results.append({"title": args.get("title"), "output": out})
            elif name == "create_note":
                out = await create_note(args.get("title", ""), args.get("content", ""))
                results.append({"title": args.get("title"), "output": out})
            elif name == "update_preferences":
                out = await update_preferences(args.get("preferences", {}))
                results.append({"preferences": args.get("preferences"), "output": out})
            elif name == "get_user_memory":
                out = await get_user_memory()
                results.append({"output": out})
            elif name == "delete_user_preference":
                out = await delete_user_preference(args.get("category", ""), args.get("key", ""))
                results.append({"category": args.get("category"), "key": args.get("key"), "output": out})
            elif name == "read_file":
                out = await read_file(args.get("file_path", ""))
                results.append({"file_path": args.get("file_path"), "output": out})
            elif name == "write_file":
                out = await write_file(args.get("file_name", ""), args.get("content", ""))
                results.append({"file_name": args.get("file_name"), "output": out})
            elif name == "read_directory":
                out = await read_directory(args.get("directory_path", ""))
                results.append({"directory_path": args.get("directory_path"), "output": out})
            elif name == "get_weather":
                out = await get_weather(args.get("city", ""))
                results.append({"city": args.get("city"), "output": out})
            elif name == "ingest_codebase":
                if rag_oracle_module.oracle_instance:
                    out = await rag_oracle_module.oracle_instance.ingest_codebase(args.get("dir_path", ""))
                    results.append({"dir_path": args.get("dir_path"), "output": out})
                else:
                    results.append({"error": "RAG Oracle not initialized"})
            elif name == "consult_oracle":
                if rag_oracle_module.oracle_instance:
                    out = await rag_oracle_module.oracle_instance.consult_oracle(args.get("query", ""))
                    results.append({"query": args.get("query"), "output": out})
                else:
                    results.append({"error": "RAG Oracle not initialized"})
            else:
                results.append({"status": "unknown_tool"})
                
        return {"status": "success", "results": results}
    except Exception as e:
        logger.exception(f"❌ Tool Execution failed: {e}")
        return {"status": "error", "error": str(e)}


# ============================================================
# CAPABILITIES & PERMISSIONS API
# ============================================================

@rest_router.get("/api/capabilities")
async def get_capabilities():
    """Return all registered capabilities and their enabled state."""
    with db._get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, description, category, enabled FROM capabilities ORDER BY category, name")
        rows = cursor.fetchall()
        return [{"id": r[0], "name": r[1], "description": r[2], "category": r[3], "enabled": bool(r[4])} for r in rows]

class CapabilityToggle(BaseModel):
    enabled: bool

@rest_router.patch("/api/capabilities/{cap_id}")
async def toggle_capability(cap_id: str, body: CapabilityToggle):
    """Enable or disable a capability by ID."""
    with db._get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE capabilities SET enabled = ? WHERE id = ?", (1 if body.enabled else 0, cap_id))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Capability {cap_id} not found")
        conn.commit()
    return {"id": cap_id, "enabled": body.enabled}

@rest_router.get("/api/audit-log")
async def get_audit_log(limit: int = 50):
    """Return the last N tool execution audit log entries."""
    with db._get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT tool_id, parameters_passed, result_status, permission_state, timestamp FROM tool_audit_logs ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        import json as _json
        return [{"tool": r[0], "params": _json.loads(r[1]) if r[1] else {}, "status": r[2], "permission": r[3], "timestamp": r[4]} for r in rows]
