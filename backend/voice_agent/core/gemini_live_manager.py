import os
import json
import base64
import asyncio
import logging
from typing import Any
from google import genai
from google.genai import types

logger = logging.getLogger("gemini_live_manager")

class GeminiLiveSessionManager:
    """
    Encapsulates a bidirectional streaming session with Gemini Multimodal Live API.
    Designed to be used as Mode A within ws_main.py.
    """
    def __init__(self, websocket, system_instruction: str):
        self.websocket = websocket
        self.system_instruction = system_instruction
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        self.session = None
        self.is_connected = False
        self.receive_task = None
        self.on_agent_message_callback = None
        self.on_disconnect_callback = None
        self.session_ready = asyncio.Event()

    async def connect(self, on_agent_message, on_disconnect):
        if not self.client:
            logger.error("❌ GEMINI_API_KEY missing for Live Session")
            raise ValueError("GEMINI_API_KEY missing")

        self.on_agent_message_callback = on_agent_message
        self.on_disconnect_callback = on_disconnect
        self.session_ready.clear()

        logger.info("🔗 Attempting to connect to Gemini Live...")
        self.receive_task = asyncio.create_task(self._receive_from_gemini())
        
        try:
            await asyncio.wait_for(self.session_ready.wait(), timeout=5.0)
            logger.info("✅ Gemini Live Session Established")
        except asyncio.TimeoutError:
            self.is_connected = False
            logger.error("❌ Gemini Live Connection Timeout")
            raise ValueError("Gemini Live Connection Timeout")

    async def send_audio(self, pcm_data: bytes):
        if not self.is_connected or not self.session:
            return
        
        try:
            await self.session.send(
                input=types.LiveClientRealtimeInput(
                    media_chunks=[types.Blob(
                        mime_type="audio/pcm;rate=16000",
                        data=pcm_data
                    )]
                )
            )
        except Exception as e:
            logger.error(f"❌ Gemini Live Audio Send Error: {e}")
            await self._handle_disconnect()

    async def send_video_frame(self, frame_b64: str):
        if not self.is_connected or not self.session:
            return
        
        try:
            # Decode base64 to raw bytes
            frame_bytes = base64.b64decode(frame_b64)
            await self.session.send(
                input=types.LiveClientRealtimeInput(
                    media_chunks=[types.Blob(
                        mime_type="image/jpeg",
                        data=frame_bytes
                    )]
                )
            )
        except Exception as e:
            logger.error(f"❌ Gemini Live Video Send Error: {e}")
            await self._handle_disconnect()

    async def send_text(self, text: str):
        if not self.is_connected or not self.session:
            return
        try:
            await self.session.send(input=text, end_of_turn=True)
        except Exception as e:
            logger.error(f"❌ Gemini Live Text Send Error: {e}")
            await self._handle_disconnect()

    async def interrupt(self):
        """Signals Gemini to stop speaking immediately (Barge-in)"""
        # Sending an empty client content or specific interrupt signal
        if self.is_connected and self.session:
            try:
                # Currently sending end_of_turn=True helps truncate
                await self.session.send(input=types.LiveClientContent(), end_of_turn=True)
            except Exception:
                pass

    async def _receive_from_gemini(self):
        config = {
            "response_modalities": ["AUDIO"],
            "system_instruction": {"parts": [{"text": self.system_instruction}]}
        }
        try:
            async with self.client.aio.live.connect(model="gemini-2.0-flash-exp", config=config) as session:
                self.session = session
                self.is_connected = True
                self.session_ready.set()
                
                async for response in session.receive():
                    server_content = response.server_content
                    if server_content is not None:
                        model_turn = server_content.model_turn
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
                                    except Exception:
                                        pass
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
