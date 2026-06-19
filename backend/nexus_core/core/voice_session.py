# ==========================================
# CRITICAL SYSTEM FILE
# Do not modify websocket lifecycle, session cleanup,
# Gemini transport, or fallback routing without running
# full voice test suite. Changes here can silently break voice.
# ==========================================
import os
import asyncio
import logging
import json
import time
import io
import wave
import re
from collections import deque
from typing import Optional, List, Dict, Any, Deque

import numpy as np
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from speech_cleaner import cleaner as speech_cleaner
import core.global_state as gs
from core.gemini_live_manager import GeminiLiveSessionManager
from core.database import db
from core.output_processor import output_processor
from core.action_router import action_router
from tools.system import execute_pc_action
from core.capability_registry_def import CAPABILITY_MAP, CONFIRMATION_LABELS
from core.execution_hooks import wrap_execution, run_desktop_tool, run_browser_tool, broadcast_workspace_state
from tools.task_tools import create_task, create_note
from tools.memory_tools import update_preferences, get_user_memory, delete_user_preference
from tools.file_tools import read_file, write_file, read_directory
from tools.third_party_tools import get_weather
import core.rag_oracle as rag_oracle_module

# Split-out mixins
from core.session_state import SessionState, SessionStateMixin
from core.session_tts_worker import SessionTTSMixin

from silero_vad import VADIterator  # type: ignore

logger = logging.getLogger("nexus_ws")


