import logging
import asyncio
import os
import numpy as np
from typing import AsyncIterator
from scipy.signal import resample_poly
from math import gcd

from getstream.video.rtc import PcmData
from vision_agents.core.tts.tts import TTS
from .tts import ProviderStatus

logger = logging.getLogger("nexus.tts.gemini")

# Gemini outputs at 24000 Hz, but our frontend expects 16000 Hz
GEMINI_SAMPLE_RATE = 24000

class GeminiTTS(TTS):
    """
    Gemini API as a TTS Provider (Mode 1).
    Uses the REST API (generateContent) with response_modalities=["AUDIO"].
    """

    def __init__(self):
        super().__init__(provider_name="GeminiTTS")
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.error("❌ GeminiTTS: GEMINI_API_KEY not found in environment.")
            self.status = ProviderStatus.FAILED
            return

        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
            self.status = ProviderStatus.READY
            logger.info("✅ GeminiTTS initialized (TTS Mode 1).")
        except ImportError:
            logger.error("❌ GeminiTTS: google-genai package not installed.")
            self.status = ProviderStatus.FAILED

    async def stream_audio(self, text: str, *args, **kwargs) -> AsyncIterator[PcmData]:
        """Synthesize text using Gemini and yield 16kHz PCM data."""
        if self.status != ProviderStatus.READY:
            logger.warning("GeminiTTS is not ready.")
            return

        # Voice selection (Gemini supports voices like Puck, Aoede, Charon, Fenrir, Kore)
        gender = kwargs.get("gender", "female")
        voice_name = "Puck" if gender == "male" else "Aoede"

        try:
            from google.genai import types
            
            def fetch_tts():
                import time
                import random
                max_retries = 3
                retries = 0
                
                while retries <= max_retries:
                    try:
                        return self.client.models.generate_content(
                            model='gemini-2.5-flash-preview-tts',
                            contents=text,
                            config=types.GenerateContentConfig(
                                response_modalities=["AUDIO"],
                                speech_config=types.SpeechConfig(
                                    voice_config=types.VoiceConfig(
                                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                            voice_name=voice_name
                                        )
                                    )
                                )
                            )
                        )
                    except Exception as e:
                        err_str = str(e).lower()
                        if "429" in err_str or "too many requests" in err_str or "quota" in err_str:
                            retries += 1
                            if retries > max_retries:
                                logger.error(f"❌ Gemini API Rate Limit Exceeded after {max_retries} retries.")
                                raise e
                            # Exponential backoff with jitter
                            sleep_time = (2 ** retries) + random.uniform(0.1, 1.0)
                            logger.warning(f"⚠️ Gemini Rate Limit Hit (429)! Retrying in {sleep_time:.2f}s... (Attempt {retries}/{max_retries})")
                            time.sleep(sleep_time)
                        else:
                            raise e
            
            response = await asyncio.to_thread(fetch_tts)

            audio_bytes = None
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.inline_data and part.inline_data.data:
                        audio_bytes = part.inline_data.data
                        break
            
            if not audio_bytes:
                logger.error("❌ GeminiTTS: No audio data returned by API.")
                return

            # Extract raw PCM from WAV file
            import wave
            import io
            try:
                with wave.open(io.BytesIO(audio_bytes), 'rb') as wav_file:
                    audio_bytes_raw = wav_file.readframes(wav_file.getnframes())
            except wave.Error:
                audio_bytes_raw = audio_bytes
            
            # Yield chunks directly without resampling or sleeping
            chunk_size = 4800  # 100ms at 24kHz (24000 * 0.1 * 2 bytes)
            
            for i in range(0, len(audio_bytes_raw), chunk_size):
                chunk = audio_bytes_raw[i:i + chunk_size]
                chunk_array = np.frombuffer(chunk, dtype=np.int16)
                yield PcmData(sample_rate=24000, format='s16', channels=1, samples=chunk_array)
                # We do NOT await asyncio.sleep here. The backend should push to the socket
                # as fast as possible, and the frontend will buffer and schedule it.
                await asyncio.sleep(0) # yield control to event loop

        except Exception as e:
            logger.error(f"❌ GeminiTTS Error: {e}")

    async def stop_audio(self) -> None:
        """Stop generating audio. For REST APIs this is a no-op as chunks are buffered immediately."""
        pass
