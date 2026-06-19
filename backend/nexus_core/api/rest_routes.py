"""
rest_routes.py
--------------
Responsibility: Data-layer REST API (sessions, memory, agents, workflows, RAG,
                capabilities, audit log, voices, theme, scrapper-os).
OS automation endpoints are in api/routes_system.py.
"""
import os
import shutil
import uuid
import logging

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from core.database import db
from core.theme_generator import generate_theme_from_image
import core.global_state as gs
import core.rag_oracle as rag_oracle_module

from api.routes_system import system_router

logger = logging.getLogger("nexus_ws")
rest_router = APIRouter()
# Re-export the system router so ws_main.py only needs to import rest_routes
rest_router.include_router(system_router)

BACKGROUNDS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "themes", "backgrounds"
)
os.makedirs(BACKGROUNDS_DIR, exist_ok=True)


# ------------------------------------------------------------------
# Health / Root
# ------------------------------------------------------------------

@rest_router.get("/")
async def root():
    """Health check — stops browser probe 404 log noise."""
    return {"status": "ok", "service": "Nexus Voice Backend", "version": "1.0.0"}

@rest_router.get("/health")
async def health_check():
    return {"status": "ok", "providers": {
        "stt": gs.stt_provider is not None,
        "llm": gs.llm_provider is not None,
        "tts": gs.tts_router is not None,
        "vad": gs.vad_model is not None,
    }}


# ------------------------------------------------------------------
# Theme
# ------------------------------------------------------------------

