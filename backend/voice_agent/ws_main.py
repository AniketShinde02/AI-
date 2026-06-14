import os
import asyncio
import logging
import json
import base64
import time
import wave
import io
import re
from enum import Enum
from typing import Optional, Deque
from contextlib import asynccontextmanager
from collections import deque
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import psutil
import platform
import random

# Re-use existing provider logic
from providers.stt import GroqSTT
from providers.llm import GroqLLM
from providers.tts import TTSProviderRouter, ProviderStatus
import torch # type: ignore
from silero_vad import load_silero_vad, VADIterator # type: ignore

# Import Backend Tools for Gemini Live Bridge
from tools.system import run_command, open_application
from tools.task_tools import create_task, create_note
from tools.memory_tools import update_preferences, get_user_memory, delete_user_preference
from memory_manager import load_memory
from tools.file_tools import read_file, write_file, read_directory
from tools.third_party_tools import get_weather
from core.rag_oracle import RAGOracle, oracle_instance
import core.rag_oracle as rag_oracle_module

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nexus.ws")

from dotenv import load_dotenv, find_dotenv
# Automatically find .env in parent directories
load_dotenv(find_dotenv(usecwd=True))

# Import config
import config

# Initialize Providers as None, will be set in lifespan startup
stt_provider: Optional[GroqSTT] = None
llm_provider: Optional[GroqLLM] = None
tts_router: Optional[TTSProviderRouter] = None
vad_model = None

import pickle
import os

# Global state for greeting cache
cached_greeting_pcm: list = []
CACHE_FILE = "greeting_cache.pkl"

if os.path.exists(CACHE_FILE):
    try:
        with open(CACHE_FILE, "rb") as f:
            cached_greeting_pcm = pickle.load(f)
            print("✅ Loaded cached greeting from disk.")
    except Exception as e:
        print(f"❌ Failed to load greeting cache: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    global stt_provider, llm_provider, tts_router, vad_model
    logger.info("🚀 Starting Nexus Voice Providers...")
    try:
        stt_provider = GroqSTT(api_key=str(config.GROQ_API_KEY))
        llm_provider = GroqLLM(api_key=str(config.GROQ_API_KEY))
        tts_router = TTSProviderRouter(config)
        vad_model = load_silero_vad()
        rag_oracle_module.oracle_instance = RAGOracle(
            gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),
            groq_api_key=str(config.GROQ_API_KEY)
        )
        logger.info(f"✅ Providers initialized. Silero VAD loaded. RAG Oracle initialized.")
    except Exception as e:
        logger.error(f"❌ Critical failure during provider initialization: {e}")
        # We allow startup but session handlers must check readiness
    yield
    # Shutdown: nothing to explicitly close for these providers

app = FastAPI(title="Nexus Voice WebSocket", lifespan=lifespan)

# Add CORS middleware for frontend to call /execute-tool
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check — stops browser probe 404 log noise."""
    return {"status": "ok", "service": "Nexus Voice Backend", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Explicit health endpoint for monitoring."""
    return {"status": "ok", "providers": {
        "stt": stt_provider is not None,
        "llm": llm_provider is not None,
        "tts": tts_router is not None,
        "vad": vad_model is not None,
    }}

@app.get("/memory")
async def get_memory_api():
    """Returns the long-term persistent user memory."""
    return load_memory()


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
            elif name == "get_user_memory":
                out = await get_user_memory()
                results.append({"output": out})
            elif name == "delete_user_preference":
                out = await delete_user_preference(args.get("category", ""), args.get("key", ""))
                results.append({"category": args.get("category"), "key": args.get("key"), "output": out})
            elif name == "read_file":
                out = await read_file(args.get("file_path", ""))
                results.append({"file_path": args.get("file_path"), "output": out})
            elif name == "write_file":
                out = await write_file(args.get("file_name", ""), args.get("content", ""))
                results.append({"file_name": args.get("file_name"), "output": out})
            elif name == "read_directory":
                out = await read_directory(args.get("directory_path", ""))
                results.append({"directory_path": args.get("directory_path"), "output": out})
            elif name == "get_weather":
                out = await get_weather(args.get("city", ""))
                results.append({"city": args.get("city"), "output": out})
            elif name == "ingest_codebase":
                if rag_oracle_module.oracle_instance:
                    out = await rag_oracle_module.oracle_instance.ingest_codebase(args.get("dir_path", ""))
                    results.append({"dir_path": args.get("dir_path"), "output": out})
                else:
                    results.append({"error": "RAG Oracle not initialized"})
            elif name == "consult_oracle":
                if rag_oracle_module.oracle_instance:
                    out = await rag_oracle_module.oracle_instance.consult_oracle(args.get("query", ""))
                    results.append({"query": args.get("query"), "output": out})
                else:
                    results.append({"error": "RAG Oracle not initialized"})
            else:
                results.append({"status": "unknown_tool"})
                
        return {"status": "success", "results": results}
    except Exception as e:
        logger.exception(f"❌ Tool Execution failed: {e}")
        return {"status": "error", "error": str(e)}

