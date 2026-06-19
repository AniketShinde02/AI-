"""
session_state.py
-----------------
Responsibility: Session state machine, transcript sanitizers, VAD processing, and process_audio.
Extracted from voice_session.py to isolate the VAD/audio ingestion layer.

DO NOT import from voice_session.py here — this module is imported by voice_session.py.
"""
import re
import time
import asyncio
import logging
from enum import Enum
from collections import deque
from typing import Optional, Deque, Any

import numpy as np
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("nexus_ws")


class SessionState(Enum):
    IDLE      = "idle"
    LISTENING = "listening"
    DEBOUNCE  = "debounce"   # Silence detected, waiting to finalize turn
    THINKING  = "thinking"   # Processing STT/LLM
    SPEAKING  = "speaking"   # AI is outputting audio


class SessionStateMixin:
    """
    Mixin that owns all VAD-level audio processing, state transitions,
    and transcript/TTS sanitization.

    Expects the host class to provide:
      self.state             : SessionState
      self.audio_buffer      : bytearray
      self.vad_chunk_buffer  : bytearray
      self.vad_preroll_buffer: Deque[bytes]
      self.vad_iterator      : VADIterator (from global_state)
      self.is_muted          : bool
      self.agent_is_speaking : bool
      self.is_connected      : bool
      self.websocket         : WebSocket
      self.last_audio_time   : float
      self.last_agent_speech_time : float
      self.speech_start_time : float
      self.debounce_task     : Optional[asyncio.Task]
      self.post_tts_guard_until : float
      self.post_tts_guard_time  : float
      self.vad_threshold_normal : float
      self.ambient_noise_level  : float
      self.silence_threshold    : float
      self.min_speech_duration  : float
      self.barge_in_threshold   : float
      self.current_turn_id      : int
      self.sample_rate          : int
      self.recent_ai_outputs    : Deque[str]
    """
    state: SessionState
    audio_buffer: bytearray
    vad_chunk_buffer: bytearray
    vad_preroll_buffer: Deque[bytes]
    vad_iterator: Any
    is_muted: bool
    agent_is_speaking: bool
    is_connected: bool
    websocket: WebSocket
    last_audio_time: float
    last_agent_speech_time: float
    speech_start_time: float
    debounce_task: Optional[asyncio.Task]
    post_tts_guard_until: float
    post_tts_guard_time: float
    vad_threshold_normal: float
    ambient_noise_level: float
    silence_threshold: float
    min_speech_duration: float
    barge_in_threshold: float
    current_turn_id: int
    sample_rate: int
    recent_ai_outputs: Deque[str]

    async def stop_audio(self) -> None:
        pass

    async def run_pipeline(self) -> None:
        pass

    async def debounce_turn(self) -> None:
        pass

    # -----------------------------------------------------------------
    # State helpers
    # -----------------------------------------------------------------

    def _change_state(self, new_state: SessionState):
        if self.state != new_state:  # type: ignore[attr-defined]
            logger.info(f"🔄 [STATE] {self.state.name} -> {new_state.name}")  # type: ignore[attr-defined]
            self.state = new_state  # type: ignore[attr-defined]
            if new_state == SessionState.IDLE:
                self.audio_buffer.clear()  # type: ignore[attr-defined]

    def get_dynamic_threshold(self) -> float:
        return max(1800, self.ambient_noise_level * 6.0)  # type: ignore[attr-defined]

    def is_filler(self, text: str) -> bool:
        """Determines if a sentence is just a filler word to skip TTS."""
        lower_text = text.lower().strip(".?!, ")
        fillers = ["hmm", "okay", "alright", "uh", "um", "ah", "mhm", "uh-huh", "right"]
        return lower_text in fillers

    # -----------------------------------------------------------------
    # Transcript sanitizer
    # -----------------------------------------------------------------

    def sanitize_transcript(self, text: str) -> Optional[str]:
        """Filter out garbage/nonsense transcripts before LLM dispatch."""
        text = text.strip()
        if not text:
            return None

        # 1. Reject repeating single characters ("A. A. B. B…")
        if len(text) > 10 and len(set(text.lower())) < 5:
            logger.warning(f"🗑 Rejecting repetitive character pattern: {text}")
            return None

        # 2. Reject transcripts with no letters at all
        if not re.search(r'[a-zA-Z\u0900-\u097f]', text):
            return None

        # 3. Reject tiny nonsense tokens (< 3 chars that aren't Devanagari)
        if len(text) < 3 and not any('\u0900' <= c <= '\u097f' for c in text):
            return None

        # 4. Reject common Whisper silence hallucinations
        junk_phrases = [
            "thank you.", "thank you", "bye.", "bye", "am.", "hm.", "stop.", "you.",
            "i.", "the.", "a.", "it's.", "associate.", "subtitles by", "uh", "um", "ah",
            "Please subscribe", "Thanks for watching", "I'll see you in the next one",
            "Mhm", "Uh-huh", "Yeah.", "Okay.", "Right.", "Go ahead.", "I'm listening.",
            "Tell me more.", "Yes.", "No.", "Alright.", "Cool.", "Sure."
        ]
        hallucination_keywords = [
            "pedro negri", "amara.org", "transcrição e legendas", "subtitles by", "terima kasih"
        ]
        lower_text = text.lower().strip(".?!, ")

        if any(keyword in lower_text for keyword in hallucination_keywords):
            logger.info(f"🗑 Filtered Whisper hallucination: {text}")
            return None

        if any(lower_text == j.lower().strip(".?!, ") for j in junk_phrases):
            logger.info(f"🗑 Filtered junk phrase: {text}")
            return None

        # 5. Reject CJK / Cyrillic scripts (out-of-domain)
        if re.search(r'[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af\u0400-\u04ff]', text):
            logger.warning(f"🗑 Rejecting out-of-domain scripts (CJK/Cyrillic): {text}")
            return None

        return text

    # -----------------------------------------------------------------
    # TTS text sanitizer
    # -----------------------------------------------------------------

    def sanitize_for_tts(self, text: str) -> str:
        """Clean text before sending to TTS to prevent phonemizer mismatches."""
        try:
            from text_normalizer import format_spelled_out_words
            text = format_spelled_out_words(text)
        except ImportError:
            pass

        # Remove emojis and symbols; keep dashes and standard punctuation
        text = re.sub(r'[^\w\s\.,\?\!\-\u0900-\u097f]', ' ', text)
        text = text.replace("...", ", ")
        text = text.replace(" - ", ", ")
        text = re.sub(r'\s+', ' ', text).strip()

        try:
            from pronunciation_dictionary import apply_pronunciation, apply_speech_director
            text = apply_speech_director(text)
            text = apply_pronunciation(text)
        except ImportError:
            pass

        return text

    # -----------------------------------------------------------------
    # VAD audio processing
    # -----------------------------------------------------------------

    async def process_audio(self, data: bytes):
        """Process raw PCM chunks with Silero VAD and turn management."""
        import torch

        if self.is_muted:  # type: ignore[attr-defined]
            return

        current_time = time.time()

        # Gate 1: Hard mute while AI is physically outputting audio
        if self.agent_is_speaking:  # type: ignore[attr-defined]
            return

        # Gate 2: Post-TTS echo guard window
        in_guard = (
            self.post_tts_guard_until > 0  # type: ignore[attr-defined]
            and current_time < self.post_tts_guard_until  # type: ignore[attr-defined]
        )
        if in_guard:
            remaining = self.post_tts_guard_until - current_time  # type: ignore[attr-defined]
            logger.debug(f"🛡️ [Guard] VAD blocked — echo guard active ({remaining:.2f}s remaining)")
            if self.state in [SessionState.LISTENING, SessionState.IDLE, SessionState.DEBOUNCE]:  # type: ignore[attr-defined]
                self.vad_preroll_buffer.append(data)  # type: ignore[attr-defined]
            self.last_audio_time = current_time  # type: ignore[attr-defined]
            return

        # Accumulate audio while listening/debouncing
        if self.state in [SessionState.LISTENING, SessionState.DEBOUNCE]:  # type: ignore[attr-defined]
            self.audio_buffer.extend(data)  # type: ignore[attr-defined]

        self.vad_chunk_buffer.extend(data)  # type: ignore[attr-defined]
        if self.state in [SessionState.LISTENING, SessionState.IDLE, SessionState.DEBOUNCE]:  # type: ignore[attr-defined]
            self.vad_preroll_buffer.append(data)  # type: ignore[attr-defined]

        chunk_size = 1024
        while len(self.vad_chunk_buffer) >= chunk_size:  # type: ignore[attr-defined]
            chunk = self.vad_chunk_buffer[:chunk_size]  # type: ignore[attr-defined]
            self.vad_chunk_buffer = self.vad_chunk_buffer[chunk_size:]  # type: ignore[attr-defined]

            samples = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
            tensor = torch.from_numpy(samples)
            rms_energy = float(torch.sqrt(torch.mean(tensor ** 2)))

            speech_dict = self.vad_iterator(tensor, return_seconds=True)  # type: ignore[attr-defined]

            if speech_dict:
                if 'start' in speech_dict:
                    if rms_energy < self.ambient_noise_level:  # type: ignore[attr-defined]
                        speech_dict = {}
                    elif self.state != SessionState.LISTENING:  # type: ignore[attr-defined]
                        if self.debounce_task:  # type: ignore[attr-defined]
                            self.debounce_task.cancel()  # type: ignore[attr-defined]
                            self.debounce_task = None  # type: ignore[attr-defined]

                        self._change_state(SessionState.LISTENING)
                        self.speech_start_time = time.time()  # type: ignore[attr-defined]

                        preroll_context = b"".join(self.vad_preroll_buffer)  # type: ignore[attr-defined]
                        self.audio_buffer = bytearray(preroll_context) + self.audio_buffer  # type: ignore[attr-defined]
                        self.vad_preroll_buffer.clear()  # type: ignore[attr-defined]
                        logger.debug(
                            f"🎤 [VAD] Speech START | Energy: {rms_energy:.4f} "
                            f"| Preroll: {len(preroll_context)}B"
                        )

            # Safety net: hard timeout prevents infinite listening
            if self.state == SessionState.LISTENING and not speech_dict:  # type: ignore[attr-defined]
                duration = current_time - self.speech_start_time  # type: ignore[attr-defined]
                if duration > 7.0:
                    logger.warning(f"[FORENSIC] VAD_FORCED_END reason=MAX_DURATION duration={duration:.3f}s")
                    speech_dict = {'end': current_time}

            if speech_dict:
                if 'end' in speech_dict:
                    if self.state == SessionState.LISTENING:  # type: ignore[attr-defined]
                        duration = current_time - self.speech_start_time  # type: ignore[attr-defined]
                        logger.debug(
                            f"🎤 [VAD] Speech END | Duration: {duration:.2f}s | Energy: {rms_energy:.4f}"
                        )

                        if duration < self.min_speech_duration:  # type: ignore[attr-defined]
                            logger.debug(
                                f"🗑 [VAD] Rejected | Too short "
                                f"({duration:.2f}s < {self.min_speech_duration}s)"
                            )
                            self._change_state(SessionState.IDLE)
                        else:
                            recently_speaking = (
                                current_time - self.last_agent_speech_time  # type: ignore[attr-defined]
                            ) < 3.0
                            if recently_speaking and duration > self.barge_in_threshold:  # type: ignore[attr-defined]
                                logger.info(
                                    f"💥 [Barge-in] User spoke {duration:.2f}s over AI. Interrupting."
                                )
                                await self.stop_audio()  # type: ignore[attr-defined]
                                await self.websocket.send_json({"type": "interrupt"})  # type: ignore[attr-defined]
                                self._change_state(SessionState.IDLE)
                                asyncio.create_task(self.run_pipeline())  # type: ignore[attr-defined]
                            else:
                                if self.state not in [SessionState.THINKING, SessionState.SPEAKING]:  # type: ignore[attr-defined]
                                    self._change_state(SessionState.DEBOUNCE)
                                    logger.debug(
                                        f"⏳ [VAD] Debouncing for {self.silence_threshold}s..."  # type: ignore[attr-defined]
                                    )
                                    if self.debounce_task:  # type: ignore[attr-defined]
                                        self.debounce_task.cancel()  # type: ignore[attr-defined]
                                    self.debounce_task = asyncio.create_task(  # type: ignore[attr-defined]
                                        self.debounce_turn()  # type: ignore[attr-defined]
                                    )
                                else:
                                    logger.info(
                                        f"⏳ [VAD] Already in {self.state.value}, skipping debounce."  # type: ignore[attr-defined]
                                    )

        self.last_audio_time = current_time  # type: ignore[attr-defined]