@rest_router.post("/api/theme/generate")
async def generate_theme(image: UploadFile = File(...)):
    """Receives an image, saves it, and asks Gemini Vision to extract a dark-mode theme."""
    try:
        ext = os.path.splitext(image.filename or ".png")[1]
        filename = f"bg_{uuid.uuid4().hex[:8]}{ext}"
        filepath = os.path.join(BACKGROUNDS_DIR, filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return {"success": False, "error": "GEMINI_API_KEY not found in backend environment"}

        theme_json = await generate_theme_from_image(filepath, api_key)
        return {
            "success": True,
            "background_url": f"http://localhost:8001/backgrounds/{filename}",
            "theme": theme_json
        }
    except Exception as e:
        logger.error(f"Theme generation failed: {e}")
        return {"success": False, "error": str(e)}


# ------------------------------------------------------------------
# Memory
# ------------------------------------------------------------------

@rest_router.get("/memory")
async def get_memory_api():
    return await db.get_all_memory()

@rest_router.delete("/memory/{category}/{key}")
async def delete_memory_api(category: str, key: str):
    await db.delete_memory(category, key)
    return {"status": "success"}


# ------------------------------------------------------------------
# Session history
# ------------------------------------------------------------------

@rest_router.get("/api/history/{session_id}")
async def get_session_history(session_id: str):
    session = gs.active_sessions.get(session_id)
    if not session:
        return {"history": []}
    return {"history": list(session.conversation_history)}


# ------------------------------------------------------------------
# Agents
# ------------------------------------------------------------------

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
    return await db.get_agents()

@rest_router.post("/api/agents")
async def create_agent(agent: AgentSchema):
    await db.create_agent(agent.model_dump())
    return {"status": "success", "agent_id": agent.id}

@rest_router.put("/api/agents/{agent_id}")
async def update_agent(agent_id: str, agent: AgentSchema):
    await db.update_agent(agent_id, agent.model_dump())
    return {"status": "success"}

@rest_router.delete("/api/agents/{agent_id}")
async def delete_agent(agent_id: str):
    await db.delete_agent(agent_id)
    return {"status": "success"}


# ------------------------------------------------------------------
# Workflows
# ------------------------------------------------------------------

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
    return await db.get_workflows()

@rest_router.post("/api/workflows")
async def create_workflow(workflow: WorkflowSchema):
    await db.create_workflow(workflow.model_dump())
    return {"status": "success", "workflow_id": workflow.id}

@rest_router.put("/api/workflows/{workflow_id}")
async def update_workflow(workflow_id: str, workflow: WorkflowSchema):
    await db.update_workflow(workflow_id, workflow.model_dump())
    return {"status": "success"}

@rest_router.delete("/api/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str):
    await db.delete_workflow(workflow_id)
    return {"status": "success"}


# ------------------------------------------------------------------
# RAG Oracle
# ------------------------------------------------------------------

class RAGIngestRequest(BaseModel):
    dir_path: str

class RAGQueryRequest(BaseModel):
    query: str

@rest_router.post("/api/rag/ingest")
async def rag_ingest(req: RAGIngestRequest):
    if rag_oracle_module.oracle_instance:
        return await rag_oracle_module.oracle_instance.ingest_codebase(req.dir_path)
    return {"success": False, "error": "RAG Oracle not initialized"}

@rest_router.post("/api/rag/query")
async def rag_query(req: RAGQueryRequest):
    if rag_oracle_module.oracle_instance:
        return await rag_oracle_module.oracle_instance.consult_oracle(req.query)
    return {"success": False, "error": "RAG Oracle not initialized"}


# ------------------------------------------------------------------
# Scrapper OS bridge
# ------------------------------------------------------------------

from core.scrapper_os import scrapper_os

class RunScraperRequest(BaseModel):
    scraper_id: str
    params: Optional[Dict[str, Any]] = None

@rest_router.get("/api/scrapper-os/health")
async def scrapper_health():
    return await scrapper_os.check_health()

@rest_router.get("/api/scrapper-os/scrapers")
async def list_scrapers():
    return await scrapper_os.list_scrapers()

@rest_router.post("/api/scrapper-os/run-scraper")
async def run_scraper(req: RunScraperRequest):
    return await scrapper_os.run_scraper(req.scraper_id, req.params)


# ------------------------------------------------------------------
# Voices
# ------------------------------------------------------------------

@rest_router.get("/api/voices")
async def get_available_voices():
    return {
        "voices": {
            "edge": [
                {"id": "en-US-AriaNeural",   "name": "Aria",   "provider": "edge", "gender": "female", "lang": "en-US"},
                {"id": "en-US-GuyNeural",    "name": "Guy",    "provider": "edge", "gender": "male",   "lang": "en-US"},
                {"id": "en-US-JennyNeural",  "name": "Jenny",  "provider": "edge", "gender": "female", "lang": "en-US"},
                {"id": "en-US-SaraNeural",   "name": "Sarah",  "provider": "edge", "gender": "female", "lang": "en-US"},
                {"id": "en-US-DavisNeural",  "name": "Davis",  "provider": "edge", "gender": "male",   "lang": "en-US"},
                {"id": "en-GB-SoniaNeural",  "name": "Sonia",  "provider": "edge", "gender": "female", "lang": "en-GB"},
                {"id": "en-IN-NeerjaNeural", "name": "Neerja", "provider": "edge", "gender": "female", "lang": "en-IN"},
                {"id": "hi-IN-SwaraNeural",  "name": "Swara",  "provider": "edge", "gender": "female", "lang": "hi-IN"},
            ],
            "gemini": [
                {"id": "Puck",   "name": "Puck",   "provider": "gemini", "gender": "male",   "lang": "en"},
                {"id": "Charon", "name": "Charon", "provider": "gemini", "gender": "male",   "lang": "en"},
                {"id": "Kore",   "name": "Kore",   "provider": "gemini", "gender": "female", "lang": "en"},
                {"id": "Fenrir", "name": "Fenrir", "provider": "gemini", "gender": "male",   "lang": "en"},
                {"id": "Aoede",  "name": "Aoede",  "provider": "gemini", "gender": "female", "lang": "en"},
            ]
        }
    }


# ------------------------------------------------------------------
# Capabilities & Permissions (use sync _get_conn for read-only queries)
# ------------------------------------------------------------------

class CapabilityToggle(BaseModel):
    enabled: bool

@rest_router.get("/api/capabilities")
async def get_capabilities():
    """Return all registered capabilities and their enabled state."""
    with db._get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, description, category, enabled FROM capabilities ORDER BY category, name"
        )
        rows = cursor.fetchall()
        return [{"id": r[0], "name": r[1], "description": r[2], "category": r[3], "enabled": bool(r[4])}
                for r in rows]

@rest_router.patch("/api/capabilities/{cap_id}")
async def toggle_capability(cap_id: str, body: CapabilityToggle):
    """Enable or disable a capability by ID."""
    with db._get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE capabilities SET enabled = ? WHERE id = ?",
            (1 if body.enabled else 0, cap_id)
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Capability {cap_id} not found")
        conn.commit()
    return {"id": cap_id, "enabled": body.enabled}

@rest_router.get("/api/audit-log")
async def get_audit_log(limit: int = 50):
    """Return the last N tool execution audit log entries."""
    import json as _json
    with db._get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT tool_id, parameters_passed, result_status, permission_state, timestamp "
            "FROM tool_audit_logs ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        return [{"tool": r[0], "params": _json.loads(r[1]) if r[1] else {}, "status": r[2],
                 "permission": r[3], "timestamp": r[4]} for r in rows]
