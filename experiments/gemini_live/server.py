"""
Gemini Live Experiment — Minimal Backend Bridge
================================================
Branch: nexus-gemini-live-test

Architecture:
  Browser Mic (16kHz PCM)
  → WebSocket → this server.py
  → google-genai Live Session
  → PCM audio response
  → WebSocket → Browser AudioWorklet Playback

ZERO overlap with existing Nexus backend.
This server runs on port 8001.

Measurements:
  - Connection time
  - First audio latency (TTFA)
  - Interruption handling
  - Language quality (per turn)
"""
import asyncio
import base64
import json
import os
import time
import logging
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("gemini_live")

app = FastAPI(title="Gemini Live Experiment")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the client HTML at /
app.mount("/static", StaticFiles(directory=Path(__file__).parent), name="static")

GEMINI_MODEL = "gemini-3.1-flash-live-preview"
GEMINI_CONFIG = {
    "response_modalities": ["AUDIO"],
    "speech_config": {
        "voice_config": {
            "prebuilt_voice_config": {
                "voice_name": "Puck"
            }
        }
    },
    "system_instruction": {
        "parts": [{"text": (
            "You are a helpful assistant. "
            "Mirror the user's language naturally — English, Hindi, Marathi, or Hinglish. "
            "Keep responses conversational and concise. "
            "Do not use markdown or emojis."
        )}]
    }
}

@app.websocket("/ws/gemini")
async def gemini_live_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("🔌 Client connected to Gemini Live bridge")

    if not GEMINI_API_KEY:
        await websocket.send_json({"type": "error", "message": "GEMINI_API_KEY not set in .env"})
        await websocket.close()
        return

    try:
        from google import genai  # type: ignore
        from google.genai import types  # type: ignore
    except ImportError:
        await websocket.send_json({"type": "error", "message": "google-genai not installed. Run: pip install google-genai"})
        await websocket.close()
        return

    client = genai.Client(api_key=GEMINI_API_KEY)
    connect_start = time.perf_counter()

    try:
        async with client.aio.live.connect(model=GEMINI_MODEL, config=GEMINI_CONFIG) as session:
            connect_ms = (time.perf_counter() - connect_start) * 1000
            logger.info(f"✅ Gemini Live connected in {connect_ms:.0f}ms")
            await websocket.send_json({"type": "connected", "connect_ms": round(connect_ms, 1)})
            
            # Force Gemini to speak immediately to test the downlink
            await session.send(input="Hello! Please say 'Connection successful, I am listening' out loud.")

            turn_start: float = 0.0
            first_audio_received = False
            total_audio_bytes = 0

            async def receive_from_client():
                """Forward mic audio to Gemini."""
                nonlocal turn_start
                try:
                    while True:
                        data = await websocket.receive()
                        if "disconnect" in data:
                            break
                        if "bytes" in data:
                            # Raw PCM 16kHz from browser
                            pcm_bytes = data["bytes"]
                            await session.send(
                                input=types.LiveClientRealtimeInput(
                                    audio=types.Blob(
                                        mime_type="audio/pcm;rate=16000",
                                        data=pcm_bytes
                                    )
                                )
                            )
                        elif "text" in data:
                            msg = json.loads(data["text"])
                            if msg.get("type") == "turn_start":
                                turn_start = time.perf_counter()
                                first_audio_received = False  # type: ignore[assignment]
                            elif msg.get("type") == "ping":
                                await websocket.send_json({"type": "pong"})
                except WebSocketDisconnect:
                    pass

            async def receive_from_gemini():
                """Forward Gemini audio to browser."""
                nonlocal first_audio_received, total_audio_bytes
                try:
                    async for response in session.receive():
                        server_content = response.server_content
                        if server_content is None:
                            continue

                        if server_content.model_turn:
                            for part in server_content.model_turn.parts:
                                if part.inline_data and part.inline_data.data:
                                    audio_data = part.inline_data.data
                                    total_audio_bytes += len(audio_data)

                                    if not first_audio_received and turn_start > 0:
                                        ttfa_ms = (time.perf_counter() - turn_start) * 1000
                                        first_audio_received = True
                                        logger.info(f"⚡ TTFA: {ttfa_ms:.0f}ms")
                                        await websocket.send_json({
                                            "type": "ttfa",
                                            "ttfa_ms": round(ttfa_ms, 1),
                                        })

                                    await websocket.send_json({
                                        "type": "audio_chunk",
                                        "data": base64.b64encode(audio_data).decode(),
                                        "sample_rate": 24000,  # Gemini outputs 24kHz
                                    })

                                if part.text:
                                    await websocket.send_json({
                                        "type": "transcript",
                                        "text": part.text,
                                    })

                        if server_content.turn_complete:
                            logger.info(f"🏁 Turn complete. Total audio: {total_audio_bytes} bytes ({total_audio_bytes/24000/2:.2f}s @ 24kHz)")
                            await websocket.send_json({
                                "type": "turn_complete",
                                "total_audio_bytes": total_audio_bytes,
                                "duration_s": round(total_audio_bytes / 24000 / 2, 3),
                            })
                            total_audio_bytes = 0

                        if server_content.interrupted:
                            logger.info("⚡ [Gemini] Turn interrupted by user barge-in")
                            await websocket.send_json({"type": "interrupted"})

                except Exception as e:
                    logger.error(f"Error receiving from Gemini: {e}")

            await asyncio.gather(receive_from_client(), receive_from_gemini())

    except WebSocketDisconnect:
        logger.info("🔌 Client disconnected")
    except Exception as e:
        logger.error(f"❌ Session error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Gemini Live Experiment server starting on http://0.0.0.0:8001")
    logger.info("   Open: http://localhost:8001/static/client.html")
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