class VoiceSession(SessionStateMixin, SessionTTSMixin):
    """
    Main session orchestrator.
    - SessionStateMixin  → SessionState enum, VAD processing, transcript/TTS sanitizers
    - SessionTTSMixin    → TTS worker, metrics worker, greeting, safe_send_json
    This class owns: __init__, lifecycle, run_pipeline, run_llm_and_tts, memory extraction.
    """

    def __init__(self, websocket: WebSocket, engine: str = "nexus", session_id: str = ""):
        self.session_id = session_id
        self.websocket = websocket
        self.engine = engine
        self.audio_buffer = bytearray()
        self.state = SessionState.IDLE
        self.current_task: Optional[str] = None

        self.last_audio_time: float = time.time()
        self.last_agent_speech_time: float = 0.0
        self.agent_is_speaking = False

        self.pipeline_lock = asyncio.Lock()
        self.debounce_task = None

        # --- Speech Orchestrator State ---
        self.current_turn_id: int = 0
        self.current_chunk_index: int = 0
        self.llm_is_streaming: bool = False
        self.tts_queue: asyncio.Queue = asyncio.Queue()
        self.is_connected: bool = True
        self.tts_worker_task = asyncio.create_task(self.tts_worker())
        self.metrics_worker_task = asyncio.create_task(self.metrics_worker())

        # --- VAD Timing Constants ---
        self.silence_threshold = 0.4
        self.min_speech_duration = 0.15
        self.barge_in_threshold = 0.6
        self.ambient_noise_level: float = 0.015
        self.turn_start_time: float = 0.0
        self.stt_latency: float = 0.0
        self.llm_latency: float = 0.0

        self.speech_start_time: float = 0.0
        self.has_greeted = False
        self.sample_rate = 16000

        # --- Session-scoped Voice Settings ---
        self.selected_provider: str = "piper"
        self.selected_persona: str = "female"
        self.selected_language: str = ""

        # --- Lifecycle Guards ---
        self.providers_ready = False
        self.last_state_change = time.time()
        self.echo_window_active = False
        self.echo_window_start = 0.0
        self.channels = 1
        self.sample_width = 2
        self.is_muted = False

        # --- Post-TTS Echo Guard ---
        self.post_tts_guard_time: float = 0.4
        self.post_tts_guard_until: float = 0.0

        self.vad_threshold_normal: float = 0.85
        self.vad_threshold_strict: float = 0.95

        self.vad_iterator = VADIterator(
            gs.vad_model,
            threshold=self.vad_threshold_normal,
            min_silence_duration_ms=500,
            speech_pad_ms=100
        )
        self.vad_chunk_buffer = bytearray()
        self.vad_preroll_buffer: Deque[bytes] = deque(maxlen=8)
        self.recent_ai_outputs: Deque[str] = deque(maxlen=3)
        self.conversation_history: Deque[dict] = deque(maxlen=16)

        # --- Gemini Live Integration ---
        self.gemini_manager = None
        if self.engine == "gemini_live":
            from prompts import get_gemini_live_system_instruction
            self.gemini_manager = GeminiLiveSessionManager(
                websocket=self.websocket,
                system_instruction=get_gemini_live_system_instruction(),
                session_id=self.session_id
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect_gemini(self):
        if self.gemini_manager:
            from prompts import get_gemini_live_system_instruction
            identity = await db.get_system_identity()
            self.gemini_manager.system_instruction = get_gemini_live_system_instruction(identity)

            async def on_agent_message(text):
                clean = output_processor.filter_reasoning(text)
                if clean:
                    await self.safe_send_json({"type": "agent_message", "text": clean})
                    self.conversation_history.append({"role": "assistant", "content": clean})
                    asyncio.create_task(db.save_message(self.session_id, "assistant", clean))

            async def on_disconnect():
                logger.warning("🔄 Falling back to Nexus STT (Groq) engine")
                self.engine = "nexus"
                await self.safe_send_json({"type": "engine_mode", "mode": "groq"})

            await self.gemini_manager.connect(on_agent_message, on_disconnect)

    async def update_workspace_state(self, active_capability=None, status="idle", verification_state=None):
        await broadcast_workspace_state(
            active_capability=active_capability,
            status=status,
            verification_state=verification_state,
            current_task=getattr(self, "current_task", None)
        )

    async def stop(self):
        """Cleanup resources."""
        self.is_connected = False
        self.tts_worker_task.cancel()
        self.metrics_worker_task.cancel()
        try:
            await self.tts_worker_task
        except asyncio.CancelledError:
            pass
        try:
            await self.metrics_worker_task
        except asyncio.CancelledError:
            pass
        logger.info("🛑 VoiceSession stopped.")

    async def start_response(self):
        pass

    # ------------------------------------------------------------------
    # Debounce
    # ------------------------------------------------------------------

    async def debounce_turn(self):
        """Waits for stable silence before triggering the pipeline."""
        try:
            await asyncio.sleep(self.silence_threshold)
            if self.state == SessionState.DEBOUNCE:
                logger.info("🏁 [Turn] Finalizing turn...")
                self._change_state(SessionState.THINKING)
                self.current_turn_id += 1
                self.turn_start_time = time.perf_counter()
                await self.run_pipeline()
        except asyncio.CancelledError:
            pass

    # ------------------------------------------------------------------
    # Memory extraction (background)
    # ------------------------------------------------------------------

    async def extract_and_save_memory(self, user_msg: str, ai_msg: str, turn_id: int = 0):
        """Background task to extract and persist user preferences."""
        try:
            import core.lance_memory as lance_memory_module
            mem = await lance_memory_module.get_memory()
            if mem is not None:
                await mem.add_memory(
                    text=f"User: {user_msg}\nAssistant: {ai_msg}",
                    metadata={"type": "conversation_turn", "turn_id": turn_id, "timestamp": time.time()}
                )

            if gs.llm_provider is None:
                return

            from tools.memory_tools import MEMORY_TOOLS
            messages = [
                {"role": "system", "content": (
                    "You are a memory extractor. If the user explicitly states a preference, "
                    "a rule for how you should behave, a fact about themselves, or a request to "
                    "remember something, call the update_preferences tool. If not, output 'NO_PREF'."
                )},
                {"role": "user", "content": f"User: {user_msg}\nAssistant: {ai_msg}"}
            ]

            resp = await gs.llm_provider.client.chat.completions.create(  # type: ignore
                messages=messages,  # type: ignore
                model="llama-3.1-8b-instant",
                tools=MEMORY_TOOLS,  # type: ignore
                tool_choice="auto",
                temperature=0.1
            )

            msg = resp.choices[0].message
            if msg.tool_calls:
                for tool_call in msg.tool_calls:
                    if tool_call.function.name == "update_preferences":
                        args = json.loads(tool_call.function.arguments)
                        if "preferences" in args:
                            res = await update_preferences(args["preferences"])
                            logger.info(f"🧠 [Memory Updated] {res}")
        except Exception as e:
            logger.error(f"❌ [Memory Extractor] Error: {e}")

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    # ACTION KEYWORDS: force tool routing for these intents without LLM judgment
    _ACTION_KEYWORDS = (
        "open ", "launch ", "start ", "run ",
        "close ", "kill ", "quit ", "shut down ",
        "minimize ", "maximize ",
        "take a screenshot", "screenshot",
        "type ", "press ", "click ", "opem ",
    )

    async def run_pipeline(self):
        if self.pipeline_lock.locked():
            self.audio_buffer.clear()
            return

        async with self.pipeline_lock:
            if len(self.audio_buffer) < 3200:  # Min 200ms
                self.audio_buffer.clear()
                return
            raw_audio = bytes(self.audio_buffer)
            self.audio_buffer.clear()

        try:
            # Normalize
            samples: np.ndarray = np.frombuffer(raw_audio, dtype=np.int16).astype(np.float32)
            max_val = float(np.max(np.abs(samples)))
            if max_val > 0:
                samples = samples * (28000.0 / max_val)
            audio_to_process = samples.astype(np.int16).tobytes()

            duration_sec = len(audio_to_process) / (self.sample_rate * self.channels * self.sample_width)
            logger.info(f"🛰 [STT] Dispatching {duration_sec:.1f}s ({len(audio_to_process)} bytes)")

            stt_start_time = time.perf_counter()
            with io.BytesIO() as wav_io:
                with wave.open(wav_io, "wb") as wav_file:
                    wav_file.setnchannels(self.channels)
                    wav_file.setsampwidth(self.sample_width)
                    wav_file.setframerate(self.sample_rate)
                    wav_file.writeframes(audio_to_process)
                wav_data = wav_io.getvalue()

            multilingual_prompt = (
                "English, Hindi, and Marathi conversation. Technical AI assistant context. "
                "User may use Hinglish or Marathi speech. "
                "Examples: 'kaise ho?', 'kya chal raha hai?', 'काय चाललंय?', 'Show me code.', 'explain this'."
            )

            if gs.stt_provider is None:
                raise RuntimeError("STT provider not initialized — startup lifecycle may have failed")

            try:
                transcription = await gs.stt_provider.client.audio.transcriptions.create(
                    file=("audio.wav", wav_data),
                    model="whisper-large-v3",
                    response_format="verbose_json",
                    prompt=multilingual_prompt
                )
            except Exception as e:
                logger.warning(f"⚠️ [STT] Groq failed: {e}. Falling back to Gemini.")
                from google import genai
                from google.genai import types
                gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
                resp = await asyncio.to_thread(
                    gemini_client.models.generate_content,
                    model="gemini-2.5-flash",
                    contents=[
                        types.Part.from_bytes(data=wav_data, mime_type="audio/wav"),
                        types.Part.from_text(text=(
                            "Transcribe the audio exactly. Output ONLY the transcription text. "
                            "Do not answer questions. Ensure Indian languages (Hindi, Marathi) "
                            "are transcribed accurately if detected."
                        ))
                    ]
                )

                class MockTranscription:
                    def __init__(self, text):
                        self.text = text or ""

                transcription = MockTranscription(text=resp.text)

            self.stt_latency = time.perf_counter() - stt_start_time

            # Extract text safely
            if hasattr(transcription, "text"):
                transcript_text = transcription.text.strip()
            elif isinstance(transcription, dict):
                transcript_text = transcription.get("text", "").strip()
            else:
                transcript_text = str(transcription).strip()

            # Confidence filter on verbose_json segments
            segments = getattr(transcription, "segments", []) or (
                transcription.get("segments", []) if isinstance(transcription, dict) else []
            )
            if segments:
                def get_val(s, key):
                    if isinstance(s, dict): return s.get(key, 0)
                    return getattr(s, key, 0)

                total_no_speech = sum(float(get_val(s, "no_speech_prob") or 0) for s in segments)
                total_logprob   = sum(float(get_val(s, "avg_logprob") or 0) for s in segments)
                avg_no_speech = total_no_speech / len(segments)
                avg_logprob   = total_logprob   / len(segments)

                if avg_no_speech > 0.6 or avg_logprob < -1.0:
                    logger.warning(
                        f"🗑 [STT] Rejecting hallucination "
                        f"(no_speech_prob: {avg_no_speech:.2f}, avg_logprob: {avg_logprob:.2f})"
                    )
                    return

            transcript = self.sanitize_transcript(transcript_text)
            if not transcript or len(transcript) < 2:
                logger.info(f"🗑 Rejected suspect transcript: {transcript}")
                return

            transcript = await speech_cleaner.clean(transcript)
            logger.info(f"📝 Final STT Text: '{transcript}'")

            if not transcript or len(transcript) < 2:
                logger.info("🗑 Rejected transcript after cleanup.")
                return

            # Phase 8: Echo Cancellation
            from difflib import SequenceMatcher
            for recent_out in self.recent_ai_outputs:
                clean_t = transcript.lower().strip()
                clean_r = recent_out.lower().strip()
                similarity = SequenceMatcher(None, clean_t, clean_r).ratio()
                if clean_t in clean_r or similarity > 0.7:
                    logger.warning(
                        f"🔇 [Echo] Dropped transcript '{transcript}' matching AI output '{recent_out}'"
                    )
                    return

            logger.info(f"💬 [STT] User: {transcript}")
            self.current_task = transcript
            await self.update_workspace_state(status="running")
            await self.safe_send_json({"type": "user_transcript", "text": transcript})

            self.current_turn_id += 1
            self.current_chunk_index = 0
            await self.run_llm_and_tts(transcript, turn_id=self.current_turn_id)
            logger.info(f"✅ Pipeline complete for Turn {self.current_turn_id}.")

        except WebSocketDisconnect:
            logger.warning("🔌 Client disconnected during pipeline")
            self.is_connected = False
            raise
        except Exception as e:
            logger.error(f"❌ Pipeline Error: {e}")
            if self.is_connected:
                await self.safe_send_json({"type": "error", "message": str(e)})

    # ------------------------------------------------------------------
    # LLM + TTS streaming
    # ------------------------------------------------------------------

    async def run_llm_and_tts(self, transcript: str, turn_id: int):
        """Streams LLM response and semantic-chunks it for TTS."""
        logger.info(f"🧠 [Turn {turn_id}] LLM processing: {transcript[:50]}...")
        self.llm_is_streaming = True
        self.agent_is_speaking = True

        try:
            full_ai_text = ""
            current_sentence = ""

            from prompts import get_nexus_system_prompt
            identity = await db.get_system_identity()
            memory_data = await db.get_all_memory()
            memory_context = json.dumps(memory_data, indent=2) if any(memory_data.values()) else "{}"
            system_prompt = get_nexus_system_prompt(identity, memory_context)

            if gs.llm_provider is None:
                raise RuntimeError("LLM provider not initialized")

            llm_start_time = time.perf_counter()

            self.conversation_history.append({"role": "user", "content": transcript})
            messages = [{"role": "system", "content": system_prompt}] + list(self.conversation_history)
            asyncio.create_task(db.save_message(self.session_id, "user", transcript))

            from core.trace_emitter import emit_trace
            await emit_trace(self.websocket, "user_command", f"Command: {transcript}", "🗣️")
            await emit_trace(self.websocket, "model_selected", f"Model routing: {gs.llm_provider.model}", "🧠")

            from tools.system import get_dynamic_system_tools
            from tools.file_tools import FILE_TOOLS
            from tools.task_tools import TASK_TOOLS
            from tools.memory_tools import MEMORY_TOOLS
            from tools.third_party_tools import THIRD_PARTY_TOOLS
            from tools.scrapper_tools import SCRAPPER_TOOLS
            from tools.browser_tools import BROWSER_TOOLS
            from core.capabilities import registry as cap_registry
            from core.registry import tool_registry

            dynamic_system_tools = await get_dynamic_system_tools()
            ALL_TOOLS = (
                dynamic_system_tools + FILE_TOOLS + TASK_TOOLS
                + MEMORY_TOOLS + THIRD_PARTY_TOOLS + SCRAPPER_TOOLS + BROWSER_TOOLS
            )

            # --- FORCED TOOL ROUTING ---
            action_intent = await action_router.route_intent(transcript)

            if action_intent:
                logger.info(f"🎯 [ACTION ROUTER] Intercepted intent: '{transcript[:50]}'")
                action = action_intent["tool"]
                params = {"target": action_intent.get("target", "")}

                await emit_trace(self.websocket, "tool_selected", f"Selected tool: {action}", "🛠️", params)
                perm = await cap_registry.check_permission("default_user", action)
                res = {"success": False, "error": "Unknown action"}

                if perm == "Deny":
                    confirmation = "That capability is currently disabled. Enable it in Settings."
                elif perm == "Prompt":
                    await self.safe_send_json({
                        "type": "permission_request",
                        "tool_id": action,
                        "parameters": params
                    })
                    return
                else:
                    cap_def = CAPABILITY_MAP.get(action)
                    if action.startswith("pc_"):
                        # Use target_param from the registry — no hardcoded if/elif lists
                        tool_params = {}
                        if cap_def and cap_def.target_param:
                            tool_params[cap_def.target_param] = params.get("target", "")
                        # Phase 4: mandatory execution hook — timing + contract validate + verification DB write
                        res = await run_desktop_tool(
                            action,
                            params.get("target", ""),
                            execute_pc_action(action, tool_params),
                        )
                    elif action.startswith("browser_"):
                        from tools.browser_tools import execute_browser_action
                        browser_params = {
                            "url": params.get("target", ""),
                            "query": params.get("target", ""),
                            "target": params.get("target", ""),
                            "selector": params.get("target", ""),
                            "text": params.get("target", ""),
                            "action": params.get("target", "")
                        }
                        res = await run_browser_tool(
                            action,
                            params.get("target", ""),
                            execute_browser_action(action, browser_params),
                        )

                    target_name = params.get("target", "").title()
                    if res.get("success"):
                        # Build confirmation from the registry template — no inline labels needed
                        template = CONFIRMATION_LABELS.get(action, "Done.")
                        if cap_def and cap_def.target_param and target_name:
                            confirmation = template.replace("{target}", target_name)
                        else:
                            confirmation = template.replace(" {target}.", ".").replace("{target}", "").strip() or "Done."
                    else:
                        confirmation = f"I couldn't do that. {res.get('error', '')}"

                await emit_trace(self.websocket, "tool_result", confirmation, "✅")
                await cap_registry.log_execution(
                    action, params,
                    "success" if perm == "Allow" and res.get("success") else "failed",
                    perm
                )
                await self.safe_send_json({"type": "agent_message", "text": confirmation, "is_final": True})
                self.conversation_history.append({"role": "assistant", "content": confirmation})
                await self.enqueue_tts(confirmation, turn_id=turn_id)
                await self.tts_queue.put({"text": "", "turn_id": turn_id, "is_sentinel": True})
                await self.update_workspace_state(status="completed")
                return

            # If engine is Gemini Live and CHAT intent, delegate
            if self.engine == "gemini_live" and self.gemini_manager and self.gemini_manager.is_connected:
                logger.info("🧠 [Gemini Live] Delegating CHAT intent to Gemini Live.")
                await self.gemini_manager.send_text(transcript, turn_complete=True)
                return

            # --- Tool detection via standard LLM ---
            try:
                tool_response = await gs.llm_provider.client.chat.completions.create(  # type: ignore
                    messages=messages,  # type: ignore
                    model=gs.llm_provider.model,
                    tools=ALL_TOOLS,  # type: ignore
                    tool_choice="auto",
                    temperature=0.1,
                    max_tokens=256
                )
                tool_msg = tool_response.choices[0].message
                if tool_msg.tool_calls:
                    tool_call = tool_msg.tool_calls[0]
                    action = tool_call.function.name
                    params = json.loads(tool_call.function.arguments)

                    await emit_trace(self.websocket, "tool_selected", f"Selected tool: {action}", "🛠️", params)
                    perm = await cap_registry.check_permission("default_user", action)

                    if perm == "Deny":
                        confirmation = "That capability is currently disabled. Enable it in Settings."
                        await cap_registry.log_execution(action, params, "denied", perm)
                        await emit_trace(self.websocket, "execution_complete", f"Denied: {action}", "❌")
                    elif perm == "Prompt":
                        await self.safe_send_json({
                            "type": "capability_prompt",
                            "tool_id": action,
                            "params": params
                        })
                        confirmation = "I need permission to perform that action. Please check your screen."
                        await cap_registry.log_execution(action, params, "prompted", perm)
                        await emit_trace(self.websocket, "execution_started", f"Requesting permission: {action}", "🛡️")
                    else:
                        await cap_registry.log_execution(action, params, "started", perm)
                        await emit_trace(self.websocket, "execution_started", f"Executing: {action}", "⏳")

                        # Phase 4: mandatory execution hook for all LLM-dispatched tools
                        if action.startswith("pc_"):
                            contract_result = await run_desktop_tool(
                                action,
                                params.get("app_name", params.get("target", "")),
                                execute_pc_action(action, params),
                            )
                        elif action.startswith("browser_"):
                            from tools.browser_tools import execute_browser_action
                            contract_result = await run_browser_tool(
                                action,
                                params.get("url", params.get("query", params.get("target", ""))),
                                execute_browser_action(action, params),
                            )
                        else:
                            contract_result = await wrap_execution(
                                action,
                                str(list(params.values())[:1]),
                                tool_registry.execute(action, params, ["admin"]),
                                category="other",
                            )

                        status = "success" if contract_result.get("success") else "failed"
                        await cap_registry.log_execution(action, params, status, perm)
                        logger.info(f"🛠 Tool executed: {action}({params}) → {contract_result}")
                        await emit_trace(
                            self.websocket, "execution_complete",
                            f"Execution {status}",
                            "✅" if status == "success" else "⚠️",
                            contract_result
                        )

                        if contract_result.get("success") and contract_result.get("verified"):
                            confirmation = str(contract_result.get("result", "Done."))
                        elif contract_result.get("success"):
                            confirmation = "Action attempted, but could not be verified."
                        else:
                            confirmation = f"Failed to perform action: {contract_result.get('error', 'Unknown error')}"

                    self.conversation_history.append({"role": "assistant", "content": confirmation})
                    asyncio.create_task(db.save_message(self.session_id, "assistant", confirmation))
                    await self.safe_send_json({"type": "agent_message", "text": confirmation, "is_final": True})
                    await self.enqueue_tts(confirmation, turn_id=turn_id, is_last=True)
                    await self.update_workspace_state(status="completed")
                    return

            except Exception as tool_err:
                logger.debug(f"Tool detection skipped: {tool_err}")

            # --- Standard LLM streaming (Groq → Gemini fallback) ---
            async def gemini_stream():
                from google import genai
                from google.genai import types
                async_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
                gemini_messages = []
                for msg in messages:
                    if msg["role"] != "system":
                        role = "user" if msg["role"] == "user" else "model"
                        gemini_messages.append(
                            types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])])
                        )
                config = types.GenerateContentConfig(system_instruction=system_prompt, temperature=0.7)
                stream = await async_client.aio.models.generate_content_stream(
                    model="gemini-2.5-flash",
                    contents=gemini_messages,
                    config=config
                )
                async for chunk in stream:
                    yield chunk.text or ""

            try:
                groq_stream = await gs.llm_provider.client.chat.completions.create(  # type: ignore
                    messages=messages,  # type: ignore
                    model=gs.llm_provider.model,
                    temperature=0.7,
                    stream=True
                )
                async def unified_stream():
                    async for chunk in groq_stream:
                        yield chunk.choices[0].delta.content or ""
                active_stream = unified_stream()
            except Exception as e:
                logger.warning(f"⚠️ [LLM] Groq failed: {e}. Falling back to Gemini.")
                active_stream = gemini_stream()

            # Semantic TTS chunking
            SENTENCE_ENDS = {".", "?", "!", "\n", "।"}
            MAX_BUFFER_CHARS = 10000

            async for content in active_stream:
                if turn_id != self.current_turn_id:
                    logger.warning(f"🛑 [LLM] Turn {turn_id} superseded. Stopping stream.")
                    return

                if content:
                    full_ai_text += content
                    current_sentence += content

                    last_char = content.rstrip()[-1] if content.strip() else ""
                    is_boundary = last_char in SENTENCE_ENDS or last_char == "\n"
                    is_long = len(current_sentence) >= MAX_BUFFER_CHARS

                    if is_boundary or is_long:
                        text_to_queue = current_sentence.strip()
                        text_to_queue = output_processor.filter_reasoning(text_to_queue) or ""
                        if text_to_queue and re.search(r'[a-zA-Z\u0900-\u097f]', text_to_queue):
                            await self.safe_send_json({
                                "type": "agent_partial", "text": text_to_queue, "turn_id": turn_id
                            })
                            self.recent_ai_outputs.append(text_to_queue)
                            await self.enqueue_tts(text_to_queue, turn_id=turn_id)
                        current_sentence = ""

            # Final flush
            if current_sentence.strip():
                text_to_queue = output_processor.filter_reasoning(current_sentence.strip()) or ""
                if text_to_queue and re.search(r'[a-zA-Z\u0900-\u097f]', text_to_queue):
                    await self.safe_send_json({
                        "type": "agent_partial", "text": text_to_queue, "turn_id": turn_id
                    })
                    self.recent_ai_outputs.append(text_to_queue)
                    await self.enqueue_tts(text_to_queue, turn_id=turn_id)

            # Sentinel to signal TTS end-of-stream
            await self.tts_queue.put({"text": "", "turn_id": turn_id, "is_sentinel": True})

            self.llm_latency = time.perf_counter() - llm_start_time
            full_ai_text = output_processor.filter_reasoning(full_ai_text) or ""
            logger.info(f"⚡ [LLM] Turn {turn_id} completed in {self.llm_latency:.2f}s")
            self.conversation_history.append({"role": "assistant", "content": full_ai_text})
            asyncio.create_task(db.save_message(self.session_id, "assistant", full_ai_text.strip()))
            await self.safe_send_json({"type": "agent_message", "text": full_ai_text.strip(), "is_final": True})
            logger.info(f"🤖 Nexus Full Response: {full_ai_text[:100]}...")
            asyncio.create_task(self.extract_and_save_memory(transcript, full_ai_text.strip(), turn_id=turn_id))
            await self.update_workspace_state(status="completed")

        except Exception as e:
            logger.error(f"❌ LLM Pipeline Error: {e}")
            await self.tts_queue.put({"text": "", "turn_id": turn_id, "is_sentinel": True})
        finally:
            self.llm_is_streaming = False
            logger.info(f"🧠 [Turn {turn_id}] LLM stream finished.")
