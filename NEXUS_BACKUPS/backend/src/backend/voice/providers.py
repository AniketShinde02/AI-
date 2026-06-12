import os
import httpx
import logging
import io
import wave
import asyncio
import numpy as np
from typing import Optional, Any, AsyncIterator, Union, AsyncGenerator
from groq import AsyncGroq
from vision_agents.core.stt.stt import STT, PcmData
from vision_agents.core.stt.events import TranscriptResponse
from vision_agents.core.tts.tts import TTS
from vision_agents.core.edge.types import Participant
from ..config.settings import settings

logger = logging.getLogger("nexus.providers")

class GroqSTT(STT):
    def __init__(self, api_key: str):
        super().__init__()
        self.client = AsyncGroq(api_key=api_key)
        self.audio_buffer = bytearray()
        
        # VAD variables
        self.silence_threshold = 2.5
        self.silence_frames = 0
        self.max_silence_frames = 35  # ~0.7s
        self.min_speech_frames = 3
        self.is_speaking = False
        self.speech_frames = 0
        self._tasks = set()

    async def process_audio(self, pcm_data: PcmData, participant: Participant):
        if pcm_data.samples is None or len(pcm_data.samples) == 0:
            return

        samples = pcm_data.samples
        energy = np.sqrt(np.mean(samples.astype(np.float32)**2))

        if energy > self.silence_threshold:
            self.silence_frames = 0
            if not self.is_speaking:
                self.is_speaking = True
                self.speech_frames = 0
        else:
            self.silence_frames += 1

        if self.is_speaking:
            self.audio_buffer.extend(pcm_data.to_bytes())
            self.speech_frames += 1

            if self.silence_frames >= self.max_silence_frames or self.speech_frames >= 750:
                if self.speech_frames > self.min_speech_frames:
                    data_to_send = bytes(self.audio_buffer)
                    task = asyncio.create_task(self._transcribe(data_to_send, participant))
                    self._tasks.add(task)
                    task.add_done_callback(self._tasks.discard)
                
                self.audio_buffer.clear()
                self.is_speaking = False
                self.speech_frames = 0

    async def _transcribe(self, audio_data: bytes, participant: Participant):
        try:
            buffer = io.BytesIO()
            with wave.open(buffer, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(audio_data)
            
            buffer.seek(0)
            buffer.name = "audio.wav"

            transcription = await self.client.audio.transcriptions.create(
                file=buffer,
                model="whisper-large-v3",
                response_format="text"
            )

            text = transcription.strip()
            if text and len(text) > 2:
                logger.info(f"🎤 STT: {text}")
                self._emit_transcript_event(
                    text=text,
                    participant=participant,
                    response=TranscriptResponse(model_name="whisper-large-v3")
                )
        except Exception as e:
            logger.error(f"❌ Groq STT Error: {e}")



class CartesiaTTS(TTS):
    def __init__(self, api_key: Optional[str] = None, voice_id: str = "a0e9987d-b687-4345-a868-3e0e77abe7e8"):
        super().__init__()
        self.api_key = api_key or settings.CARTESIA_API_KEY
        self.voice_id = voice_id
        self.base_url = "https://api.cartesia.ai/tts/bytes"

    async def stream_audio(self, text: str) -> AsyncIterator[PcmData]:
        headers = {
            "X-API-Key": self.api_key,
            "Cartesia-Version": "2024-06-10",
            "Content-Type": "application/json"
        }
        payload = {
            "model_id": "sonic-english",
            "transcript": text,
            "voice": {
                "mode": "id",
                "id": self.voice_id
            },
            "output_format": {
                "container": "raw",
                "encoding": "pcm_s16le",
                "sample_rate": 16000
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream("POST", self.base_url, json=payload, headers=headers, timeout=60.0) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"Cartesia TTS Error {response.status_code}: {error_text}")
                        return
                        
                    async for chunk in response.aiter_bytes():
                        yield PcmData(sample_rate=16000, format='s16', samples=np.frombuffer(chunk, dtype=np.int16), channels=1)
        except Exception as e:
            logger.error(f"Cartesia Stream Error: {e}")
            raise

class LocalKokoroTTS(TTS):
    """
    Local TTS provider using the Kokoro-82M worker.
    Zero cost, high durability, running on local CPU/GPU.
    """
    def __init__(self, endpoint: str = "http://localhost:8001/tts", voice: str = "af_sarah"):
        super().__init__()
        self.endpoint = endpoint
        self.voice = voice

    async def generate(self, text: str) -> AsyncGenerator[bytes, None]:
        request_id = f"local_tts_{id(text)}"

        try:
            async with httpx.AsyncClient() as client:
                # We use a POST request with form data as expected by local_worker.py
                async with client.stream("POST", self.endpoint, data={"text": text, "voice": self.voice}, timeout=60.0) as response:
                    if response.status_code != 200:
                        logger.error(f"Local TTS Error: {response.status_code}")
                        return
                    
                    async for chunk in response.aiter_bytes():
                        yield chunk
        except Exception as e:
            logger.error(f"Local TTS Connection Error: {e}")
            # Fallback to a warning or silent failure
            yield b"" 

class NullSTT(STT):
    """
    Disabled STT provider. Used when the frontend handles transcription.
    Zero backend cost, zero GPU usage.
    """
    async def process_audio(self, pcm_data: PcmData, participant: Participant):
        pass

class LogBroadcaster(logging.Handler):
    """
    Custom log handler that captures logs and makes them available for 
    real-time broadcasting to the frontend.
    Supports structured data for rich UI display.
    """
    def __init__(self):
        super().__init__()
        self.logs = asyncio.Queue()

    def emit(self, record):
        try:
            # Check if this is a structured log
            data = getattr(record, 'nexus_data', None)
            level = record.levelname.lower()
            
            # Custom mapping for rich UI levels
            if hasattr(record, 'nexus_level'):
                level = record.nexus_level

            log_entry = {
                "level": level,
                "message": self.format(record),
                "data": data,
                "timestamp": record.created * 1000
            }
            
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.logs.put(log_entry))
            except RuntimeError:
                pass # No running loop
        except Exception:
            self.handleError(record)

log_broadcaster = LogBroadcaster()
log_broadcaster.setFormatter(logging.Formatter('%(message)s'))
nexus_logger = logging.getLogger("nexus")
nexus_logger.setLevel(logging.DEBUG)
nexus_logger.addHandler(log_broadcaster)

def nexus_log(message: str, level: str = "info", data: Any = None):
    """Helper to emit structured logs that reach the frontend."""
    nexus_logger.log(
        logging.INFO if level == "info" else logging.DEBUG, 
        message, 
        extra={"nexus_data": data, "nexus_level": level}
    )
