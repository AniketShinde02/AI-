import asyncio
import logging
import json
import websockets
from config import DEEPGRAM_API_KEY

logger = logging.getLogger(__name__)

async def stream_stt(audio_in_queue: asyncio.Queue, text_out_queue: asyncio.Queue):
    """
    Streams raw audio bytes to Deepgram WebSocket.
    Receives text back and pushes to LLM queue.
    """
    dg_url = "wss://api.deepgram.com/v1/listen?model=nova-2&punctuate=true&interim_results=false&endpointing=300"
    headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}
    
    try:
        async with websockets.connect(dg_url, extra_headers=headers) as ws:
            logger.info("[STT] Connected to Deepgram WebSocket")
            
            async def sender():
                while True:
                    audio_chunk = await audio_in_queue.get()
                    if audio_chunk is None:
                        await ws.send(json.dumps({"type": "CloseStream"}))
                        break
                    await ws.send(audio_chunk)

            async def receiver():
                async for msg in ws:
                    res = json.loads(msg)
                    if res.get("channel"):
                        transcript = res["channel"]["alternatives"][0]["transcript"]
                        if transcript.strip():
                            logger.info(f"[STT] Heard: {transcript}")
                            await text_out_queue.put(transcript)

            await asyncio.gather(sender(), receiver())
            
    except Exception as e:
        logger.error(f"[STT] Deepgram stream error: {e}")
