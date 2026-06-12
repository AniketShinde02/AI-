import logging
import io
import wave
from typing import Optional, Any
from groq import AsyncGroq
from vision_agents.core.stt.stt import STT
from vision_agents.core.stt.events import TranscriptResponse
from vision_agents.core.edge.types import Participant
from getstream.video.rtc.track_util import PcmData
import asyncio
import numpy as np

logger = logging.getLogger("nexus.stt")

class GroqSTT(STT):
    def __init__(self, api_key: str):
        super().__init__()
        self.client = AsyncGroq(api_key=api_key)
        self.audio_buffer = bytearray()
        
        # VAD variables (Strictly tuned for responsive interaction)
        self.silence_threshold = 1200.0  # Increased from 500.0 to reduce noise sensitivity
        self.silence_frames = 0
        self.max_silence_frames = 15  # ~300ms of silence for snappier responses
        self.min_speech_frames = 5   # 100ms minimum speech
        self.is_speaking = False
        self.is_agent_speaking = False # Anti-self-interruption flag
        self.speech_frames = 0
        self.log_counter = 0
        self._tasks = set()

    async def process_audio(self, pcm_data: PcmData, participant: Participant):
        if pcm_data.samples is None or len(pcm_data.samples) == 0:
            return

        self.log_counter += 1
        
        samples = pcm_data.samples
        # Calculate RMS energy
        energy = np.sqrt(np.mean(np.square(samples.astype(np.float32))))

        # 🟢 Heartbeat logging (Every 2s if 50fps)
        if self.log_counter % 100 == 0:
            logger.info(f"📊 [STT] Energy: {energy:.1f} | Thr: {self.silence_threshold} | Speak: {self.is_speaking}")

        # Anti-self-interruption check
        current_threshold = self.silence_threshold
        if self.is_agent_speaking:
            # If agent is speaking, we require much higher energy to detect a user interruption (barge-in)
            current_threshold = 6000.0 
            
        if energy > current_threshold:
            self.silence_frames = 0
            if not self.is_speaking:
                logger.info(f"🎤 [STT] Voice Start Detected (Energy: {energy:.2f} | Agent Speaking: {self.is_agent_speaking})")
                self.is_speaking = True
                self.speech_frames = 0
                self.audio_buffer.clear() 
        else:
            self.silence_frames += 1

        if self.is_speaking:
            self.audio_buffer.extend(pcm_data.to_bytes())
            self.speech_frames += 1

            # End speech if silence threshold hit OR max duration reached (15s @ 50fps = 750)
            if self.silence_frames >= self.max_silence_frames or self.speech_frames >= 750:
                if self.speech_frames > self.min_speech_frames:
                    # Capture buffer and spawn transcription
                    audio_data = bytes(self.audio_buffer)
                    logger.info(f"🎤 [STT] Dispatching transcription ({len(audio_data)} bytes)")
                    asyncio.create_task(self._transcribe(audio_data, participant))
                else:
                    logger.info("🎤 [STT] Audio too short, skipping transcription.")
                
                self.audio_buffer.clear()
                self.is_speaking = False
                self.speech_frames = 0

    async def _transcribe(self, audio_data: bytes, participant: Participant):
        """Internal transcription worker - DO NOT gather tasks here."""
        try:
            buffer = io.BytesIO()
            with wave.open(buffer, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(audio_data)
            
            buffer.seek(0)
            buffer.name = "audio.wav"

            # 1. Groq Transcription
            transcription = await self.client.audio.transcriptions.create(
                file=buffer,
                model="whisper-large-v3-turbo",
                response_format="text"
            )

            text = transcription.strip()
            if text and len(text) > 1:
                logger.info(f"🎤 [STT RESULT]: {text}")
                
                # 2. Emit proper event for the Agent loop
                # vision-agents Agent looks for STTTranscriptEvent
                from vision_agents.core.stt.events import STTTranscriptEvent
                
                event = STTTranscriptEvent(
                    text=text,
                    participant=participant,
                    session_id=self.agent.id if self.agent else "default"
                )
                self.events.send(event)

        except Exception as e:
            logger.error(f"❌ Groq STT Error: {e}")
