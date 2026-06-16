import os
import asyncio
import logging
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from vision_agents.core import Agent, AgentLauncher, Runner, ServeOptions, User
from vision_agents.plugins import getstream
import vision_agents.core.stt.events as stt_events
import vision_agents.core.agents.events as agent_events
import vision_agents.core.edge.events as edge_events

# Local Providers
from providers.llm import GroqLLM
from providers.tts import KokoroTTS
from providers.stt import GroqSTT

# Import Backend Tools
from tools.system import run_command, open_application
from tools.task_tools import create_task, create_note
from tools.memory_tools import update_preferences

# Load environment variables
load_dotenv()

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Nexus")

# 1. Component Configuration
AGENT_USER_ID = "nexus-agent-1"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
KOKORO_MODEL_PATH = os.getenv("KOKORO_MODEL_PATH", "D:/AI/backend/src/backend/voice/models/kokoro-v0_19.onnx")

if not GROQ_API_KEY:
    logger.error("❌ GROQ_API_KEY is missing!")

# 2. Agent Logic
_background_tasks = set()

async def greeter(agent: Agent):
    """Speaks a welcome message when the agent joins the call."""
    try:
        logger.info(f"🎤 Greeter: Initializing welcome sequence for agent {agent.id}...")
        
        # 3. Delay speaking until transport ready (WebRTC ICE needs time)
        await asyncio.sleep(4.5)  # Increased for stability
        
        logger.info("🎤 Greeter: Triggering language selection message...")
        await agent.say("Namaste. Nexus system online. Please state your preferred language: English, Hindi, or Marathi.")
        
        logger.info("✅ Greeter: Message sent successfully.")
    except Exception as e:
        logger.error(f"❌ Greeter Error: {e}", exc_info=True)

async def on_session_closed(agent: Agent, session_id: str):
    """Cleanup when a session ends."""
    logger.info(f"🔒 Session CLOSED: {session_id}")
    # Cancel all background tasks for this session
    for task in list(_background_tasks):
        if not task.done():
            task.cancel()
    _background_tasks.clear()

async def on_call_join(agent: Agent, call_type: str, call_id: str):
    """Triggered when the agent successfully joins a Stream call."""
    logger.info(f"📞 Agent JOINED! ID: {agent.id} | User ID: {agent.agent_user.id} | Call: {call_type}:{call_id}")
    
    # Send a diagnostic event to the frontend immediately
    await agent.edge.send_custom_event({
        "type": "agent_joined",
        "agent_user_id": agent.agent_user.id,
        "session_id": agent.id
    })

    @agent.subscribe
    async def on_event(event):
        # 1. Track Management
        if isinstance(event, edge_events.TrackAddedEvent):
            uid = event.participant.user_id if event.participant else "unknown"
            kind = event.track.kind
            logger.info(f"👂 [Edge] Track Added: {kind} from {uid}")
            
            # CRITICAL: Explicitly subscribe to audio tracks so STT can process them
            if kind == "audio" and not event.participant.is_local:
                logger.info(f"✅ Subscribing to audio track from {uid}")
                await agent.edge.subscribe(event.track.sid)
                
                # Signal frontend that we are listening
                await agent.edge.send_custom_event({
                    "type": "nexus_listening",
                    "user_id": uid
                })
            
        # 2. Forward User Transcripts to UI
        elif isinstance(event, stt_events.STTTranscriptEvent):
            logger.info(f"🎤 [Transcript] User: {event.text}")
            await agent.edge.send_custom_event({
                "type": "user_transcript",
                "text": event.text,
                "user_id": event.participant.user_id if event.participant else "unknown"
            })

        # 3. Forward Agent Messages to UI & Sync STT State
        elif isinstance(event, agent_events.AgentSayEvent):
            logger.info(f"🔊 [Agent] Speaking: {event.text}")
            if agent.stt:
                agent.stt.is_agent_speaking = True
                
            await agent.edge.send_custom_event({
                "type": "agent_message",
                "text": event.text
            })
            
            # Since AgentSayEvent is emitted when synthesis *starts*, we need to reset it after some time
            # or when we get a completion signal. For now, we use a simple task to reset after estimated duration.
            # (Words / 2.5) * 1.0 roughly estimates duration in seconds
            words = len(event.text.split())
            duration = max(2.0, words / 2.0) # Conservative estimate
            
            async def _reset_speaking():
                await asyncio.sleep(duration)
                if agent.stt:
                    agent.stt.is_agent_speaking = False
            
            asyncio.create_task(_reset_speaking())

    # Scenario 1: Welcome message
    task = asyncio.create_task(greeter(agent))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

