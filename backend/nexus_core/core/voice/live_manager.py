# ==========================================
# CRITICAL SYSTEM FILE
# Do not modify websocket lifecycle, session cleanup, 
# Gemini transport, or fallback routing without running 
# full voice test suite. Changes here can silently break voice.
# ==========================================
import os
import base64
import asyncio
import logging
import time
from typing import Any, Optional
from google import genai
from google.genai import types

raw_logger = logging.getLogger('DEBUG_GEMINI_RAW')
raw_logger.setLevel(logging.INFO)
if not raw_logger.handlers:
    fh = logging.FileHandler('d:/AI/backend/nexus_core/DEBUG_GEMINI_RAW.log', encoding='utf-8')
    fh.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    raw_logger.addHandler(fh)

session_logger = logging.getLogger('DEBUG_GEMINI_SESSION')
session_logger.setLevel(logging.DEBUG)
if not session_logger.handlers:
    fh = logging.FileHandler('d:/AI/backend/nexus_core/DEBUG_GEMINI_SESSION.log', encoding='utf-8')
    fh.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    session_logger.addHandler(fh)

logger = logging.getLogger("gemini_live_manager")

# Prefixes that indicate Gemini internal reasoning/planning — never shown to user
_PLANNING_PREFIXES = (
    "i'll ", "i will ", "i'm going to ", "i'm now ", "i am going to ",
    "my priority", "i recognize", "i need to", "i should", "let me",
    "planning:", "step 1", "first,", "alright,", "okay, so", "alright, so",
    "i've zeroed", "i've identified", "i've noted", "i understand that",
    "i am carrying", "i am now", "i can see", "i notice",
    "i am ready to", "i'm currently", "i am checking", "i'm cross-referencing",
    "i think i've", "based on the", "i'm focusing", "going to see what",
    "i'm aiming for", "i am able to", "i am checking", "i'm focusing on",
    "i think", "my plan", "i interpreted", "i refined", "i will", "my next step",
    "let's", "i'm going", "i am", "i'm", "here is", "ok,", "understood.",
)

def _filter_planning_text(text: str) -> str:
    """Strip Gemini internal planning/reasoning from UI-visible text.
    Only allows clean action confirmations through.
    """
    if not text:
        return text
    lines = text.splitlines()
    clean_lines = []
    for line in lines:
        stripped = line.strip().lower()
        is_planning = any(stripped.startswith(p) for p in _PLANNING_PREFIXES)
        if not is_planning:
            clean_lines.append(line)
    return "\n".join(clean_lines).strip()


