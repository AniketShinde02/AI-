"""
session_tts_worker.py — Backward Compatibility Shim
===================================================
DO NOT add logic here. All behavior lives in core/voice/tts_worker.py.
"""
from core.voice.tts_worker import SessionTTSMixin

__all__ = ["SessionTTSMixin"]
