import asyncio
import logging
import os
from typing import Optional

from vision_agents.core.agents import Agent
from vision_agents.core.edge.types import User
from vision_agents.plugins.getstream.stream_edge_transport import StreamEdge
from vision_agents.plugins.deepgram.deepgram_stt import STT as DeepgramSTT
from vision_agents.plugins.elevenlabs.tts import TTS as ElevenLabsTTS

from providers.llm import GroqLLM

logger = logging.getLogger(__name__)

async def join_and_run_agent(call_id: str, instructions: Optional[str] = None):
    """
    Initializes and runs the streaming voice agent pipeline.
    
    Args:
        call_id: The GetStream call ID to join.
        instructions: Optional system prompt/instructions for the agent.
    """
    logger.info(f"🚀 Initializing production agent for call: {call_id}")

    # 1. Environment Validation
    required_vars = [
        "STREAM_API_KEY", "STREAM_API_SECRET", 
        "DEEPGRAM_API_KEY", "ELEVENLABS_API_KEY", "GROQ_API_KEY"
    ]
    missing = [v for v in required_vars if not os.environ.get(v)]
    if missing:
        error_msg = f"Missing required environment variables: {', '.join(missing)}"
        logger.error(f"❌ {error_msg}")
        raise ValueError(error_msg)

    # 2. Configure Providers
    stt = DeepgramSTT() # Uses DEEPGRAM_API_KEY from env
    tts = ElevenLabsTTS() # Uses ELEVENLABS_API_KEY from env
    llm = GroqLLM(api_key=os.environ["GROQ_API_KEY"])

    # 3. Initialize Transport
    # Note: StreamEdge uses AsyncStream internally which respects STREAM_API_KEY/SECRET
    transport = StreamEdge()
    
    # 4. Create Agent Identity
    agent_user = User(
        id="production-agent-001",
        name="Iridescent Assistant",
        image="https://getstream.io/random_svg/?id=agent&name=Assistant"
    )

    # 5. Create Agent instance
    agent = Agent(
        transport=transport,
        user=agent_user,
        llm=llm,
        stt=stt,
        tts=tts,
        streaming_tts=True # Enable streaming for lower latency
    )

    try:
        # 6. Authenticate and Join Call
        await transport.authenticate(agent_user)
        
        # We assume the call is already created by the client or launcher
        # but we use create_call (which is actually a get_or_create) to be safe
        call = await transport.create_call(call_id=call_id)
        
        logger.info(f"🔗 Joining WebRTC session for call: {call_id}")
        
        # Use the recommended async with pattern for agent lifecycle
        async with agent.join(call) as connection:
            # Create the conversation context
            await transport.create_conversation(
                call=call, 
                user=agent_user, 
                instructions=instructions or "You are a helpful, professional AI assistant. Keep responses concise and natural for voice conversation."
            )
            
            logger.info("✅ Agent is live and listening...")
            
            # Keep the agent alive as long as participants are present or connection is open
            # The agent loop internally handles STT -> LLM -> TTS
            while True:
                # We can add custom monitoring logic here if needed
                await asyncio.sleep(1)
                
                # Optional: Add idleness check if required
                # if connection.idle_since() > 60: # 60 seconds idle
                #     logger.info("🕒 Agent idle for too long, disconnecting...")
                #     break
                    
    except asyncio.CancelledError:
        logger.info("🛑 Agent task cancelled, shutting down gracefully...")
    except Exception as e:
        logger.exception(f"❌ Critical error in agent loop: {e}")
    finally:
        logger.info(f"🔌 Agent disconnected from call {call_id}")
        await transport.close()
