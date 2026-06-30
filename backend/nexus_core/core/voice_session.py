"""
voice_session.py — Backward Compatibility Shim
==============================================
DO NOT add logic here. All behavior lives in core/voice/session.py.
"""
from core.voice.session import VoiceSession

__all__ = ["VoiceSession"]
