"""
Nexus Voice Agent — production entry point.

Stack (all streaming, no OpenAI):
  Edge -> GetStream Video WebRTC     (vision-agents-plugins-getstream)
  STT  -> Deepgram Flux              (vision-agents-plugins-deepgram)
  LLM  -> Groq llama-3.3-70b        (custom GroqLLM in providers/llm.py)
  TTS  -> ElevenLabs Multilingual v2 (vision-agents-plugins-elevenlabs)

Runner modes:
  python main.py run   [--call-type audio_room --call-id <id>]  — single session (console)
  python main.py serve [--host 0.0.0.0 --port 8000]            — HTTP server mode

HTTP endpoints (serve mode):
  POST   /calls/{call_type}/{call_id}/sessions  → start agent on that call
  DELETE /calls/{call_type}/{call_id}/sessions/{session_id} → stop agent
  GET    /health                                → liveness
  GET    /ready                                 → readiness
"""

import logging
import os

from dotenv import load_dotenv

# vision-agents core
from vision_agents.core import AgentLauncher, Runner, ServeOptions, User
from vision_agents.core.agents.agents import Agent

# getstream edge plugin — provides the concrete EdgeTransport
from vision_agents.plugins.getstream import Edge

# provider plugins — confirmed paths from installed packages
from vision_agents.plugins.deepgram.deepgram_stt import STT as DeepgramSTT
from vision_agents.plugins.elevenlabs.tts import TTS as ElevenLabsTTS

# our custom Groq LLM (non-OpenAI)
from providers.llm import GroqLLM

# ── env ──────────────────────────────────────────────────────────────────────
load_dotenv()  # loads d:/AI/backend/voice_agent/.env

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("nexus.agent")

# ── config ───────────────────────────────────────────────────────────────────
# Stream env vars are read by getstream.AsyncStream automatically:
#   STREAM_API_KEY, STREAM_API_SECRET
GROQ_API_KEY       = os.environ.get("GROQ_API_KEY", "")
DEEPGRAM_API_KEY   = os.environ.get("DEEPGRAM_API_KEY", "")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")

MAX_SESSIONS    = int(os.environ.get("MAX_CONCURRENT_CALLS", "50"))
AGENT_USER_ID   = os.environ.get("AGENT_USER_ID", "nexus-agent-1")
AGENT_USER_NAME = os.environ.get("AGENT_USER_NAME", "Nexus")
PORT            = int(os.environ.get("PORT", "8000"))
HOST            = os.environ.get("HOST", "0.0.0.0")

SYSTEM_PROMPT = (
    "You are Nexus, a friendly, sharp voice assistant. "
    "Keep answers short (1–3 sentences), conversational, and avoid markdown. "
    "You can speak English, Hindi, and Marathi naturally."
)


# ── agent factory ─────────────────────────────────────────────────────────────
def create_agent() -> Agent:
    """
    Called once per new session by AgentLauncher.

    Returns a fresh, isolated Agent. Do NOT reuse agents across calls —
    the framework guarantees one agent per session.
    """
    logger.info("🏗  Building new agent session…")

    # Concrete GetStream edge transport.
    # Reads STREAM_API_KEY + STREAM_API_SECRET from env automatically.
    edge = Edge()

    stt = DeepgramSTT(
        api_key=DEEPGRAM_API_KEY,
        model=os.environ.get("DEEPGRAM_MODEL", "nova-3"),
        # eager_turn_detection gives ~200ms faster turn-end detection
        eager_turn_detection=True,
    )

    llm = GroqLLM(
        api_key=GROQ_API_KEY,
        model=os.environ.get("LLM_MODEL", "llama-3.3-70b-versatile"),
        temperature=0.7,
        max_tokens=200,
    )

    tts = ElevenLabsTTS(
        api_key=ELEVENLABS_API_KEY,
        model_id=os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2"),
        voice_id=os.environ.get("ELEVENLABS_VOICE_ID", "VR6AewLTigWG4xSOukaG"),
    )

    return Agent(
        edge=edge,
        agent_user=User(id=AGENT_USER_ID, name=AGENT_USER_NAME),
        instructions=SYSTEM_PROMPT,
        llm=llm,
        stt=stt,
        tts=tts,
        # Stream TTS per sentence as LLM streams — reduces latency
        streaming_tts=True,
    )


# ── join_call callback ────────────────────────────────────────────────────────
async def join_call(agent: Agent, call_type: str, call_id: str) -> None:
    """
    Called by AgentLauncher.start_session() for every new session.
    Uses agent.join() context manager — exits when the call ends.

    Signature must be:  async (agent, call_type, call_id) -> None
    """
    logger.info(f"🔑 Authenticating agent '{agent.agent_user.id}'…")
    await agent.edge.authenticate(agent.agent_user)

    logger.info(f"📞 Creating/fetching call {call_type}:{call_id}…")
    call = await agent.edge.create_call(call_id, call_type=call_type)

    logger.info(f"🎙  Joining call {call_id}…")
    async with agent.join(call):
        logger.info(f"✅ Agent is live on {call_id} — waiting for participants…")
        # Greet as soon as user joins (simple_response queues the LLM)
        await agent.simple_response("Greet the user briefly, in 1 sentence.")


# ── launcher + runner ─────────────────────────────────────────────────────────
launcher = AgentLauncher(
    create_agent=create_agent,
    join_call=join_call,
    max_concurrent_sessions=MAX_SESSIONS,
    agent_idle_timeout=120.0,     # leave if nobody speaks for 2 min
    max_sessions_per_call=1,      # one agent bot per room
)

runner = Runner(
    launcher=launcher,
    serve_options=ServeOptions(
        cors_allow_origins=["*"],  # tighten in production
    ),
)

# Expose the FastAPI app at module level for uvicorn / gunicorn
app = runner.fast_api


# ── CLI entrypoint ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # python main.py serve  →  HTTP server
    # python main.py run    →  joins a single call (for local testing)
    runner.cli()
