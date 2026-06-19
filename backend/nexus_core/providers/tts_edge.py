import logging
import asyncio
from typing import AsyncIterator
from .tts import ProviderStatus, PcmData, TTS

logger = logging.getLogger("nexus.tts.edge")

class EdgeTTS(TTS):
    def __init__(self):
        super().__init__(provider_name="edge")
        self._is_stopped = False
        try:
            import edge_tts
            self.status = ProviderStatus.READY
            logger.info("✅ EdgeTTS initialized as Fallback provider.")
        except ImportError:
            logger.error("❌ EdgeTTS: edge-tts package not installed.")
            self.status = ProviderStatus.FAILED

    async def stream_audio(self, text: str, *args, **kwargs):
        self._is_stopped = False
        if self.status != ProviderStatus.READY:
            logger.warning("EdgeTTS is not ready.")
            return

        import edge_tts
        import re
        
        # Determine voice
        voice_name = kwargs.get("voice")
        if not voice_name or voice_name == "undefined":
            gender = kwargs.get("gender", "nexus_male")
            
            # Detect language script in text
            is_devanagari = bool(re.search(r'[\u0900-\u097f]', text))
            if is_devanagari:
                # Provide hi/mr specific voices
                if gender in ["sarah", "casual_female"]:
                    voice_name = "hi-IN-SwaraNeural" # Fallback/generic female
                else:
                    voice_name = "hi-IN-MadhurNeural"
            else:
                # Map to Edge TTS voices for Indian English
                if gender is None:
                    gender = "female"
                    
                voice_map = {
                    "sarah": "en-IN-NeerjaNeural",
                    "female": "en-IN-NeerjaNeural",
                    "casual_female": "en-IN-NeerjaNeural",
                    "nexus_male": "en-IN-PrabhatNeural",
                    "male": "en-IN-PrabhatNeural",
                    "professional_male": "en-IN-PrabhatNeural"
                }
                # Default to Prabhat if male, otherwise Neerja
                fallback = "en-IN-PrabhatNeural" if "male" in gender.lower() and "female" not in gender.lower() else "en-IN-NeerjaNeural"
                voice_name = voice_map.get(gender, fallback)

        logger.info(f"🎤 EdgeTTS Synthesizing with voice: {voice_name}")

        try:
            communicate = edge_tts.Communicate(text, voice_name)
            
            # Edge TTS returns mp3, so we might need to convert it to raw PCM 16kHz
            # But wait, edge_tts can output raw PCM?
            # actually edge_tts streams MP3 or Silk or raw PCM depending on format!
            # Bump rate to +20% to make it feel faster, snappier, and reduce TTS generation time
            communicate = edge_tts.Communicate(text, voice_name, rate="+20%", pitch="+0Hz")
            # Since standard edge_tts output is mp3, we must decode it.
            # To avoid heavy dependencies if pydub/ffmpeg is missing, let's just 
            # save to a temp file and read it or stream chunks. 
            import tempfile
            import subprocess
            import os
            
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                temp_mp3 = tmp.name

            await communicate.save(temp_mp3)

            # Convert to 24kHz 16-bit PCM (same as Gemini)
            # Use ffmpeg via subprocess
            pcm_temp = temp_mp3.replace(".mp3", ".raw")
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            
            cmd = [
                ffmpeg_exe, "-y", "-i", temp_mp3,
                "-f", "s16le", "-acodec", "pcm_s16le",
                "-ar", "24000", "-ac", "1", pcm_temp
            ]
            
            import subprocess
            def run_ffmpeg():
                subprocess.run(
                    cmd, 
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL,
                    check=True
                )
            
            await asyncio.to_thread(run_ffmpeg)

            if os.path.exists(pcm_temp):
                with open(pcm_temp, "rb") as f:
                    while not self._is_stopped:
                        chunk = await asyncio.to_thread(f.read, 4800) # 100ms
                        if not chunk:
                            break
                        import numpy as np
                        samples = np.frombuffer(chunk, dtype=np.int16)
                        yield PcmData(samples=samples)
                        await asyncio.sleep(0) # yield control
                os.remove(pcm_temp)
            os.remove(temp_mp3)

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"❌ EdgeTTS Error: {e}\n{tb}")
            raise e

    async def stop_audio(self) -> None:
        self._is_stopped = True
