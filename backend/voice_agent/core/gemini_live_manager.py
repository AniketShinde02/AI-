import os
import json
import base64
import asyncio
import logging

import logging
import json
import time

raw_logger = logging.getLogger('DEBUG_GEMINI_RAW')
raw_logger.setLevel(logging.DEBUG)
if not raw_logger.handlers:
    fh = logging.FileHandler('d:/AI/backend/voice_agent/DEBUG_GEMINI_RAW.log', encoding='utf-8')
    fh.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    raw_logger.addHandler(fh)

session_logger = logging.getLogger('DEBUG_GEMINI_SESSION')
session_logger.setLevel(logging.DEBUG)
if not session_logger.handlers:
    fh = logging.FileHandler('d:/AI/backend/voice_agent/DEBUG_GEMINI_SESSION.log', encoding='utf-8')
    fh.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    session_logger.addHandler(fh)

from typing import Any
from google import genai
from google.genai import types

logger = logging.getLogger("gemini_live_manager")

class GeminiLiveSessionManager:
    """
    Encapsulates a bidirectional streaming session with Gemini Multimodal Live API.
    Designed to be used as Mode A within ws_main.py.
    """
    def __init__(self, websocket, system_instruction: str, session_id: str = ""):
        self.session_id = session_id
        self.websocket = websocket
        self.system_instruction = system_instruction
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(
            api_key=self.api_key, 
            http_options={'api_version': 'v1alpha'}
        ) if self.api_key else None
        self.session = None
        self.is_connected = False
        self.receive_task = None
        self.on_agent_message_callback = None
        self.on_disconnect_callback = None
        self.session_ready = asyncio.Event()
        self._send_lock = asyncio.Lock()

    async def connect(self, on_agent_message, on_disconnect):
        if not self.client:
            logger.error("❌ GEMINI_API_KEY missing for Live Session")
            raise ValueError("GEMINI_API_KEY missing")

        self.on_agent_message_callback = on_agent_message
        self.on_disconnect_callback = on_disconnect
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
            self.is_connected = False
            session_logger.error(f"[LIFECYCLE] [Session: {self.session_id}] ❌ Gemini Live Connection Timeout")
            logger.error("❌ Gemini Live Connection Timeout")
            raise ValueError("Gemini Live Connection Timeout")

    async def send_audio(self, pcm_data: bytes):
        if not self.is_connected or not self.session:
            return
        
        try:
            async with self._send_lock:
                raw_logger.info(f"[OUTBOUND AUDIO] [Session: {self.session_id}] [Func: send_audio] Size: {len(pcm_data)} bytes")
                await self.session.send_realtime_input(
                    audio=types.Blob(
                        mime_type="audio/pcm;rate=16000",
                        data=pcm_data
                    )
                )
        except Exception as e:
            session_logger.error(f"[ERROR] [Session: {self.session_id}] [Func: send_audio] Error: {e}")
            logger.error(f"❌ Gemini Live Audio Send Error: {e}")
            await self._handle_disconnect()

    async def send_video_frame(self, frame_b64: str):
        if not self.is_connected or not self.session:
            return
        
        try:
            # Decode base64 to raw bytes
            frame_bytes = base64.b64decode(frame_b64)
            async with self._send_lock:
                await self.session.send_realtime_input(
                    video=types.Blob(
                        mime_type="image/jpeg",
                        data=frame_bytes
                    )
                )
        except Exception as e:
            logger.error(f"❌ Gemini Live Video Send Error: {e}")
            await self._handle_disconnect()

    async def send_text(self, text: str, turn_complete: bool = False):
        if not self.is_connected or not self.session:
            return
        try:
            async with self._send_lock:
                raw_logger.info(f"[OUTBOUND TEXT] [Session: {self.session_id}] [Func: send_text] {text} (turn_complete={turn_complete})")
                await self.session.send_client_content(
                    turns=types.Content(parts=[types.Part.from_text(text=text)]),
                    turn_complete=turn_complete
                )
        except Exception as e:
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
            session_logger.error(f"[ERROR] [Session: {self.session_id}] [Func: send_turn_complete] Error: {e}")
            logger.error(f"❌ Gemini Live Turn Complete Send Error: {e}")

    async def interrupt(self):
        """Signals Gemini to stop speaking immediately (Barge-in)"""
        # Sending an empty client content or specific interrupt signal
        if self.is_connected and self.session:
            try:
                async with self._send_lock:
                    # Currently sending turn_complete=True helps truncate
                    await self.session.send_client_content(turn_complete=True)
            except Exception:
                pass

    async def _receive_from_gemini(self):
        if not self.client:
            logger.error("❌ Gemini Client is not initialized")
            return
            
        config = types.LiveConnectConfig(
            response_modalities=[types.Modality.AUDIO],
            system_instruction=types.Content(parts=[types.Part.from_text(text=self.system_instruction)])
        )
        try:
            async with self.client.aio.live.connect(model="gemini-2.5-flash-native-audio-latest", config=config) as session:
                self.session = session
                self.is_connected = True
                self.session_ready.set()
                
                while self.is_connected:
                    async for response in session.receive():
                        raw_logger.info(f"[INBOUND JSON] [Session: {self.session_id}] Size: {len(response.model_dump_json())} bytes | Content: {response.model_dump_json(exclude_none=True)}")
                        try:
                            server_content = getattr(response, "server_content", None)
                            if server_content is not None:
                                model_turn = getattr(server_content, "model_turn", None)
                                if model_turn and getattr(model_turn, "parts", None):
                                    for part in model_turn.parts:
                                        # 1. Text transcript of what Gemini is saying
                                        if getattr(part, "text", None):
                                            if self.on_agent_message_callback:
                                                await self.on_agent_message_callback(part.text)
                                        
                                        # 2. Audio PCM data
                                        if getattr(part, "inline_data", None) and getattr(part.inline_data, "data", None):
                                            pcm_data = part.inline_data.data
                                            out_b64 = base64.b64encode(pcm_data).decode('utf-8')
                                            try:
                                                await self.websocket.send_json({
                                                    "type": "audio_chunk",
                                                    "data": out_b64
                                                })
                                            except Exception as ws_err:
                                                logger.error(f"❌ WS failed to send Gemini audio chunk: {ws_err}")
                        except asyncio.CancelledError:
                            break
                        except Exception as chunk_err:
                            logger.error(f"❌ Error processing Gemini response chunk: {chunk_err}")
                            continue
        except asyncio.CancelledError:
            logger.info("ℹ️ Gemini Live receive loop gracefully cancelled")
        except Exception as e:
            logger.error(f"❌ Gemini Live Receive Stream Broken: {e}")
            await self._handle_disconnect()

    async def _handle_disconnect(self):
        if self.is_connected:
            logger.warning("⚠️ Gemini Live Session Dropped - Triggering Fallback")
            self.is_connected = False
            self.session = None
            if self.on_disconnect_callback:
                await self.on_disconnect_callback()

    async def close(self):
        self.is_connected = False
        if self.session:
            # The async with context will auto-close when we cancel receive_task or exit loop
            self.session = None
        if self.receive_task:
            self.receive_task.cancel()
