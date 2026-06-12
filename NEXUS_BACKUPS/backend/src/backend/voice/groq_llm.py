import os
import time
import json
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
from ..services.memory import memory_service
from ..config.settings import settings
from .tools.nexus_tools import (
    NEXUS_TOOL_DEFINITIONS,
    run_command,
    open_application,
    create_task,
    create_note,
    web_search
)
from .providers import nexus_log

logger = logging.getLogger("nexus.voice.llm")

class GroqLLM(LLM):
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.5,
        max_tokens: int = 1024,
        user_id: Optional[str] = None
    ):
        super().__init__()
        self.client = AsyncGroq(api_key=api_key or settings.GROQ_API_KEY)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.user_id = user_id or "nexus-user-default"
        
        # Map tool names to their implementation
        self.tool_map = {
            "run_command": run_command,
            "open_application": open_application,
            "create_task": lambda **kwargs: create_task(user_id=self.user_id, **kwargs),
            "create_note": lambda **kwargs: create_note(user_id=self.user_id, **kwargs),
            "web_search": web_search
        }

    async def simple_response(
        self,
        text: str,
        participant: Optional[Participant] = None,
    ) -> LLMResponseEvent[Any]:
        request_id = f"llm_{time.time()}"
        logger.info(f"LLM request: {request_id} | Input: '{text[:60]}...'")
        nexus_log(f"Processing input: '{text[:40]}...'", level="debug")
        
        self.events.send(
            LLMRequestStartedEvent(
                request_id=request_id,
                model=self.model,
                streaming=True,
            )
        )

        # 1. Fetch Context from Memory
        history = []
        if self.user_id:
            try:
                raw_history = await memory_service.get_recent_context(self.user_id, limit=40)
                # Reverse to get chronological order for LLM
                for msg in reversed(raw_history):
                    history.append({"role": msg["role"], "content": msg["content"]})
            except Exception as e:
                logger.warning(f"Memory load failed: {e}")

        # 2. Prepare Messages
        messages = [{"role": "system", "content": self._instructions}]
        messages.extend(history)
        messages.append({"role": "user", "content": text})

        start_time = time.perf_counter()

        try:
            # 3. First Call (Allow Tools)
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=NEXUS_TOOL_DEFINITIONS,
                tool_choice="auto",
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls

            # AI Thought Logging
            if not tool_calls and response_message.content:
                nexus_log("Formulating response...", level="ai")
            elif tool_calls:
                nexus_log(f"Logic sequence triggered: {len(tool_calls)} actions planned", level="ai")

            # 4. Handle Tool Execution
            if tool_calls:
                messages.append(response_message)
                for tool_call in tool_calls:
                    name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    
                    logger.info(f"🛠  TOOL_CALL: {name}({args})")
                    
                    if name in self.tool_map:
                        nexus_log(f"Executing system tool: {name}", level="info", data=args)
                        result = await self.tool_map[name](**args)
                        logger.info(f"✅ TOOL_RESULT: {result}")
                    else:
                        result = f"Error: Tool {name} not found."
                        logger.error(result)
                        nexus_log(f"Tool failure: {name} not found", level="error")

                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": name,
                        "content": result,
                    })

                # Second Call for Final Response
                stream = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    stream=True,
                )
            else:
                # No tools, but we need a stream for consistent UI behavior
                # Re-calling with stream=True
                stream = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    stream=True,
                )

            # 5. Stream Results
            full_text = ""
            first_token_time = None
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
            
            # 6. Persist interaction
            if self.user_id:
                await memory_service.save_interaction(self.user_id, "user", text)
                await memory_service.save_interaction(self.user_id, "assistant", full_text)

            self.events.send(
                LLMResponseCompletedEvent(
                    text=full_text,
                    item_id=request_id,
                    latency_ms=(end_time - start_time) * 1000,
                    time_to_first_token_ms=(
                        (first_token_time - start_time) * 1000 if first_token_time else None
                    ),
                    model=self.model,
                )
            )
            
            return LLMResponseEvent(original=None, text=full_text)

        except Exception as e:
            logger.error(f"❌ LLM error: {e}")
            raise

    async def close(self) -> None:
        pass

