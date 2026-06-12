from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config.settings import settings
import sys
import os
import time
from loguru import logger
from .core.diagnostics import check_environment

# Configure loguru
logger.remove()
logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>", level="DEBUG")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info("[Launch] Nexus 2.0 Backend Starting...")
    logger.info(f"[Env] Project Root: {os.getcwd()}")
    logger.info(f"[Env] Project: {settings.PROJECT_NAME} v{settings.VERSION}")
    logger.info(f"[Env] Debug Mode: {settings.DEBUG}")
    
    # Check essential keys (log status, not values)
    logger.info("[Config] Checking Environment Keys:")
    keys = {
        "Groq": settings.GROQ_API_KEY,
        "GetStream": settings.GETSTREAM_API_KEY,
        "Deepgram": settings.DEEPGRAM_API_KEY,
        "ElevenLabs": settings.ELEVENLABS_API_KEY,
        "Firebase Credentials": settings.FIREBASE_CREDENTIALS or os.path.exists("serviceAccountKey.json")
    }
    
    for key_name, value in keys.items():
        status = "[OK] Loaded" if value else "[MISSING] Missing"
        logger.info(f"   - {key_name: <20}: {status}")

    # Run deep diagnostics if in debug mode
    if settings.DEBUG:
        check_environment()

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION
    }

from .voice.session import session_manager
from .voice.orchestrator import voice_orchestrator
from pydantic import BaseModel

class VoiceSessionRequest(BaseModel):

    userId: str
    agentType: str = "nexus-v2"
    callId: str = None # If provided, use this, else generate
    persona: str = "female"

@app.post("/voice/session")
async def get_voice_session(request: VoiceSessionRequest):
    """
    1. Generates a Stream token for the Frontend.
    2. Triggers the Nexus Agent to join the call room.
    """
    call_id = request.callId or f"call_{request.userId}"
    return await _handle_voice_session(request.userId, call_id, persona=request.persona)

@app.post("/calls/{call_type}/{session_id}/sessions")
async def stream_voice_session(call_type: str, session_id: str):
    """
    Alias for Stream-style frontend calls.
    Extracts userId from session_id (format: nexus_session_{userId})
    """
    user_id = session_id.replace("nexus_session_", "")
    # Default to female for alias calls unless we add a query param later
    return await _handle_voice_session(user_id, session_id, call_type, persona="female")

async def _handle_voice_session(user_id: str, call_id: str, call_type: str = "default", persona: str = "female"):
    logger.info(f"[Voice] New voice session request for user: {user_id}, call_id: {call_id}")
    
    # Generate Frontend Token
    try:
        session_data = await session_manager.create_session(user_id)
        logger.debug(f"[Session] Token generated for {user_id}")
    except Exception as e:
        logger.error(f"[Error] Failed to generate session token: {e}")
        return {"error": "Failed to initialize session"}
    
    # Trigger Backend Agent Join
    try:
        logger.info(f"[Agent] Triggering agent to join call: {call_id}")
        await voice_orchestrator.start_session(
            user_id=user_id,
            call_id=call_id,
            call_type=call_type,
            persona=persona
        )
        logger.info(f"[Agent] Successfully triggered for call: {call_id}")
    except Exception as e:
        logger.error(f"[Error] Failed to trigger agent: {e}")
        # We still return the token so the user can at least join/wait

    return {
        "sessionId": call_id,
        "callType": call_type,
        "token": session_data["token"],
        "apiKey": session_data["api_key"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

