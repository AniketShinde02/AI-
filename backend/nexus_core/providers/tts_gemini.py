import logging
import asyncio
import os
import numpy as np
from typing import AsyncIterator
from scipy.signal import resample_poly
from math import gcd

from .tts import ProviderStatus, PcmData, TTS

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
        voice_name = kwargs.get("voice")
        if not voice_name or voice_name == "undefined":
            gender = kwargs.get("gender", "nexus_male")
            voice_map = {
                "sarah": "Aoede",
                "nexus_male": "Puck",
                "professional_male": "Fenrir",
                "casual_female": "Kore"
            }
            voice_name = voice_map.get(gender, "Puck")

        try:
            from google.genai import types
            
            def fetch_tts():
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
                    logger.error(f"❌ GeminiTTS Error: {e}")
                    raise e
            
            try:
                response = await asyncio.wait_for(asyncio.to_thread(fetch_tts), timeout=15.0)
            except asyncio.TimeoutError:
                raise RuntimeError("GeminiTTS: API call timed out after 15 seconds.")
            
            if not response:
                raise RuntimeError("GeminiTTS: API returned no response (None).")

            audio_bytes = None
            try:
                if getattr(response, "candidates", None) and response.candidates[0].content and response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        if getattr(part, "inline_data", None) and getattr(part.inline_data, "data", None):
                            audio_bytes = part.inline_data.data
                            break
            except Exception as e:
                logger.warning(f"⚠️ GeminiTTS: Failed to parse response candidates: {e}")
            
            if not audio_bytes:
                error_msg = "GeminiTTS: No audio data returned by API."
                logger.error(f"❌ {error_msg}")
                if getattr(response, "candidates", None) and response.candidates[0].content:
                    parts = getattr(response.candidates[0].content, "parts", []) or []
                    for part in parts:
                        if getattr(part, "text", None):
                            logger.error(f"   Gemini Text Output instead of Audio: {part.text}")
                raise RuntimeError(error_msg)

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
                yield PcmData(samples=chunk_array)
                # We do NOT await asyncio.sleep here. The backend should push to the socket
                # as fast as possible, and the frontend will buffer and schedule it.
                await asyncio.sleep(0) # yield control to event loop

        except Exception as e:
            logger.error(f"❌ GeminiTTS Error: {e}")
            raise e

    async def stop_audio(self) -> None:
        """Stop generating audio. For REST APIs this is a no-op as chunks are buffered immediately."""
        pass
