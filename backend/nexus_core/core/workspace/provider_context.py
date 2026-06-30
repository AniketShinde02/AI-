"""
provider_context.py
===================
Exposes structured provider health from ProviderGovernor.

Design rules:
  - Reads from governor._history (the in-memory sliding window deque)
  - TTL: 1s — governor data is already in-memory, very cheap
  - Never calls external APIs
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from core.workspace.workspace_state import ProviderState

logger = logging.getLogger("nexus.workspace.provider")

_TTL_PROVIDER = 1.0


class ProviderContext:
    """
    Gathers provider state from ProviderGovernor.
    Consumed only by WorkspaceManager.
    """

    def __init__(self) -> None:
        self._cache: Optional[ProviderState] = None
        self._cache_ts: float = 0.0

    async def collect(self) -> ProviderState:
        now = time.monotonic()
        if self._cache and (now - self._cache_ts) < _TTL_PROVIDER:
            return self._cache

        state = self._build_state()
        self._cache = state
        self._cache_ts = now
        return state

    def _build_state(self) -> ProviderState:
        try:
            from core.provider.governor import governor, PROVIDER_LIMITS
            from core.provider.router import model_router

            # Determine active provider from model_router if available
            active_provider = "groq"
            active_model = "unknown"
            try:
                # model_router exposes _active_provider if set
                active_provider = getattr(model_router, "_active_provider", "groq")
                active_model = getattr(model_router, "_active_model", "unknown")
            except Exception:
                pass

            # Compute RPM/TPM from governor sliding window
            now_ts = time.time()
            history = governor._history.get(active_provider, [])
            # Clean stale records
            recent = [(ts, tkns) for ts, tkns in history if (now_ts - ts) < 60.0]
            rpm_used = len(recent)
            tpm_used = sum(t for _, t in recent)
            limits = PROVIDER_LIMITS.get(active_provider, {"rpm": 30, "tpm": 6000})

            return ProviderState(
                active_provider=active_provider,
                active_model=active_model,
                is_healthy=True,
                rpm_used=rpm_used,
                rpm_limit=limits["rpm"],
                tpm_used=tpm_used,
                tpm_limit=limits["tpm"],
            )
        except Exception as e:
            logger.debug(f"Provider context collection failed: {e}")
            return ProviderState()
