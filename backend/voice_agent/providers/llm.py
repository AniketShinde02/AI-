import os
import time
import logging
from typing import Any, Dict, List, Optional, Tuple

from groq import AsyncGroq
from vision_agents.core.llm.llm import LLM, LLMResponseEvent
from vision_agents.core.llm.events import (
    LLMRequestStartedEvent,
    LLMResponseChunkEvent,
    LLMResponseCompletedEvent,
)
from vision_agents.core.edge.types import Participant

logger = logging.getLogger(__name__)

class GroqLLM(LLM):
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "llama-3.1-70b-versatile",
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ):
        super().__init__()
        if not api_key:
            api_key = os.environ.get("GROQ_API_KEY")
        
        self.client = AsyncGroq(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def simple_response(
        self,
        text: str,
        participant: Optional[Participant] = None,
    ) -> LLMResponseEvent[Any]:
        request_id = str(time.time())
        self.events.send(
            LLMRequestStartedEvent(
                request_id=request_id,
                model=self.model,
                streaming=True,
            )
        )

        messages = [
            {"role": "system", "content": self._instructions},
        ]
        
        # Add conversation history if available
        if self._conversation:
            history = await self._conversation.get_messages()
            for msg in history:
                messages.append({"role": msg.role, "content": msg.content})
        
        messages.append({"role": "user", "content": text})

        start_time = time.perf_counter()
        first_token_time = None
        full_text = ""

        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
            )

            async for chunk in stream:
                if first_token_time is None:
                    first_token_time = time.perf_counter()
                
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    full_text += delta
                    self.events.send(
                        LLMResponseChunkEvent(
                            delta=delta,
                            item_id=request_id,
                            is_first_chunk=(first_token_time == time.perf_counter()),
                        )
                    )

            end_time = time.perf_counter()
            
            completed_event = LLMResponseCompletedEvent(
                text=full_text,
                item_id=request_id,
                latency_ms=(end_time - start_time) * 1000,
                time_to_first_token_ms=(
                    (first_token_time - start_time) * 1000 if first_token_time else None
                ),
                model=self.model,
            )
            self.events.send(completed_event)
            
            return LLMResponseEvent(original=None, text=full_text)

        except Exception as e:
            logger.error(f"Groq LLM error: {e}")
            raise

    async def close(self) -> None:
        # AsyncGroq doesn't strictly need a close() usually but good practice if available
        pass
