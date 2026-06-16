import logging
import asyncio
from typing import AsyncIterator, Optional, Dict
import os
import numpy as np
from scipy.signal import resample
import re
from enum import Enum
from dataclasses import dataclass

@dataclass
class PcmData:
    samples: np.ndarray

class TTS:
    def __init__(self, provider_name: str = "Unknown"):
        self.provider_name = provider_name
    
    async def generate(self, text: str):
        pass

    async def stream_audio(self, text: str, *args, **kwargs) -> AsyncIterator[PcmData]:
        yield PcmData(samples=np.array([]))

    async def stop_audio(self):
        pass

    async def close(self):
        pass

@dataclass
class ProviderCapabilities:
    supports_gender: bool = True
    supports_multilingual: bool = False
    supports_streaming: bool = True

class ProviderStatus(Enum):
    READY = "ready"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNINITIALIZED = "uninitialized"

logger = logging.getLogger("nexus.tts.router")

# Removed Kokoro fallback implementation entirely.

class TTSProviderRouter(TTS):
    """
    Simplified TTS Architecture:
    - Gemini: Primary and Only Active Provider
    """
    def __init__(self, config_obj):
        super().__init__(provider_name="TTSProviderRouter")
        self.config = config_obj
        self.providers: Dict[str, TTS] = {}
        self.status = ProviderStatus.UNINITIALIZED

        # 1. Initialize Gemini (Premium / Mode 1)
        try:
            from .tts_gemini import GeminiTTS
            self.providers["gemini"] = GeminiTTS()
            logger.info("✅ [TTS] GeminiTTS initialized as Primary provider.")
        except Exception as e:
            logger.error(f"❌ Failed to init GeminiTTS: {e}")

        # 2. Initialize Edge TTS (Fallback)
        try:
            from .tts_edge import EdgeTTS
            self.providers["edge"] = EdgeTTS()
        except Exception as e:
            logger.error(f"❌ Failed to init EdgeTTS: {e}")

        # Final Status Resolution
        if any(getattr(p, 'status', None) == ProviderStatus.READY for p in self.providers.values()):
            self.status = ProviderStatus.READY
        else:
            self.status = ProviderStatus.FAILED
            logger.critical("🆘 [TTS] All TTS providers failed to initialize. Voice pipeline broken.")

    def validate_provider(self, provider_name: str) -> bool:
        """Strict validation before switching to a provider."""
        provider = self.providers.get(provider_name)
        if not provider:
            logger.warning(f"⚠️ Provider '{provider_name}' not found.")
            return False
            
        if hasattr(provider, 'status') and provider.status != ProviderStatus.READY:
            logger.warning(f"⚠️ Provider '{provider_name}' status is {getattr(provider, 'status')}, skipping.")
            return False
            
        return True

    async def stream_audio(
        self,
        text: str,
        provider: str = "gemini",
        **kwargs
    ) -> AsyncIterator[PcmData]:
        """
        Routes text to Gemini TTS.
        """
        async def _gen():
            base_chain = ["edge"]
            chain = [provider] + [p for p in base_chain if p != provider]

            provider_used = None
            fallback_occurred = False
            provider_errors = {}

            for p_key in chain:
                if not self.validate_provider(p_key):
                    continue

                if fallback_occurred:
                    logger.info(f"[TTS] Provider Fallback: Trying {p_key}")

                p_instance = self.providers[p_key]

                try:
                    logger.info(f"[TTS] Provider Selected: {p_key}")

                    yield {"provider": p_key, "fallback": fallback_occurred, "voice": kwargs.get("voice", "unknown")}

                    async for data in p_instance.stream_audio(text, **kwargs):
                        yield data

                    provider_used = p_key
                    logger.info(f"[TTS] Provider Success: {p_key}")
                    break  # Success — stop fallback chain

                except Exception as e:
                    import traceback
                    err_str = traceback.format_exc()
                    logger.error(f"[TTS] Provider Failed: {p_key}. Error: {e}")
                    with open("DEBUG_FORENSICS.txt", "a", encoding="utf-8") as f: f.write(f"[TTS Router Error] {p_key} failed: {e}\n{err_str}\n")
                    fallback_occurred = True
                    provider_errors[p_key] = str(e)
                    # Mark this provider degraded so validate_provider skips it next time
                    if hasattr(p_instance, "status"):
                        setattr(p_instance, "status", ProviderStatus.FAILED)

            if not provider_used:
                logger.critical("🆘 [TTS Router] All providers in chain failed!")
                raise RuntimeError(f"All TTS providers failed — no audio produced. Errors: {provider_errors}")

        return _gen()

    async def close(self):
        for p in self.providers.values():
            await p.close()
        await super().close()

    async def stop_audio(self) -> None:
        for p in self.providers.values():
            await p.stop_audio()

    async def wait_until_ready(self, timeout: float = 10.0) -> bool:
        """Wait for at least one provider to become READY."""
        import time
        start = time.time()
        while time.time() - start < timeout:
            if self.status == ProviderStatus.READY:
                return True
            await asyncio.sleep(0.5)
        return False
