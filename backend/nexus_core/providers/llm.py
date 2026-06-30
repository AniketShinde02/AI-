import logging
from typing import Optional, Any
from groq import AsyncGroq
from vision_agents.core.llm.llm import LLM, LLMResponseEvent
from vision_agents.core.llm.events import (
    LLMResponseChunkEvent,
    LLMResponseCompletedEvent,
    LLMRequestStartedEvent,
)
from vision_agents.core.edge.types import Participant

logger = logging.getLogger("nexus.llm")

class GroqLLM(LLM):
    """
    LLM Provider using Groq's Llama 3 70B for high-speed reasoning.
    """
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile", system_prompt: Optional[str] = None):
        super().__init__()
        self.client = AsyncGroq(api_key=api_key)
        self.model = model
        if system_prompt:
            self.set_instructions(system_prompt)

    async def simple_response(
        self,
        text: str,
        participant: Optional[Participant] = None
    ) -> LLMResponseEvent[Any]:
        """
        Generate a streaming response and emit events for the Agent to handle.
        """
        logger.info(f"🧠 LLM Query: {text}")
        
        # Emit start event
        self.events.send(LLMRequestStartedEvent(
            session_id=self.agent.id if self.agent else "default",
            plugin_name="GroqLLM",
            participant=participant
        ))

        full_text = ""
        try:
            stream = await self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": self._instructions},
                    {"role": "user", "content": text}
                ],
                model=self.model,
                stream=True,
            )

            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_text += content
                    # Emit chunk for streaming TTS
                    self.events.send(LLMResponseChunkEvent(
                        session_id=self.agent.id if self.agent else "default",
                        plugin_name="GroqLLM",
                        delta=content,
                        participant=participant,
                        item_id="msg_" + str(chunk.id)
                    ))

            # Emit completion event
            self.events.send(LLMResponseCompletedEvent(
                session_id=self.agent.id if self.agent else "default",
                plugin_name="GroqLLM",
                text=full_text,
                participant=participant,
                item_id="msg_" + str(chunk.id)
            ))

            return LLMResponseEvent(original=None, text=full_text)

        except Exception as e:
            logger.error(f"❌ Groq LLM Error: {e}")
            return LLMResponseEvent(original=None, text="", exception=e)

    def _convert_tools_to_provider_format(self, tools):
        return []

    def _extract_tool_calls_from_response(self, response):
        return []
