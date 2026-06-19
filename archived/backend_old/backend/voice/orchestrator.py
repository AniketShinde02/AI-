from loguru import logger
import os
import asyncio
import json
from typing import Optional

# vision-agents core
from vision_agents.core import AgentLauncher, User
from vision_agents.core.agents.agents import Agent
from vision_agents.plugins.getstream import Edge

from .groq_llm import GroqLLM
from .providers import GroqSTT, CartesiaTTS, LocalKokoroTTS, NullSTT, log_broadcaster
from ..config.settings import settings

import contextvars

_user_id_var = contextvars.ContextVar('user_id', default="anonymous")
_persona_var = contextvars.ContextVar('persona', default="female")

class NexusVoiceOrchestrator:
    """
    Manages production-grade voice sessions using vision-agents.
    Handles WebRTC transport via GetStream and streaming AI pipeline.
    """
    
    def __init__(self):
        logger.debug("Initializing NexusVoiceOrchestrator...")
        self.launcher = AgentLauncher(
            create_agent=self.create_agent,
            join_call=self.join_call,
            max_concurrent_sessions=50,
            agent_idle_timeout=28800.0,
            max_sessions_per_call=1
        )
        self._log_broadcast_task = None

    def create_agent(self) -> Agent:
        """Factory method called for each new voice session."""
        user_id = _user_id_var.get()
        persona = _persona_var.get()
        
        logger.info(f"🏗  Building Nexus Agent (Production) for user: {user_id}")

        try:
            logger.debug("Initializing GetStream Edge...")
            edge = Edge()
            
            logger.debug("Initializing Groq STT (Server-Side)...")
            stt = GroqSTT()

            logger.debug("Initializing Groq LLM with Tool-Calling and Memory...")
            llm = GroqLLM(
                user_id=user_id # Enable Firestore persistence & context
            )

            # Persona selection based on user preference
            # Sarah (Female): a0e9987d-b687-4345-a868-3e0e77abe7e8 (British Female)
            # Alex (Male): 6926713a-d066-4774-895d-98cf3a046228 (US Male)
            voice_id = "a0e9987d-b687-4345-a868-3e0e77abe7e8" # Sarah
            persona_name = "Sarah"
            kokoro_voice = "af_sarah"
            if persona == "male":
                voice_id = "6926713a-d066-4774-895d-98cf3a046228" # Alex
                persona_name = "Alex"
                kokoro_voice = "am_michael"

            # Check if we should use Local TTS (Survive mode)
            # Default to Local for high-durability 14,400 min requirement
            use_local_tts = os.getenv("NEXUS_LOCAL_TTS", "true").lower() == "true"

            if use_local_tts:
                logger.info(f"🚀 Using Local Kokoro TTS (Voice: {kokoro_voice})")
                tts = LocalKokoroTTS(voice=kokoro_voice)
            else:
                logger.debug(f"Initializing Cartesia TTS with persona: {persona} ({persona_name})...")
                tts = CartesiaTTS(voice_id=voice_id)

            # Perplexity Mode - can be passed from frontend or env
            perplexity_mode = os.getenv("NEXUS_PERPLEXITY_MODE", "true").lower() == "true"
            
            instructions = (
                f"You are {persona_name}, a highly intelligent and helpful voice AI assistant. "
                "You provide deep, comprehensive information. "
            )
            
            if perplexity_mode:
                instructions += "Always provide full, detailed, and cited-style information like Perplexity AI. "
            else:
                instructions += "Be concise and direct in your responses. "
                
            instructions += (
                "If you don't know something or need up-to-date info, use the 'web_search' tool. "
                "Be professional, clear, and informative. "
                "You can also run system commands and manage the user's tasks and notes. "
                "Keep your spoken responses relatively concise but high-signal."
            )

            agent = Agent(
                edge=edge,
                agent_user=User(id="nexus-agent-1", name="Nexus"),
                instructions=instructions,
                llm=llm,
                stt=stt,
                tts=tts,
                streaming_tts=True
            )
            logger.info("✅ Production Agent successfully built.")
            return agent
        except Exception as e:
            logger.error(f"❌ Failed to create agent: {e}")
            raise

    async def _broadcast_logs_to_call(self, call):
        """Drains the log_broadcaster queue and sends events via GetStream."""
        logger.debug("Starting log broadcast loop for call...")
        try:
            while True:
                log_data = await log_broadcaster.logs.get()
                # Send custom event 'nexus_log' to the call members
                # log_data is now a dict: {"level": level, "message": message, "data": data, "timestamp": ts}
                await call.send_custom_event({
                    "type": "nexus_log",
                    "message": log_data["message"],
                    "level": log_data["level"],
                    "data": log_data.get("data"),
                    "timestamp": log_data["timestamp"]
                })
                log_broadcaster.logs.task_done()
        except asyncio.CancelledError:
            logger.debug("Log broadcast loop stopped.")
        except Exception as e:
            logger.error(f"Error in log broadcast: {e}")

    async def join_call(self, agent: Agent, call_type: str, call_id: str) -> None:
        """Callback to authenticate and join a WebRTC call."""
        logger.info(f"🎙 Joining call: {call_id} (type: {call_type})")
        
        try:
            logger.debug(f"Authenticating agent user: {agent.agent_user.id}")
            await agent.edge.authenticate(agent.agent_user)
            
            logger.debug(f"Creating/Joining call object: {call_id}")
            call = await agent.edge.create_call(call_id, call_type=call_type)
            
            # Start log broadcasting in the background
            self._log_broadcast_task = asyncio.create_task(self._broadcast_logs_to_call(call))
            
            # The agent will now automatically handle STT via the audio track
            # using the GroqSTT provider assigned to it.

            async with agent.join(call):
                logger.info(f"✨ Nexus is live on call: {call_id}")
                # Welcome message to verify audio is working
                await agent.say("Neural link established. I am online and listening.")
                
                # Keep the session alive until the call ends or agent stops
                while agent.is_running:
                    await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"❌ Error during call join for {call_id}: {e}")
            raise
        finally:
            if self._log_broadcast_task:
                self._log_broadcast_task.cancel()

    async def start_session(self, user_id: str, call_id: str, call_type: str = "default", persona: str = "female"):
        """Entry point for the API to trigger a session start."""
        logger.debug(f"Starting session launcher for call: {call_id} with persona: {persona}")
        
        # Set context variables for create_agent
        _user_id_var.set(user_id)
        _persona_var.set(persona)
        
        return await self.launcher.start_session(call_id=call_id, call_type=call_type)

# Singleton instance
voice_orchestrator = NexusVoiceOrchestrator()

