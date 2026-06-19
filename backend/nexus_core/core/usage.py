import logging
import time
from typing import Dict, Any

logger = logging.getLogger("nexus.usage")

class UsageMonitor:
    """
    Tracks usage metrics for STT, TTS, and LLM to provide cost estimates.
    """
    def __init__(self):
        self.total_stt_seconds = 0.0
        self.total_tts_characters = 0
        self.total_llm_tokens = 0
        self.start_time = time.time()

    def record_stt(self, duration_seconds: float):
        self.total_stt_seconds += duration_seconds
        logger.debug(f"📈 STT Usage: +{duration_seconds}s (Total: {self.total_stt_seconds}s)")

    def record_tts(self, text: str):
        count = len(text)
        self.total_tts_characters += count
        logger.debug(f"📈 TTS Usage: +{count} chars (Total: {self.total_tts_characters})")

    def record_llm(self, tokens: int):
        self.total_llm_tokens += tokens
        logger.debug(f"📈 LLM Usage: +{tokens} tokens (Total: {self.total_llm_tokens})")

    def get_report(self) -> Dict[str, Any]:
        uptime_hours = (time.time() - self.start_time) / 3600
        return {
            "uptime_hours": round(uptime_hours, 2),
            "stt_minutes": round(self.total_stt_seconds / 60, 2),
            "tts_characters": self.total_tts_characters,
            "llm_tokens": self.total_llm_tokens,
            "estimated_cost_usd": self.calculate_cost()
        }

    def calculate_cost(self) -> float:
        # Based on Deepgram/Groq current pricing
        stt_cost = (self.total_stt_seconds / 60) * 0.0043  # Nova-2
        tts_cost = (self.total_tts_characters / 1_000_000) * 15.0  # Aura
        # Groq is free for now, but we can assume Llama 3 70B pricing eventually (~$0.60/1M tokens)
        llm_cost = (self.total_llm_tokens / 1_000_000) * 0.60
        return round(stt_cost + tts_cost + llm_cost, 4)

# Global monitor instance
monitor = UsageMonitor()