def create_agent() -> Agent:
    """Expert factory for the Nexus Agent with Groq STT/LLM and Kokoro TTS."""
    llm = GroqLLM(
        api_key=GROQ_API_KEY,
        model="llama-3.3-70b-versatile",
        system_prompt="""You are Nexus, a highly advanced AI system. 
        IMPORTANT: Your first task is to wait for the user to select a language (English, Hindi, or Marathi).
        Once the language is selected:
        1. Switch your response language to the selected one.
        2. Be efficient, precise, and maintain a calm, professional tone.
        3. Keep responses concise for voice interaction.
        4. If English is chosen, use 'en-us'. If Hindi is chosen, use 'hi'. If Marathi is chosen, use 'mr'."""
    )
    
    tts = KokoroTTS(
        model_path=KOKORO_MODEL_PATH,
        voices_path=os.getenv("KOKORO_VOICES_PATH", "D:/AI/backend/src/backend/voice/models/voices-v1.0.bin")
    )
    stt = GroqSTT(api_key=GROQ_API_KEY)
    stt.silence_threshold = 500.0 # Match Int16 RMS logic
    
    # Initialize Edge transport (Stream)
    edge = getstream.Edge(auto_subscribe=True)
    
    return Agent(
        edge=edge,
        llm=llm,
        stt=stt,
        tts=tts,
        agent_user=User(id=AGENT_USER_ID, name="Nexus Agent"),
        streaming_tts=True
    )

# 3. Launcher & Runner Setup
launcher = AgentLauncher(
    create_agent=create_agent,
    join_call=on_call_join
)

options = ServeOptions()
runner = Runner(launcher=launcher, serve_options=options)
app = runner.fast_api

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Custom API Endpoints for Frontend Integration
@app.post("/voice/session")
async def voice_session(request: dict):
    """
    Handle session initialization from the tRPC proxy.
    Matches the call in router.ts: fetch(`${backendUrl}/voice/session`, ...)
    """
    call_id = request.get("callId")
    call_type = request.get("callType", "default")
    
    if not call_id:
        logger.error("❌ voice_session: callId missing in request")
        raise HTTPException(status_code=400, detail="callId is required")
    
    logger.info(f"🆕 Request to join call: {call_id} (type: {call_type})")
    
    try:
        session = await launcher.start_session(call_id=call_id, call_type=call_type)
        return {
            "status": "success",
            "session_id": session.id,
            "call_id": session.call_id,
            "agent_id": AGENT_USER_ID,
            "call_type": call_type
        }
    except Exception as e:
        logger.exception(f"❌ Failed to start voice session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/execute-tool")
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
            elif name == "run_command":
                out = await run_command(args.get("command", ""))
                results.append({"command": args.get("command"), "output": out})
            elif name == "open_application":
                out = await open_application(args.get("app_name", ""))
                results.append({"app_name": args.get("app_name"), "output": out})
            elif name == "create_task":
                out = await create_task(args.get("title", ""), args.get("priority", "medium"), args.get("due_date"))
                results.append({"title": args.get("title"), "output": out})
            elif name == "create_note":
                out = await create_note(args.get("title", ""), args.get("content", ""))
                results.append({"title": args.get("title"), "output": out})
            elif name == "update_preferences":
                out = await update_preferences(args.get("preferences", {}))
                results.append({"preferences": args.get("preferences"), "output": out})
            else:
                results.append({"status": "unknown_tool"})
                
        return {"status": "success", "results": results}
    except Exception as e:
        logger.exception(f"❌ Tool Execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 5. Main Entry Point
async def main():
    """Expert initialization for Nexus Voice Backend."""
    logger.info("🚀 Initializing Nexus Voice Agent (v0.5.5)...")
    
    import uvicorn
    logger.info("📡 Nexus Server starting on http://0.0.0.0:8000")
    uv_config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info", use_colors=False)
    server = uvicorn.Server(uv_config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