class SessionState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    DEBOUNCE = "debounce" # Silence detected, waiting to finalize turn
    THINKING = "thinking" # Processing STT/LLM
    SPEAKING = "speaking" # AI is outputting audio

class VoiceSession:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.audio_buffer = bytearray()
        self.state = SessionState.IDLE
        
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
        # 0.4s sweet spot: minimizes latency without cutting off "umm"s
        self.silence_threshold = 0.4      # Was 1.2s
        self.min_speech_duration = 0.15   # Catch short words like "yes/no"
        self.barge_in_threshold = 0.6     # Sustained user speech required to interrupt AI
        self.ambient_noise_level: float = 0.0
        
        # Latency tracking
        self.turn_start_time: float = 0.0
        self.stt_latency: float = 0.0
        self.llm_latency: float = 0.0
        
        self.speech_start_time: float = 0.0
        self.has_greeted = False
        self.current_turn_id: int = 0
        self.sample_rate = 16000
        
        # --- Session-scoped Voice Settings (always explicit, never lazy hasattr) ---
        # These are updated live via 'settings' WebSocket messages
        self.selected_provider: str = "piper"     # Piper is primary
        self.selected_persona: str = "female"     # gender: 'male' | 'female'
        self.selected_language: str = ""          # '' = auto-detect from speech

        # --- Lifecycle Guards ---
        self.providers_ready = False
        self.last_state_change = time.time()
        self.echo_window_active = False
        self.echo_window_start = 0.0
        self.channels = 1
        self.sample_width = 2
        self.is_muted = False

        # --- Post-TTS Echo Guard ---
        # After last audio chunk is sent, we block VAD for this many seconds
        # regardless of whether the client sends audio_finished early.
        self.post_tts_guard_time: float = 0.4   # Was 1.8s
        self.post_tts_guard_until: float = 0.0  # epoch timestamp; 0 = guard inactive
        self.vad_threshold_normal: float = 0.3
        self.vad_threshold_strict: float = 0.6  # raised threshold during post-speech window

        self.vad_iterator = VADIterator(vad_model, threshold=self.vad_threshold_normal)
        self.vad_chunk_buffer = bytearray()
        self.vad_preroll_buffer: Deque[bytes] = deque(maxlen=50) # ~2-3 seconds context
        self.recent_ai_outputs: Deque[str] = deque(maxlen=3) # Phase 8 Echo Cancellation

    async def tts_worker(self):
        """Background worker to synthesize and send audio from the queue sequentially."""
        logger.info("👷 TTS Worker started.")
        try:
            while self.is_connected:
                # Wait for a sentence to process
                item = await self.tts_queue.get()
                if item is None: break 
                
                # Check for router readiness
                if tts_router is None or tts_router.status != ProviderStatus.READY:
                    logger.error("❌ [Worker] TTS router not ready. Waiting...")
                    await asyncio.sleep(1)
                    self.tts_queue.put_nowait(item) # Re-queue
                    self.tts_queue.task_done()
                    continue

                # New item format: {"text": str, "turn_id": int, "index": int}
                text = item.get("text", "")
                turn_id = item.get("turn_id", 0)
                chunk_index = item.get("index", 0)
                
                # Check if this item is from a stale turn
                if turn_id != self.current_turn_id:
                    logger.info(f"🗑 [Worker] Skipping stale chunk from Turn {turn_id}")
                    self.tts_queue.task_done()
                    continue

                if item.get("is_sentinel"):
                    logger.info(f"🏁 [Worker] All audio for Turn {turn_id} sent. Signaling tts_end.")
                    if self.is_connected and turn_id == self.current_turn_id:
                        await self.safe_send_json({
                            "type": "tts_end",
                            "turn_id": turn_id
                        })
                    self.tts_queue.task_done()
                    continue

                try:
                    self.agent_is_speaking = True
                    
                    if tts_router is None:
                        logger.error("❌ [Worker] TTS router is None")
                        break
                        
                    # Pass session voice settings — read directly, no hasattr checks
                    kwargs = {
                        "gender":   self.selected_persona,
                        "language": self.selected_language,
                    }
                    # Phase 3 & 4: Language Routing and forcing Gemini
                    provider_name = "gemini" # Mode 1 TTS
                    is_indian = bool(re.search(r'[\u0900-\u097f]', text)) or self.selected_language in ["hi", "mr"]
                    
                    if is_indian and self.selected_language != "mr":
                        kwargs["language"] = "hi"
                    elif is_indian and self.selected_language == "mr":
                        kwargs["language"] = "mr"
                    else:
                        kwargs["language"] = "en"
                        
                    tts_start_time = time.perf_counter()
                    audio_gen = await tts_router.stream_audio(text, provider=provider_name, **kwargs)
                    if audio_gen:
                        audio_buffer = b""
                        # 6400 bytes = 200ms of audio @ 16kHz s16le
                        # Significantly lower latency TTFA while still large enough to avoid OS-level buffer thrashing
                        BUFFER_SIZE = 6400

                        async for pcm_data in audio_gen:
                            # Stale check during synthesis
                            if not self.is_connected or turn_id != self.current_turn_id:
                                logger.info("⏹ [Worker] Turn superseded or disconnected, stopping...")
                                break

                            audio_buffer += pcm_data.samples.tobytes()

                            if len(audio_buffer) >= BUFFER_SIZE:
                                if self.state != SessionState.SPEAKING:
                                    tts_latency = time.perf_counter() - tts_start_time
                                    total_latency = time.perf_counter() - self.turn_start_time
                                    logger.info(f"[STT] {self.stt_latency*1000:.0f}ms")
                                    logger.info(f"[LLM] {self.llm_latency*1000:.0f}ms")
                                    logger.info(f"[TTS] {tts_latency*1000:.0f}ms")
                                    logger.info(f"[TOTAL] {total_latency*1000:.0f}ms")
                                    self._change_state(SessionState.SPEAKING)
                                    self.echo_window_active = True
                                    self.echo_window_start = time.time()
                                    logger.info("📢 [Audio] Agent speech started. Echo window active.")

                                self.current_chunk_index += 1
                                await self.safe_send_json({
                                    "type": "audio_chunk",
                                    "data": base64.b64encode(audio_buffer).decode('utf-8'),
                                    "meta": {
                                        "turn_id": turn_id,
                                        "chunk_index": self.current_chunk_index,
                                        "is_last": False
                                    }
                                })
                                audio_buffer = b""
                                self.last_agent_speech_time = time.time()

                        # Send final remaining buffer for this sentence — never mark as is_last
                        # because more sentences might be in the queue.
                        if self.is_connected and turn_id == self.current_turn_id:
                            self.current_chunk_index += 1
                            logger.info(f"📤 [Worker] Final chunk {self.current_chunk_index} for Turn {turn_id} ({len(audio_buffer)} bytes)")
                            await self.safe_send_json({
                                "type": "audio_chunk",
                                "data": base64.b64encode(audio_buffer).decode('utf-8'),
                                "meta": {
                                    "turn_id": turn_id,
                                    "chunk_index": self.current_chunk_index,
                                    "is_last": False
                                }
                            })
                            self.last_agent_speech_time = time.time()
                            # Arm the post-TTS echo guard the moment the last audio byte leaves.
                            # This is the only reliable signal — client ACK can arrive early or late.
                            self.post_tts_guard_until = time.time() + self.post_tts_guard_time
                            logger.info(f"🛡️ [Guard] Post-TTS echo guard armed for {self.post_tts_guard_time:.1f}s (until +{self.post_tts_guard_time:.1f}s)")
                except Exception as e:
                    logger.error(f"❌ [Worker] Error synthesizing Turn {turn_id}: {e}")
                    if self.is_connected:
                        await self.safe_send_json({
                            "type": "error",
                            "message": f"Speech synthesis failed: {e}"
                        })
                finally:
                    self.tts_queue.task_done()

        except Exception as e:
            logger.error(f"❌ TTS Worker crashed: {e}")
        finally:
            logger.info("👷 TTS Worker stopped.")

    async def metrics_worker(self):
        """Streams system metrics to the client every 1.5 seconds."""
        logger.info("📊 Metrics Worker started.")
        try:
            while self.is_connected:
                await asyncio.sleep(1.5)
                cpu = psutil.cpu_percent()
                mem = psutil.virtual_memory().percent
                os_name = f"{platform.system()} {platform.release()}"
                
                # Mock temperature and network metrics for UI
                temp = min((cpu / 100.0) * 40 + 40 + random.uniform(-2, 2), 90.0)
                ping = random.randint(12, 45)
                rate = round(random.uniform(0.5, 9.0), 2)
                tx = random.randint(0, 100)
                rx = random.randint(0, 100)
                
                metrics = {
                    "cpu": cpu,
                    "memory": {"usedPercentage": mem},
                    "temperature": round(temp, 1),
                    "os": {"type": os_name},
                    "network": {"ping": ping, "rate": rate, "tx": tx, "rx": rx}
                }
                
                if self.is_connected:
                    await self.safe_send_json({
                        "type": "system_metrics",
                        "data": metrics
                    })
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"❌ Metrics Worker crashed: {e}")
        finally:
            logger.info("📊 Metrics Worker stopped.")

    async def stop_audio(self) -> None:
        """Immediately stops any ongoing TTS and clears buffers."""
        self.agent_is_speaking = False
        # Clear the STT input buffer — must use .clear() to preserve bytearray type
        self.audio_buffer.clear()
        
        # Clear the TTS queue to stop pending synthesis/delivery
        while not self.tts_queue.empty():
            try:
                self.tts_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        
        logger.info("🛑 [Stop Audio] Audio generation and buffers cleared.")

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

    async def safe_send_json(self, data: dict):
        if not self.is_connected:
            raise WebSocketDisconnect()
        try:
            await self.websocket.send_json(data)
        except Exception:
            self.is_connected = False
            raise WebSocketDisconnect()

    async def safe_send_bytes(self, data: bytes):
        if not self.is_connected:
            raise WebSocketDisconnect()
        try:
            await self.websocket.send_bytes(data)
        except Exception:
            self.is_connected = False
            raise WebSocketDisconnect()

    def get_dynamic_threshold(self):
        return max(1800, self.ambient_noise_level * 6.0)

    def sanitize_transcript(self, text: str) -> Optional[str]:
        """Task 1D & 3: Filter out garbage/nonsense transcripts."""
        text = text.strip()
        if not text: return None
        
        # 1. Reject repeating single characters (e.g. "A. A. B. B. I. I...")
        if len(text) > 10 and len(set(text.lower())) < 5:
            logger.warning(f"🗑 Rejecting repetitive character pattern: {text}")
            return None

        # 2. Reject transcripts that are just dots/dashes/spaces or punctuation
        if not re.search(r'[a-zA-Z\u0900-\u097f]', text):
            return None
            
        # 3. Reject tiny nonsense (common noise hallucinations)
        if len(text) <= 3 and not any('\u0900' <= c <= '\u097f' for c in text):
            return None
            
        # 4. Reject common Whisper "silence" hallucinations (Aggressive list)
        junk_phrases = [
            "thank you.", "thank you", "bye.", "bye", "am.", "hm.", "stop.", "you.", 
            "i.", "the.", "a.", "it's.", "associate.", "subtitles by", "uh", "um", "ah",
            "Please subscribe", "Thanks for watching", "I'll see you in the next one",
            "Mhm", "Uh-huh", "Yeah.", "Okay.", "Right.", "Go ahead.", "I'm listening.",
            "Tell me more.", "Yes.", "No.", "Alright.", "Cool.", "Sure."
        ]
        
        lower_text = text.lower().strip(".?!, ")
        if any(lower_text == j.lower().strip(".?!, ") for j in junk_phrases):
            logger.info(f"🗑 Filtered junk phrase: {text}")
            return None

        # 5. Reject text that contains Chinese, Japanese, Korean, or Russian characters
        # since our target languages are English, Hindi, Marathi.
        if re.search(r'[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af\u0400-\u04ff]', text):
            logger.warning(f"🗑 Rejecting out-of-domain scripts (CJK/Cyrillic): {text}")
            return None

        return text

    def sanitize_for_tts(self, text: str) -> str:
        """Phase 9: Clean text to prevent phonemizer mismatches."""
        # Remove emojis and symbols
        text = re.sub(r'[^\w\s\.,\?!\u0900-\u097f]', ' ', text)
        # Collapse multiple spaces
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    async def start_response(self):
        pass

    def _change_state(self, new_state: SessionState):
        if self.state != new_state:
            logger.info(f"🔄 [STATE] {self.state.name} -> {new_state.name}")
            self.state = new_state
            if new_state == SessionState.IDLE:
                self.audio_buffer.clear()

    def is_filler(self, text: str) -> bool:
        """Determines if a sentence is just a filler word to skip TTS."""
        lower_text = text.lower().strip(".?!, ")
        fillers = ["hmm", "okay", "alright", "uh", "um", "ah", "mhm", "uh-huh", "right"]
        return lower_text in fillers

    async def process_audio(self, data: bytes):
        """Processes raw PCM chunks with Silero VAD and Turn Management."""
        if self.is_muted:
            return

        current_time = time.time()

        # ── Gate 1: Hard mute while AI is physically outputting audio ─────────
        if self.agent_is_speaking:
            return

        # ── Gate 2: Post-TTS echo guard window ───────────────────────────────
        # The 200ms playback buffer + speaker acoustic tail can linger well past
        # the moment we flip agent_is_speaking=False. Block all VAD for a fixed
        # window after the last audio byte was sent.
        in_guard = self.post_tts_guard_until > 0 and current_time < self.post_tts_guard_until
        if in_guard:
            remaining = self.post_tts_guard_until - current_time
            logger.debug(f"🛡️ [Guard] VAD blocked — echo guard active ({remaining:.2f}s remaining)")
            # Still accumulate preroll so user speech that starts after the guard
            # retains context, but do NOT run VAD.
            self.vad_preroll_buffer.append(data)
            self.last_audio_time = current_time
            return

        # ── Accumulate to audio_buffer only while listening / debouncing ──────
        if self.state in [SessionState.LISTENING, SessionState.DEBOUNCE]:
            self.audio_buffer.extend(data)

        self.vad_chunk_buffer.extend(data)
        self.vad_preroll_buffer.append(data)

        chunk_size = 1024
        while len(self.vad_chunk_buffer) >= chunk_size:
            chunk = self.vad_chunk_buffer[:chunk_size]
            self.vad_chunk_buffer = self.vad_chunk_buffer[chunk_size:]

            samples = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0  # type: ignore[operator]
            tensor = torch.from_numpy(samples)
            speech_dict = self.vad_iterator(tensor, return_seconds=True)

            if speech_dict:
                if 'start' in speech_dict:
                    if self.state != SessionState.LISTENING:
                        if self.debounce_task:
                            self.debounce_task.cancel()
                            self.debounce_task = None

                        self._change_state(SessionState.LISTENING)
                        self.speech_start_time = time.time()

                        # Prepend preroll context so we capture the very start of speech
                        preroll_context = b"".join(self.vad_preroll_buffer)
                        self.audio_buffer = bytearray(preroll_context) + self.audio_buffer
                        logger.info(f"🎤 [VAD] Speech start detected (preroll={len(preroll_context)}B, state was {self.state.value})")

                if 'end' in speech_dict:
                    if self.state == SessionState.LISTENING:
                        duration = current_time - self.speech_start_time
                        logger.info(f"🎤 [VAD] Speech end — duration={duration:.2f}s")

                        if duration < self.min_speech_duration:
                            logger.info("🗑 [VAD] Too short, ignoring.")
                            self._change_state(SessionState.IDLE)
                        else:
                            # ── Barge-in path (AI was speaking when user started) ──
                            # NOTE: We evaluate against the previous speaking state via
                            # last_agent_speech_time, not the current state (which is LISTENING).
                            recently_speaking = (current_time - self.last_agent_speech_time) < 3.0
                            if recently_speaking and duration > self.barge_in_threshold:
                                logger.info(f"💥 [Barge-in] User spoke {duration:.2f}s over AI. Interrupting.")
                                await self.stop_audio()
                                await self.websocket.send_json({"type": "interrupt"})
                                self._change_state(SessionState.IDLE)
                                asyncio.create_task(self.run_pipeline())
                            else:
                                # Normal turn — start debounce
                                if self.state not in [SessionState.THINKING, SessionState.SPEAKING]:
                                    self._change_state(SessionState.DEBOUNCE)
                                    logger.info(f"⏳ [VAD] Debouncing for {self.silence_threshold}s...")
                                    if self.debounce_task:
                                        self.debounce_task.cancel()
                                    self.debounce_task = asyncio.create_task(self.debounce_turn())
                                else:
                                    logger.info(f"⏳ [VAD] Already in {self.state.value}, skipping debounce.")

        self.last_audio_time = current_time

    async def debounce_turn(self):
        """Waits for a stable silence before triggering the pipeline."""
        try:
            await asyncio.sleep(self.silence_threshold)
            if self.state == SessionState.DEBOUNCE:
                logger.info("🏁 [Turn] Finalizing turn...")
                self._change_state(SessionState.THINKING)
                self.current_turn_id += 1
                self.turn_start_time = time.perf_counter()
                await self.run_pipeline()
                # We do NOT set IDLE here anymore; we wait for audio_finished or next turn start
        except asyncio.CancelledError:
            pass # User started speaking again

    async def greet(self):
        """Sends an initial greeting when connected."""
        global cached_greeting_pcm
        global greeting_lock
        
        if self.has_greeted:
            logger.info("👋 Skipping greeting (already greeted this session)")
            return

        text = "Hi, I'm Nexus. How can I help you today?"
        logger.info(f"👋 Sending greeting: {text}")
        
        try:
            self.agent_is_speaking = True
            self.last_agent_speech_time = time.time()
            
            # Use current_turn_id 0 for greeting
            greeting_turn_id = 0
            await self.safe_send_json({"type": "agent_message", "text": text})

            async with greeting_lock:
                if cached_greeting_pcm:
                    logger.info("👋 Sending cached greeting PCM")
                    for i, chunk in enumerate(cached_greeting_pcm):
                        if not self.is_connected: break
                        await self.safe_send_json({
                            "type": "audio_chunk",
                            "data": base64.b64encode(chunk).decode('utf-8'),
                            "meta": {"turn_id": greeting_turn_id, "chunk_index": i}
                        })
                        self.last_agent_speech_time = time.time()
                    
                    if self.is_connected:
                        await self.safe_send_json({"type": "tts_end", "turn_id": greeting_turn_id})
                    
                    self.has_greeted = True
                    return

                # Synthesize and cache
                full_pcm = []
                if tts_router is not None:
                    # Wait for provider readiness (Cartesia or Kokoro)
                    if not await tts_router.wait_until_ready(timeout=5.0):
                        logger.error("❌ [Pipeline] TTS providers failed to become ready in time.")
                        return

                    audio_gen = await tts_router.stream_audio(
                        text,
                        provider="gemini",
                        gender=self.selected_persona,
                        language="en"
                    )
                    if audio_gen:
                        idx = 0
                        audio_buffer = b""
                        BUFFER_SIZE = 9600  # 200ms @ 24kHz s16

                        async for pcm_data in audio_gen:
                            if not self.is_connected: break

                            audio_buffer += pcm_data.samples.tobytes()

                            if len(audio_buffer) >= BUFFER_SIZE:
                                full_pcm.append(audio_buffer)
                                logger.info(f"📤 [Greeting] Chunk {idx} ({len(audio_buffer)} bytes)")
                                await self.safe_send_json({
                                    "type": "audio_chunk",
                                    "data": base64.b64encode(audio_buffer).decode('utf-8'),
                                    "meta": {
                                        "turn_id": greeting_turn_id,
                                        "chunk_index": idx,
                                        "is_last": False
                                    }
                                })
                                audio_buffer = b""
                                idx += 1
                                self.last_agent_speech_time = time.time()

                        # Final remaining buffer
                        if audio_buffer and self.is_connected:
                            full_pcm.append(audio_buffer)
                            logger.info(f"📤 [Greeting] Final chunk {idx} ({len(audio_buffer)} bytes)")
                            await self.safe_send_json({
                                "type": "audio_chunk",
                                "data": base64.b64encode(audio_buffer).decode('utf-8'),
                                "meta": {
                                    "turn_id": greeting_turn_id,
                                    "chunk_index": idx,
                                    "is_last": True
                                }
                            })
                            self.last_agent_speech_time = time.time()
                        
                        if self.is_connected:
                            await self.safe_send_json({"type": "tts_end", "turn_id": greeting_turn_id})
                    else:
                        logger.error("❌ [Pipeline] TTS provider is None during greeting")
                    
                    if full_pcm:
                        cached_greeting_pcm = full_pcm
                        try:
                            with open(CACHE_FILE, "wb") as f:
                                pickle.dump(cached_greeting_pcm, f)
                        except Exception as e:
                            logger.error(f"❌ Failed to save greeting cache: {e}")
                    else:
                        logger.warning("⚠️ No TTS audio generated, not updating cache.")
                        
                    self.has_greeted = True
                else:
                    logger.error("❌ [Pipeline] TTS router is None during greeting")
        except WebSocketDisconnect:
            logger.warning("🔌 Client disconnected during greeting")
            self.is_connected = False
            raise
        except Exception as e:
            logger.error(f"❌ Greeting Error: {e}")
            self.agent_is_speaking = False

    async def run_pipeline(self):
        if self.pipeline_lock.locked():
            self.audio_buffer.clear()
            return

        async with self.pipeline_lock:
            if len(self.audio_buffer) < 3200: # Min 200ms
                self.audio_buffer.clear()
                return

            # Preprocessing: Normalize
            raw_audio = bytes(self.audio_buffer)
            self.audio_buffer.clear()
        
        try:
            # Simple Normalization
            samples: np.ndarray = np.frombuffer(raw_audio, dtype=np.int16).astype(np.float32)  # type: ignore
            max_val = float(np.max(np.abs(samples)))
            if max_val > 0:
                samples = samples * (28000.0 / max_val)  # type: ignore
            audio_to_process = samples.astype(np.int16).tobytes()  # type: ignore
            
            # 1. STT with Task 2: Multilingual Prompt
            duration_sec = len(audio_to_process) / (self.sample_rate * self.channels * self.sample_width)
            logger.info(f"🛰 [STT] Dispatching {duration_sec:.1f} seconds ({len(audio_to_process)} bytes)")
            
            stt_start_time = time.perf_counter()
            with io.BytesIO() as wav_io:
                with wave.open(wav_io, 'wb') as wav_file:
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

            if stt_provider is None:
                raise RuntimeError("STT provider not initialized — startup lifecycle may have failed")
            transcription = await stt_provider.client.audio.transcriptions.create(
                file=("audio.wav", wav_data),
                model="whisper-large-v3",
                response_format="verbose_json",
                prompt=multilingual_prompt
            )
            
            self.stt_latency = time.perf_counter() - stt_start_time
            
            # Extract text safely
            if hasattr(transcription, "text"):
                transcript_text = transcription.text.strip()
            elif isinstance(transcription, dict):
                transcript_text = transcription.get("text", "").strip()
            else:
                transcript_text = str(transcription).strip()
            
            # Use verbose_json metadata to filter out low-confidence hallucinations
            segments = getattr(transcription, "segments", []) or (transcription.get("segments", []) if isinstance(transcription, dict) else [])
            
            if segments:
                def get_val(s, key):
                    if isinstance(s, dict): return s.get(key, 0)
                    return getattr(s, key, 0)

                total_no_speech = 0.0
                total_logprob = 0.0
                for s in segments:
                    total_no_speech += float(get_val(s, "no_speech_prob") or 0)
                    total_logprob += float(get_val(s, "avg_logprob") or 0)
                
                avg_no_speech = total_no_speech / len(segments)
                avg_logprob = total_logprob / len(segments)
                
                if avg_no_speech > 0.6 or avg_logprob < -1.0:
                    logger.warning(f"🗑 [STT] Rejecting hallucination (no_speech_prob: {avg_no_speech:.2f}, avg_logprob: {avg_logprob:.2f}): {transcript_text}")
                    return

            # Task 1D & 3: Sanitization
            transcript = self.sanitize_transcript(transcript_text)
            
            # Additional check: If transcript is too short or likely noise
            if not transcript or (len(transcript.split()) <= 1 and len(transcript) < 4):
                logger.info(f"🗑 Rejected suspect transcript: {transcript}")
                return

            # Phase 8: Echo Cancellation
            from difflib import SequenceMatcher
            for recent_out in self.recent_ai_outputs:
                # If transcript is a substantial substring of a recent output, it's echo
                # We check if >60% similarity or if it's a direct substring
                clean_t = transcript.lower().strip()
                clean_r = recent_out.lower().strip()
                similarity = SequenceMatcher(None, clean_t, clean_r).ratio()
                
                if clean_t in clean_r or similarity > 0.7:
                    logger.warning(f"🔇 [Echo Failure] Dropped transcript '{transcript}' matching AI output '{recent_out}'")
                    return

            logger.info(f"💬 [STT] User: {transcript}")
            await self.safe_send_json({"type": "user_transcript", "text": transcript})

            # --- Start New Response Turn ---
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

    async def run_llm_and_tts(self, transcript: str, turn_id: int):
        """Streams LLM response and semantic-chunks it for TTS."""
        logger.info(f"🧠 [Turn {turn_id}] LLM processing: {transcript[:50]}...")
        self.llm_is_streaming = True
        self.agent_is_speaking = True
        
        try:
            full_ai_text = ""
            current_sentence = ""
            sent_count = 0
            
            system_prompt = (
                "You are Nexus, a premium AI assistant. "
                "Your persona is Professional, Confident, Helpful, Fast, and Natural. "
                "Do not sound robotic. Be concise. "
                "Mirror the user's dominant language naturally. "
                "If the user speaks English, respond in English. "
                "If the user speaks Hindi or Marathi, respond in that language. "
                "Only mix languages when the user naturally mixes them first. "
                "Do not force translations. "
                "Keep responses conversational and natural. "
                "CRITICAL: Do NOT output internal monologues, reasoning steps, or thought processes. "
                "CRITICAL: No markdown or emojis. Never use asterisks (*) or formatting."
            )

            if llm_provider is None:
                raise RuntimeError("LLM provider not initialized")
                
            llm_start_time = time.perf_counter()
            stream = await llm_provider.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcript}
                ],
                model=llm_provider.model,
                temperature=0.7,
                stream=True
            )

            # --- Semantic TTS chunking ---
            # Strategy: buffer LLM tokens until we hit a semantic boundary with sufficient words.
            # This balances Time-To-First-Audio with natural TTS prosody (Piper sounds much better with full sentences).
            #
            # Boundaries: \n । (Hindi danda)
            # We no longer chunk on . ! ? to avoid unnatural "robot breathing" hard cuts mid-paragraph
            SENTENCE_ENDS = {"\n", "।"}
            MAX_BUFFER_CHARS = 10000  # Effectively disabled to accumulate full paragraph

            async for chunk in stream:
                if turn_id != self.current_turn_id:
                    logger.warning(f"🛑 [LLM] Turn {turn_id} superseded. Stopping stream.")
                    return

                content = chunk.choices[0].delta.content
                if content:
                    full_ai_text += content
                    current_sentence += content

                    # Check semantic boundary
                    last_char = content.rstrip()[-1] if content.strip() else ""
                    word_count = len(current_sentence.split())
                    
                    is_punctuation_boundary = last_char in SENTENCE_ENDS
                    is_long_enough = True # Always flush on paragraph boundary
                    is_hard_break = last_char == "\n"
                    
                    is_boundary = is_hard_break or (is_punctuation_boundary and is_long_enough)

                    # Safety valve: force flush if buffer gets too large
                    is_long = len(current_sentence) >= MAX_BUFFER_CHARS

                    if is_boundary or is_long:
                        text_to_queue = current_sentence.strip()
                        # Filter out internal monologues/thoughts enclosed in asterisks (e.g., **Acknowledge and Respond**)
                        text_to_queue = re.sub(r'\*+.*?\*+', '', text_to_queue).strip()
                        
                        if text_to_queue and re.search(r'[a-zA-Z\u0900-\u097f]', text_to_queue):
                            sent_count += 1
                            if sent_count == 1:
                                self.llm_latency = time.perf_counter() - llm_start_time

                            await self.safe_send_json({
                                "type": "agent_partial",
                                "text": text_to_queue,
                                "turn_id": turn_id
                            })
                            
                            self.recent_ai_outputs.append(text_to_queue)

                            self.tts_queue.put_nowait({
                                "text": text_to_queue,
                                "turn_id": turn_id,
                                "index": sent_count
                            })
                            current_sentence = ""


            # Final flush
            if current_sentence.strip():
                text_to_queue = current_sentence.strip()
                text_to_queue = re.sub(r'\*+.*?\*+', '', text_to_queue).strip()
                
                if text_to_queue and re.search(r'[a-zA-Z\u0900-\u097f]', text_to_queue):
                    sent_count += 1
                    logger.info(f"📝 [LLM] Turn {turn_id} Final: '{text_to_queue[:60]}...'")
                    await self.safe_send_json({
                        "type": "agent_partial",
                        "text": text_to_queue,
                        "is_paragraph_end": True,
                        "turn_id": turn_id
                    })
                    
                    self.recent_ai_outputs.append(text_to_queue)

                    await self.tts_queue.put({
                        "text": text_to_queue,
                        "turn_id": turn_id,
                        "index": sent_count
                    })

            await self.tts_queue.put({
                "text": "",
                "turn_id": turn_id,
                "is_sentinel": True
            })

            await self.safe_send_json({"type": "agent_message", "text": full_ai_text})
            logger.info(f"🤖 Nexus Full Response: {full_ai_text}")
            
        except Exception as e:
            logger.error(f"❌ LLM Pipeline Error: {e}")
            await self.tts_queue.put({
                "text": "",
                "turn_id": turn_id,
                "is_sentinel": True
            })
        finally:
            self.llm_is_streaming = False
            logger.info(f"🧠 [Turn {turn_id}] LLM stream finished.")