class GeminiLiveSessionManager:
    """
    Encapsulates a bidirectional streaming session with Gemini Multimodal Live API.
    Designed to be used as Mode A within ws_main.py.

    ================================================================
    CRITICAL: DO NOT CHANGE API VERSION OR LIVE_MODEL WITHOUT TESTING
    ================================================================
    VERIFIED LIVE TEST (2026-06-29, API key: JinWoo-PC):

    The following models were tested by actually calling
    client.aio.live.connect() and confirmed WORKING:
      - models/gemini-2.5-flash-native-audio-latest  (PRIMARY - BEST)
      - models/gemini-3.1-flash-live-preview          (FALLBACK)

    The following models are DEAD and will cause 1008 errors:
      - gemini-2.0-flash-exp         (DEPRECATED - removed from API)
      - models/gemini-2.0-flash-exp  (same, dead)
      - gemini-2.0-flash             (not a Live model)
      - models/gemini-2.0-flash      (not a Live model)

    API VERSION:
      - v1alpha is REQUIRED for bidiGenerateContent (Live).
      - v1beta does NOT expose bidiGenerateContent - guaranteed 1008.

    To re-verify: run the test script at d:/AI/backend/test_live_models.py
    DO NOT change LIVE_MODEL without running that test first.
    ================================================================
    """
    # PRIMARY Live model - verified working 2026-06-29 against real API.
    # gemini-2.5-flash-native-audio-latest is the current native audio model.
    # This is the ONLY string that should be passed to aio.live.connect().
    LIVE_MODEL = "models/gemini-2.5-flash-native-audio-latest"
    # Fallback Live model if primary is unavailable (also verified working).
    LIVE_MODEL_FALLBACK = "models/gemini-3.1-flash-live-preview"

    def __init__(self, websocket, system_instruction: str, session_id: str = "", model: str = "models/gemini-2.5-flash-native-audio-latest", tools: Optional[list] = None):
        self.session_id = session_id
        self.websocket = websocket
        self.system_instruction = system_instruction
        self.tools = tools
        # Always override with the verified LIVE_MODEL.
        # The caller's model param is intentionally ignored here because
        # 95% of callers pass text-model names (e.g. gemini-2.0-flash)
        # that are NOT valid for the Live WebSocket endpoint.
        self.model = self.LIVE_MODEL
        self.connection_count = 0
        self.api_key = os.getenv("GEMINI_API_KEY")
        # MUST be v1alpha. bidiGenerateContent does not exist on v1beta.
        # See class docstring for full root cause analysis.
        self.client = genai.Client(
            api_key=self.api_key,
            http_options={'api_version': 'v1alpha'}
        ) if self.api_key else None
        self.session = None
        self.is_connected = False
        # True while Gemini is streaming its audio/text response back to us.
        # During this window, we MUST NOT send mic audio — Gemini's Live API
        # closes the session with 1000 OK if it receives user audio mid-response.
        self.agent_is_responding = False
        self.receive_task = None
        self.on_agent_message_callback = None
        self.on_disconnect_callback = None
        self.on_tool_call_callback = None
        self.session_ready = asyncio.Event()
        self._send_lock = asyncio.Lock()
        # Track clean 1000 OK closes to apply minimum reconnect delay.
        # This prevents the reconnect storm visible in logs.
        self._last_clean_close_time: float = 0.0

    async def connect(self, on_agent_message, on_disconnect, on_tool_call=None):
        if not self.client:
            logger.error("❌ GEMINI_API_KEY missing for Live Session")
            raise ValueError("GEMINI_API_KEY missing")

        self.on_agent_message_callback = on_agent_message
        self.on_disconnect_callback = on_disconnect
        self.on_tool_call_callback = on_tool_call
        self.session_ready.clear()

        session_logger.info(f"[LIFECYCLE] [Session: {self.session_id}] 🔗 Attempting to connect to Gemini Live...")
        logger.info("🔗 Attempting to connect to Gemini Live...")
        self.receive_task = asyncio.create_task(self._receive_from_gemini())
        
        try:
            await asyncio.wait_for(self.session_ready.wait(), timeout=15.0)
            session_logger.info(f"[LIFECYCLE] [Session: {self.session_id}] ✅ Gemini Live Session Established")
            logger.debug("[STATUS] ✅ Gemini Live Session Established")
            logger.info("✅ Gemini Live Session Established")
        except asyncio.TimeoutError:
            session_logger.error(f"[LIFECYCLE] [Session: {self.session_id}] ❌ Gemini Live connection timed out")
            logger.error("❌ Gemini Live connection timed out")
            raise

    async def _handle_disconnect(self):
        self.is_connected = False
        self.session = None
        if self.on_disconnect_callback:
            if asyncio.iscoroutinefunction(self.on_disconnect_callback):
                await self.on_disconnect_callback()
            else:
                self.on_disconnect_callback()

    async def send_audio(self, audio_data: bytes):
        if not self.is_connected or not self.session:
            return
            
        if self.agent_is_responding:
            # Drop incoming user audio if agent is currently speaking.
            # This is critical to prevent the 1000 OK session close bug.
            return
            
        try:
            async with self._send_lock:
                await self.session.send_realtime_input(
                    audio=types.Blob(
                        data=audio_data,
                        mime_type="audio/pcm;rate=16000"
                    )
                )
        except Exception as e:
            err_str = str(e)
            # 1000 OK is Gemini cleanly closing its turn — not a fatal error.
            # Log as debug, let the reconnect loop handle it cleanly.
            if "1000" in err_str:
                session_logger.debug(f"[TURN_CLOSE] [Session: {self.session_id}] Gemini closed turn cleanly (1000 OK) during send_audio")
            else:
                logger.error(f"❌ Gemini Live Audio Send Error: {e}")
                session_logger.error(f"[ERROR] [Session: {self.session_id}] [Func: send_audio] Error: {e}")
                await self._handle_disconnect()

    async def send_video_frame(self, frame_b64: str):
        if not self.is_connected or not self.session:
            logger.debug("[VISION_FRAME_FORWARDED] Skipped — Gemini Live not connected")
            return
        
        try:
            # Decode base64 to raw bytes
            frame_bytes = base64.b64decode(frame_b64)
            async with self._send_lock:
                raw_logger.debug(f"[OUTBOUND VIDEO] [Session: {self.session_id}] [Func: send_video_frame] Size: {len(frame_bytes)} bytes")
                logger.debug(f"[VISION_FRAME_FORWARDED] size={len(frame_bytes)}B session={self.session_id}")
                await self.session.send_realtime_input(
                    video=types.Blob(
                        data=frame_bytes,
                        mime_type="image/jpeg"
                    )
                )
        except Exception as e:
            err_str = str(e)
            if "1000" in err_str:
                session_logger.debug(f"[TURN_CLOSE] Gemini closed turn cleanly (1000 OK) during send_video_frame")
            else:
                logger.error(f"❌ Gemini Live Video Send Error: {e}")
                await self._handle_disconnect()

    async def send_text(self, text: str, turn_complete: bool = True):
        if not self.is_connected or not self.session:
            return
        try:
            async with self._send_lock:
                raw_logger.info(f"[OUTBOUND TEXT] [Session: {self.session_id}] [Func: send_text] {text} (turn_complete={turn_complete})")
                await self.session.send_client_content(
                    turns=[types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=text)]
                    )],
                    turn_complete=turn_complete
                )
        except Exception as e:
            err_str = str(e)
            if "1000" in err_str:
                session_logger.debug(f"[TURN_CLOSE] Gemini closed turn cleanly (1000 OK) during send_text")
            else:
                logger.debug(f"[OUTBOUND ERROR TEXT] {e}")
                session_logger.error(f"[ERROR] [Session: {self.session_id}] [Func: send_text] Error: {e}")
                logger.error(f"❌ Gemini Live Text Send Error: {e}")
                await self._handle_disconnect()

    async def send_turn_complete(self):
        """Signals Gemini that the user has finished speaking."""
        if not self.is_connected or not self.session:
            return
        try:
            async with self._send_lock:
                raw_logger.info(f"[OUTBOUND TURN_COMPLETE] [Session: {self.session_id}]")
                await self.session.send_client_content(turn_complete=True)
        except Exception as e:
            err_str = str(e)
            if "1000" in err_str:
                session_logger.debug(f"[TURN_CLOSE] Gemini closed turn cleanly (1000 OK) during send_turn_complete")
            else:
                session_logger.error(f"[ERROR] [Session: {self.session_id}] [Func: send_turn_complete] Error: {e}")
                logger.error(f"❌ Gemini Live Turn Complete Send Error: {e}")

    async def interrupt(self):
        """Signals Gemini to stop speaking immediately (Barge-in)"""
        if self.is_connected and self.session:
            try:
                async with self._send_lock:
                    await self.session.send_client_content(turn_complete=True)
            except Exception:
                pass

    async def _receive_from_gemini(self):
        if not self.client:
            logger.error("❌ Gemini Client is not initialized")
            return
            
        config = types.LiveConnectConfig(
            response_modalities=[types.Modality.AUDIO],
            system_instruction=types.Content(role="system", parts=[types.Part.from_text(text=self.system_instruction)]),
            tools=self.tools
        )
        attempt = 0
        while True:
            try:
                async with self.client.aio.live.connect(model=self.model, config=config) as live_session:
                    attempt = 0
                    session_any: Any = live_session
                    self.session = session_any
                    self.is_connected = True
                    self.connection_count += 1
                    raw_logger.info(f"[GEMINI_FORENSICS] connect() | Session: {self.session_id} | Count: {self.connection_count} | Timestamp: {time.time()}")
                    self.session_ready.set()
                    
                    async for response in session_any.receive():
                        raw_logger.debug(f"[INBOUND JSON] [Session: {self.session_id}] Size: {len(response.model_dump_json())} bytes | Content: {response.model_dump_json(exclude_none=True)}")
                        if not self.is_connected:
                            break
                        try:
                            server_content = getattr(response, "server_content", None)
                            if server_content is not None:
                                turn_complete = getattr(server_content, "turn_complete", False)
                                if turn_complete:
                                    self.agent_is_responding = False
                                model_turn = getattr(server_content, "model_turn", None)
                                if model_turn and getattr(model_turn, "parts", None):
                                    # Gemini has started streaming a response
                                    if not self.agent_is_responding:
                                        self.agent_is_responding = True
                                        try:
                                            await self.websocket.send_json({
                                                "type": "user_transcript",
                                                "text": "🎤 Audio processed..."
                                            })
                                        except Exception:
                                            pass
                                            
                                    for part in model_turn.parts:
                                        # 1. Text transcript of what Gemini is saying
                                        if getattr(part, "text", None):
                                            if self.on_agent_message_callback:
                                                # BUG #2 FIX: Filter internal planning text before
                                                # sending to UI. Gemini must never expose reasoning.
                                                clean_text = _filter_planning_text(part.text)
                                                if clean_text:
                                                    await self.on_agent_message_callback(clean_text)
                                        
                                        # 2. Audio PCM data
                                        if getattr(part, "inline_data", None) and getattr(part.inline_data, "data", None):
                                            pcm_data = part.inline_data.data
                                            out_b64 = base64.b64encode(pcm_data).decode('utf-8')
                                            
                                            import core.global_state as gs
                                            from core.workspace.state import SessionState
                                            session = gs.active_sessions.get(self.session_id)
                                            if session:
                                                session.agent_is_speaking = True
                                                session.last_agent_speech_time = time.time()
                                                session._change_state(SessionState.SPEAKING)
                                            
                                            try:
                                                await self.websocket.send_json({
                                                    "type": "audio_chunk",
                                                    "data": out_b64
                                                })
                                            except Exception as ws_err:
                                                logger.error(f"❌ WS failed to send Gemini audio chunk: {ws_err}")

                                        # 3. Function Calls (Tool execution from Gemini Live)
                                        if getattr(part, "function_call", None):
                                            if self.on_tool_call_callback:
                                                func_call = part.function_call
                                                logger.info(f"🎯 [GEMINI LIVE] Function call received: {getattr(func_call, 'name', 'unknown')}")
                                                
                                                if asyncio.iscoroutinefunction(self.on_tool_call_callback):
                                                    asyncio.create_task(self.on_tool_call_callback(func_call))
                                                else:
                                                    self.on_tool_call_callback(func_call)
                        except asyncio.CancelledError:
                            raise
                        except Exception as chunk_err:
                            logger.error(f"❌ Error processing Gemini response chunk: {chunk_err}")
                            continue
            except asyncio.CancelledError:
                logger.info("ℹ️ Gemini Live receive loop gracefully cancelled")
                break
            except Exception as e:
                self.is_connected = False
                self.session = None
                self.session_ready.clear()
                err_str = str(e)
                is_clean_close = "1000" in err_str or "sent 1000" in err_str

                if is_clean_close:
                    # BUG #11 FIX: 1000 OK is EXPECTED — Gemini closes per-turn.
                    # Apply a minimum 0.5s delay between clean reconnects to prevent
                    # reconnect storms when there is rapid back-to-back activity.
                    now = time.time()
                    since_last = now - self._last_clean_close_time
                    if since_last < 0.5:
                        await asyncio.sleep(0.5 - since_last)
                    self._last_clean_close_time = time.time()
                    session_logger.debug(
                        f"[LIFECYCLE] [Session: {self.session_id}] "
                        f"Turn closed cleanly (1000 OK). Reconnecting for next turn."
                    )
                    attempt = 0  # Clean close is not an error — reset retry counter
                    continue

                attempt += 1
                if attempt > 5:
                    logger.error(f"❌ Gemini Live Receive Stream Broken (Max Retries Reached): {e}")
                    await self._handle_disconnect()
                    break
                backoff = min(1.5 ** attempt, 15)
                logger.warning(f"⚠️ Gemini Live Session Dropped: {e}. Reconnecting in {backoff:.1f}s...")
                await asyncio.sleep(backoff)

    async def _handle_disconnect(self):
        if self.is_connected:
            logger.warning("⚠️ Gemini Live Session Dropped - Triggering Fallback")
            self.is_connected = False
            self.session = None
            if self.on_disconnect_callback:
                await self.on_disconnect_callback()

    async def close(self):
        self.is_connected = False
        raw_logger.info(f"[GEMINI_FORENSICS] disconnect() | Session: {self.session_id} | Timestamp: {time.time()}")
        if self.session:
            # The async with context will auto-close when we cancel receive_task or exit loop
            self.session = None
        if self.receive_task:
            self.receive_task.cancel()
