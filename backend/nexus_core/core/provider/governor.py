"""
provider_governor.py
====================
Phase 4 — Centralized Provider Governor & Rate Limiter

A global registry and sliding-window rate limiter for all external APIs 
(Groq, Mistral, Gemini, Cerebras, OpenRouter).

Responsibilities:
- Tracks Requests Per Minute (RPM) and Tokens Per Minute (TPM) per provider.
- Proactively pauses execution (asyncio.sleep) if a limit is approaching.
- Emits UI state broadcasts so the frontend can show a cooldown animation.
- Used by ModelRouter (LLMs), VoiceSession (STT), and TTS pipelines.
"""

import time
import asyncio
import logging
from typing import Dict, List, Tuple
from collections import deque

logger = logging.getLogger("nexus.provider_governor")

# ---------------------------------------------------------------------------
# Rate Limit Registry (Free / Dev Tier baselines)
# ---------------------------------------------------------------------------

PROVIDER_LIMITS = {
    "groq":       {"rpm": 30,  "tpm": 6000},       # Strict free tier limits
    "gemini":     {"rpm": 15,  "tpm": 1000000},    # Gemini 1.5 Flash standard
    "mistral":    {"rpm": 60,  "tpm": 200000},     # 1 RPS approx
    "cerebras":   {"rpm": 30,  "tpm": 60000},      # Assumed standard tier
    "openrouter": {"rpm": 10,  "tpm": 40000},      # Free tier limits
}

class ProviderGovernor:
    def __init__(self):
        # Format: deque of tuples (timestamp, tokens)
        self._history: Dict[str, deque[Tuple[float, int]]] = {
            p: deque() for p in PROVIDER_LIMITS.keys()
        }
        self._lock = asyncio.Lock()

    def _cleanup_old_records(self, provider: str, now: float) -> None:
        """Removes records older than 60 seconds."""
        history = self._history[provider]
        while history and (now - history[0][0]) >= 60.0:
            history.popleft()

    async def wait_if_needed(self, provider: str, estimated_tokens: int = 0) -> None:
        """
        Check if the incoming request will exceed the provider's RPM or TPM.
        If so, wait just enough time for the sliding window to clear capacity.
        """
        if provider not in PROVIDER_LIMITS:
            return  # Unmetered or unknown provider

        limits = PROVIDER_LIMITS[provider]
        
        async with self._lock:
            now = time.time()
            self._cleanup_old_records(provider, now)

            history = self._history[provider]
            current_reqs = len(history)
            current_tokens = sum(t for _, t in history)

            wait_ms = 0

            # Check RPM
            if current_reqs >= limits["rpm"]:
                oldest_time = history[0][0]
                wait_time = 60.0 - (now - oldest_time)
                if wait_time > 0:
                    wait_ms = max(wait_ms, int(wait_time * 1000))

            # Check TPM
            if current_tokens + estimated_tokens >= limits["tpm"]:
                # Find how long until enough tokens are freed
                freed_tokens = 0
                required = (current_tokens + estimated_tokens) - limits["tpm"]
                
                for timestamp, tkns in history:
                    freed_tokens += tkns
                    if freed_tokens >= required:
                        wait_time = 60.0 - (now - timestamp)
                        if wait_time > 0:
                            wait_ms = max(wait_ms, int(wait_time * 1000))
                        break

            # If we need to wait, emit UI broadcast and sleep
            if wait_ms > 0:
                logger.warning(f"⏳ [Governor] Rate limit approaching for '{provider}'. Pausing {wait_ms}ms (Tokens: {estimated_tokens})")
                
                # Emit WebSocket Broadcast
                from core.workspace.broadcast import broadcast_workspace_state
                asyncio.create_task(broadcast_workspace_state(
                    status="rate_limit_cooldown",
                    last_result=f"{provider} cooling down for {wait_ms}ms"
                ))

                await asyncio.sleep(wait_ms / 1000.0)
                
                # Re-sync time after sleep
                now = time.time()
                self._cleanup_old_records(provider, now)

            # Log the new request execution
            self._history[provider].append((now, estimated_tokens))

# Singleton Instance
governor = ProviderGovernor()