active_sessions = {}
greeting_lock = asyncio.Lock()

@app.websocket("/ws/nexus")
async def websocket_endpoint(websocket: WebSocket):
    session_id = websocket.query_params.get("session_id")
    logger.info(f"🔌 Incoming WebSocket connection from {websocket.client} with session_id: {session_id}")
    await websocket.accept()
    logger.info("🔌 WebSocket connected and accepted")
    
    if session_id and session_id in active_sessions:
        old_session = active_sessions[session_id]
        old_session.is_connected = False
        logger.info(f"♻️ Replacing previous session {session_id} with a fresh one to restart worker tasks")
        
    session = VoiceSession(websocket)
    if session_id:
        active_sessions[session_id] = session
        logger.info(f"🆕 Created session {session_id}")

    
    try:
        # 5. Startup Greeting
        await session.greet()
        
        while session.is_connected:
            try:
                data = await websocket.receive()
                if "bytes" not in data: # Prevent logging massive binary payloads
                    logger.info(f"🔍 RAW WS RECEIVE: {data}")
            except (WebSocketDisconnect, RuntimeError):
                # RuntimeError = "Cannot call receive once a disconnect message has been received"
                break
            
            if "disconnect" in data:
                break
            elif "bytes" in data and data["bytes"] is not None:
                await session.process_audio(data["bytes"])
            elif "text" in data and data["text"] is not None:
                msg = json.loads(data["text"])
                if msg.get("type") == "ping":
                    await session.safe_send_json({
                        "type": "pong",
                        "timestamp": msg.get("timestamp")
                    })
                    continue

                if msg.get("type") == "audio_finished":
                    # Client reports playback complete. We accept this as a signal to
                    # clear the SPEAKING state, and we reset the post-TTS guard starting NOW
                    # to protect against acoustic room tail.
                    if session.state == SessionState.SPEAKING:
                        session.agent_is_speaking = False
                        session._change_state(SessionState.IDLE)
                        session.post_tts_guard_until = time.time() + 1.2
                        logger.info(f"✅ [Session] audio_finished received. Armed post-TTS guard for 1.2s.")
                    else:
                        logger.info(f"ℹ️ [Session] Ignoring audio_finished in state: {session.state.value}")
                    continue
                    
                if msg.get("type") == "settings":
                    logger.info(f"📩 Received settings: {msg}")
                    session.selected_persona = msg.get("persona")
                    session.selected_provider = msg.get("ttsProvider")
                    session.selected_language = msg.get("language")
                    continue
                    
                if "action" in msg:
                    action = msg["action"]
                    logger.info(f"📩 Received action: {action}")
                    if action == "mute":
                        session.is_muted = True
                        session.audio_buffer.clear()
                        session.vad_chunk_buffer.clear()
                        session.vad_iterator.reset_states()
                        session.agent_is_speaking = False
                    elif action == "unmute":
                        session.is_muted = False
                        session.vad_iterator.reset_states()
                        
                elif "text" in msg:
                    logger.info(f"📩 Received chat message: {msg['text']}")
                    session.current_turn_id += 1
                    asyncio.create_task(session.run_llm_and_tts(
                        msg["text"], 
                        turn_id=session.current_turn_id
                    ))
    except WebSocketDisconnect:
        logger.info("🔌 WebSocket disconnected cleanly")
    except Exception as e:
        logger.error(f"❌ WebSocket Error: {e}", exc_info=True)
    finally:
        await session.stop()
        logger.info("🔌 Session cleaned up")

if __name__ == "__main__":
    import uvicorn
    # Using wsproto as it handles browser WebSocket handshakes more reliably on Windows
    uvicorn.run(app, host="0.0.0.0", port=8000, ws="wsproto", log_level="info", ws_ping_interval=20.0, ws_ping_timeout=20.0)
