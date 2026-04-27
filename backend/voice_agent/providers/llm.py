"""
Groq LLM plugin for vision-agents.

Extends vision_agents.core.llm.LLM — the only required abstract method
is simple_response(), which must return an LLMResponseEvent.

The Agent calls simple_response() for every STT transcript it receives.
The returned LLMResponseEvent.text drives the TTS pipeline.
"""

import logging
import os
from typing import Optional

from groq import AsyncGroq
from vision_agents.core.llm.llm import LLM, LLMResponseEvent
from vision_agents.core.edge.types import Participant

logger = logging.getLogger(__name__)


class GroqLLM(LLM):
    """
    Groq-backed LLM for the vision-agents pipeline.

    simple_response() is the only abstract method — it receives the
    transcribed user text and must return an LLMResponseEvent whose
    .text field is the assistant reply (drives TTS).

    Also sends LLMResponseChunkEvent / LLMResponseCompletedEvent on
    self.events so that any attached listeners (transcripts, logging)
    get streaming updates.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.7,
        max_tokens: int = 200,
    ):
        super().__init__()
        self.api_key = api_key or os.environ.get("GROQ_API_KEY", "")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = AsyncGroq(api_key=self.api_key)

    def _build_messages(self, text: str) -> list:
        """Build the message list for Groq, including chat history if available."""
        messages = [{"role": "system", "content": self._instructions}]

        # Append prior conversation turns if available
        if self._conversation:
            for msg in self._conversation.messages:
                role = getattr(msg, "role", None)
                content = getattr(msg, "content", None)
                if role and content:
                    messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": text})
        return messages

    async def simple_response(
        self,
        text: str,
        participant: Optional[Participant] = None,
    ) -> LLMResponseEvent:
        """
        Called by the Agent for every STT transcript.

        Streams tokens from Groq and accumulates the full response.
        Fires LLMResponseChunkEvent per token and LLMResponseCompletedEvent
        on the EventManager so listeners (e.g., transcripts) receive updates.

        Returns an LLMResponseEvent whose .text drives the TTS output.
        """
        messages = self._build_messages(text)
        full_response = ""
        raw_response = None

        try:
            stream = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            from vision_agents.core.llm.events import (
                LLMResponseChunkEvent,
                LLMResponseCompletedEvent,
            )

            async for chunk in stream:
                token = chunk.choices[0].delta.content
                if token:
                    full_response += token
                    raw_response = chunk  # keep last raw chunk as "original"

                    # Fire streaming event for any attached listeners
                    self.events.send(
                        LLMResponseChunkEvent(
                            plugin_name="groq",
                            delta=token,
                        )
                    )

            # Fire completion event
            self.events.send(
                LLMResponseCompletedEvent(
                    plugin_name="groq",
                    text=full_response,
                    model=self.model,
                )
            )

            logger.info("[GroqLLM] response(%s…)", full_response[:80])
            return LLMResponseEvent(original=raw_response, text=full_response)

        except Exception as exc:
            logger.error("[GroqLLM] error: %s", exc)
            # Return empty-text event with exception so Agent can handle it
            return LLMResponseEvent(original=None, text="", exception=exc)

    async def close(self) -> None:
        """Release the Groq HTTP client."""
        try:
            inner = getattr(self._client, "_client", None)
            if inner and hasattr(inner, "aclose"):
                await inner.aclose()
        except Exception as e:
            logger.warning("[GroqLLM] close warning: %s", e)
        await super().close()
