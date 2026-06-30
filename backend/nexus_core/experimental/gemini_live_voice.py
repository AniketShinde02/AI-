import os
import json
import base64
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from google import genai
import logging

logger = logging.getLogger("gemini_live")

router = APIRouter()

SYSTEM_INSTRUCTION = """
You are Nexus, an experimental voice assistant powered by Gemini Live.
- Keep responses extremely short.
- Use a natural, casual Hinglish tone with humor and sarcasm.
- Do not add conversational filler.
"""

@router.websocket("/ws/gemini-live")
async def gemini_live_websocket(websocket: WebSocket, session_id: str = "default"):
    await websocket.accept()
    logger.info(f"✅ Gemini Live WS Connected: {session_id}")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("❌ GEMINI_API_KEY missing")
        await websocket.close(code=1011, reason="GEMINI_API_KEY missing")
        return

    client = genai.Client(api_key=api_key)
    
    config = {
        "response_modalities": ["AUDIO"],
        "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
    }

    async def log_to_client(level, message):
        if level == "info":
            logger.info(message)
        elif level == "error":
            logger.error(message)
        elif level == "warn":
            logger.warning(message)
        else:
            logger.debug(message)
            
        try:
            if websocket.client_state.name == "CONNECTED":
                await websocket.send_json({"type": "log", "level": level, "message": message})
        except Exception:
            pass

    try:
        async with client.aio.live.connect(model="gemini-3.1-flash-live-preview", config=config) as session: # type: ignore
            await log_to_client("info", "Connected to Gemini Live API")
            
            # Trigger initial greeting
            await session.send(
                input="Hi Nexus! Please introduce yourself briefly and casually in Hinglish and ask how I'm doing.",
                end_of_turn=True
            )
            await log_to_client("ai", "Sent initial greeting trigger to Gemini")
            
            async def receive_from_client():
                try:
                    while True:
                        message = await websocket.receive()
                        if "text" in message:
                            try:
                                data = json.loads(message["text"])
                                if data.get("type") == "ping":
                                    await websocket.send_json({"type": "pong"})
                                elif "text" in data:
                                    await log_to_client("info", f"Received text from client: {data['text']}")
                                    await session.send(input=data["text"], end_of_turn=True)
                            except json.JSONDecodeError:
                                pass
                        elif "bytes" in message:
                            # Frontend sends raw int16 PCM at 16kHz
                            pcm_data = message["bytes"]
                            # Send to Gemini
                            await session.send(
                                input={"data": pcm_data, "mime_type": "audio/pcm;rate=16000"}
                            )
                            
                except WebSocketDisconnect:
                    logger.info("Client disconnected")
                except Exception as e:
                    logger.error(f"Error receiving from client: {e}")

            async def receive_from_gemini():
                try:
                    async for response in session.receive():
                        server_content = response.server_content
                        if server_content is not None:
                            model_turn = server_content.model_turn
                            if model_turn and getattr(model_turn, "parts", None):
                                for part in model_turn.parts:
                                    if getattr(part, "text", None):
                                        await log_to_client("ai", f"Gemini said: {part.text}")
                                        await websocket.send_json({
                                            "type": "message",
                                            "message": {
                                                "id": "gemini",
                                                "role": "assistant",
                                                "content": part.text,
                                                "timestamp": 0
                                            }
                                        })
                                    if getattr(part, "inline_data", None) and getattr(part.inline_data, "data", None):
                                        pcm_data = part.inline_data.data
                                        # await log_to_client("debug", f"Received audio from Gemini: {len(pcm_data)} bytes")
                                        out_b64 = base64.b64encode(pcm_data).decode('utf-8')
                                        
                                        await websocket.send_json({
                                            "type": "audio_chunk",
                                            "data": out_b64
                                        })
                except Exception as e:
                    logger.error(f"Error receiving from Gemini: {e}")

            await asyncio.gather(receive_from_client(), receive_from_gemini())

    except Exception as e:
        logger.error(f"Gemini Session Error: {e}")
    finally:
        if websocket.client_state.name == "CONNECTED":
            await websocket.close()
