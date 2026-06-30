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
        self.status = ProviderStatus.UNINITIALIZED
    
    async def generate(self, text: str):
        pass

    async def stream_audio(self, text: str, *args, **kwargs) -> AsyncIterator[PcmData | dict]:
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
    - Edge TTS: Primary and Only Active REST Provider
    - Gemini Live: Bypasses this entirely via WebRTC/WebSocket
    """
    def __init__(self, config_obj):
        super().__init__(provider_name="TTSProviderRouter")
        self.config = config_obj
        self.providers: Dict[str, TTS] = {}
        self.status = ProviderStatus.UNINITIALIZED

        # 1. Initialize Edge TTS (Primary for Standard Voice/Chat)
        try:
            from .tts_edge import EdgeTTS
            self.providers["edge"] = EdgeTTS()
            logger.info("✅ [TTS] EdgeTTS initialized as Primary REST provider.")
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
        provider: str = "edge",
        **kwargs
    ) -> AsyncIterator[PcmData | dict]:
        """
        Routes text to Edge TTS. Returns detailed diagnostics.
        """
        async def _gen():
            chain = ["edge"]
            fallback_occurred = False

            for p_key in chain:
                if not self.validate_provider(p_key):
                    continue

                p_instance = self.providers[p_key]

                try:
                    logger.info(f"[TTS] Provider Selected: {p_key}")

                    # Diagnostic yield for frontend truth
                    yield {
                        "provider": p_key,
                        "fallback": fallback_occurred,
                        "voice": kwargs.get("voice", "unknown")
                    }

                    bytes_generated = 0
                    async for data in p_instance.stream_audio(text, **kwargs):
                        bytes_generated += len(data.samples) if isinstance(data, PcmData) else 0
                        yield data

                    if bytes_generated == 0:
                        logger.warning(f"[TTS] Provider {p_key} succeeded but generated 0 bytes.")

                    logger.info(f"[TTS] Provider Success: {p_key}. Bytes: {bytes_generated}")
                    break  # Success

                except Exception as e:
                    logger.error(f"[TTS] Provider '{p_key}' failed: {e}")
                    fallback_occurred = True

            if bytes_generated == 0:
                logger.critical("[TTS Router] Provider failed to generate bytes!")
                yield {"error": "All providers failed or generated 0 bytes."}

        async for item in _gen():
            yield item

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
