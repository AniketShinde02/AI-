import os
import logging
import asyncio
from dotenv import load_dotenv

# Vision Agents core & plugins
# Note: exact import paths depend on vision-agents version
from vision_agents.core import Agent, User
from vision_agents.plugins.getstream import Edge

# Example placeholders for LLM/STT/TTS plugins
# Adjust these based on the actual vision_agents package structure
from vision_agents.core.llms import GroqLLM, OpenRouterLLM
from vision_agents.core.stt import DeepgramSTT
from vision_agents.core.tts import ElevenLabsTTS

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("NexusVoiceAgent")

def get_llm():
    """Detects env vars and returns the preferred LLM client."""
    provider = os.getenv("LLM_PROVIDER", "openrouter").lower()
    
    if provider == "groq" and os.getenv("GROQ_API_KEY"):
        logger.info("Using Groq LLM")
        return GroqLLM(
            api_key=os.getenv("GROQ_API_KEY"),
            model=os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
        )
    
    logger.info("Using OpenRouter LLM (Default)")
    return OpenRouterLLM(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        model=os.getenv("OPENROUTER_FREE_MODEL", "deepseek/deepseek-chat")
    )

def get_stt():
    """Detects and returns preferred STT."""
    if os.getenv("DEEPGRAM_API_KEY"):
        logger.info("Using Deepgram STT")
        return DeepgramSTT(api_key=os.getenv("DEEPGRAM_API_KEY"))
    
    logger.warning("No Deepgram key found, using fallback STT if available")
    # Return a fallback or mock STT if vision-agents provides one
    return None

def get_tts():
    """Detects and returns preferred TTS."""
    if os.getenv("ELEVENLABS_API_KEY"):
        logger.info("Using ElevenLabs TTS")
        return ElevenLabsTTS(api_key=os.getenv("ELEVENLABS_API_KEY"))
    
    logger.warning("No ElevenLabs key found, using fallback TTS if available")
    return None

def create_agent() -> Agent:
    """Configures and returns the Vision Agent instance."""
    logger.info("Initializing Agent...")
    
    api_key = os.getenv("STREAM_API_KEY")
    api_secret = os.getenv("STREAM_API_SECRET")
    
    if not api_key or not api_secret:
        raise ValueError("STREAM_API_KEY and STREAM_API_SECRET must be set")
        
    edge = Edge(api_key=api_key, api_secret=api_secret)
    
    llm = get_llm()
    stt = get_stt()
    tts = get_tts()
    
    agent_user = User(name="Nexus Voice Agent", id="nexus_agent_1")
    
    agent = Agent(
        edge=edge,
        agent_user=agent_user,
        instructions=(
            "You are Nexus, a friendly, concise voice assistant. "
            "Answer questions clearly in 1-2 short sentences. "
            "You can speak English, Hindi, and Marathi."
        ),
        llm=llm,
        stt=stt,
        tts=tts,
        turn_detection=True  # Detect when user stops talking
    )
    
    return agent

async def join_call(agent: Agent, call_type: str, call_id: str):
    """Joins the Stream call and processes audio."""
    try:
        logger.info(f"Ensuring agent user exists: {agent.agent_user.id}")
        await agent.create_user()
        
        logger.info(f"Connecting to Stream call {call_type}:{call_id}")
        call = await agent.create_call(call_type, call_id)
        
        logger.info("Agent joining call...")
        async with agent.join(call):
            logger.info("Agent successfully joined call. Listening for audio...")
            # Keep process alive while the call is active
            await asyncio.Future()
            
    except Exception as e:
        logger.error(f"Error in join_call: {e}", exc_info=True)
