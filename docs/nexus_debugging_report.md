# Nexus Voice Pipeline: Production Debugging Report

## A. Root Cause Ranking

1. **🔴 Unbounded Audio Buffer Append (40%)**
   - **Issue:** Raw audio is unconditionally appended to `self.audio_buffer` during the `IDLE` state.
   - **Impact:** Causes massive (5MB) silent payloads to reach Whisper, triggering severe hallucinations.
2. **🟠 Whisper Silence Hallucination (20%)**
   - **Issue:** Long silent audio files inherently cause Whisper V3 to hallucinate Youtube subtitles.
   - **Impact:** Fills the LLM context with garbage like "Thank you for watching."
3. **🟡 VAD State Machine Race Condition (15%)**
   - **Issue:** Preroll context is prepended to an already bloated buffer on speech `start`, and the state machine resets the buffer haphazardly on "Speech too short".
   - **Impact:** Causes repeated cutoffs and "Speech too short" log spam.
4. **🟡 Phonemizer Language Incompatibility (10%)**
   - **Issue:** Kokoro's backend (`espeak`) natively processes English phonemes. It lacks context-aware Indian language switching.
   - **Impact:** Hindi/Marathi text generates warnings and drops syllables.
5. **🟢 Echo-induced Self-Interruption (10%)**
   - **Issue:** Delayed WebRTC/WebSocket audio leaks back into the microphone, triggering the `barge_in_threshold`.
   - **Impact:** Assistant interrupts itself.
6. **🟢 Frontend Jitter Buffer Starvation (5%)**
   - **Issue:** Sentence-chunking delays cause the frontend to send `audio_finished` prematurely.
   - **Impact:** Triggers backend state resets while the LLM is still generating.

---

## B. Issue Origins

* **Microphone capture:** Not the root cause (hardware is fine).
* **VAD:** Contributes to cutoff issues (timers too rigid).
* **Buffering:** **Major Root Cause.** Infinite append during `IDLE`.
* **WebSocket transport:** Causes jitter, but not the source of hallucinations.
* **STT (Whisper):** Hallucinates natively when fed bad/silent buffers.
* **TTS (Kokoro):** Fails on code-switching (Phonemizer mismatch).
* **Frontend playback:** Starvation causes premature `audio_finished`.
* **Echo cancellation:** Insufficient backend deaf-window causes self-interruption.
* **State machine logic:** **Major Root Cause.** Poor buffer lifecycle management across `IDLE`, `LISTENING`, and `DEBOUNCE`.

---

## C. Why Whisper Generates Hallucinations
Because `ws_main.py` unconditionally executes `self.audio_buffer.extend(data)` on line 376 regardless of `SessionState`, the buffer accumulates pure silence whenever the user isn't speaking. If the user stays quiet for 2 minutes, then speaks a 3-second sentence, a 2-minute-and-3-second audio file is sent to Whisper API. Whisper V3 is notoriously susceptible to "silence hallucinations," wherein it attempts to transcribe static as common training data phrases like "Thank you for watching" or "Please subscribe."

## D. Why VAD Repeatedly Starts and Stops
The ambient noise level combined with a highly sensitive threshold (`1800` dynamic) causes small background noises (keyboard clicks, fans) to trigger `start`. Because these noises end quickly (under `min_speech_duration` of `0.3s`), the VAD immediately logs "Speech too short, ignoring" and resets. This constant start/stop cycle fills the logs.

## E. Why Huge Silent Recordings Reach Whisper
As proven in **C**, there is no logic restricting `self.audio_buffer.extend(data)` to only the `LISTENING` state. The buffer grows infinitely while `IDLE`.

## F. Why Hindi and Marathi Speech Produce Phonemizer Warnings
Kokoro relies on the `espeak-ng` phonemizer. When initialized with the default `en-us` voice (`hf_alpha`), it uses the English phoneme dictionary. When fed native Devanagari script or Romanized Hinglish ("Main theek hoon"), `espeak` fails to map the characters to valid English phonemes, resulting in "words count mismatch" warnings, garbled pronunciation, and skipped audio.

## G. Is Kokoro the Correct Model for Multilingual Indian Speech?
**No.** Kokoro (in its default English-tuned ONNX configuration) is exceptionally high-quality for US/UK English, but structurally lacks native code-switching capabilities for Indian regional languages without a dedicated Indian-English/Hindi voice pack or an external transliteration pre-processor.

## H. Should Piper Handle Hindi/Marathi Instead?
**Yes, conditionally.** Piper has dedicated, native models for Hindi (`hi_IN`) and Marathi (`mr_IN`). However, routing requires the backend to detect the language *before* synthesis and explicitly switch the model pipeline, rather than relying on a single model to auto-detect and code-switch mid-sentence.

## I. Can Frontend Playback Leak Assistant Audio Back?
**Yes.** Without a robust WebRTC Echo Cancellation node, speakers play the AI's voice directly into the user's microphone. The backend attempts to handle this with a static `0.8s` "deaf window," but network jitter frequently causes the audio to arrive *after* the 0.8s window expires, triggering a false VAD "Barge-in".

## J. Are `audio_finished` Messages Fired Too Early?
**Yes.** The AudioWorklet relies on a strict starvation timeout. If the backend LLM pauses mid-thought (e.g., waiting for the next sentence chunk), the frontend buffer drains. The worklet assumes the stream is over and fires `audio_finished`. The backend receives this, resets `agent_is_speaking` to `False`, and opens the microphone, completely breaking the state flow.

## K. Do State Transitions Contain Race Conditions?
**Yes.** 
1. If the user interrupts the agent (`barge-in`), the state is forced to `IDLE` and `run_pipeline()` is instantly spawned. However, the agent might still be receiving delayed STT/TTS packets, causing interleaved audio.
2. The `DEBOUNCE` state cancels and restarts its timer continuously, but the `audio_buffer` retains the old prepended preroll data, corrupting the alignment of the PCM bytes.

---

## L. Required Metrics Before Changing Code

Before implementing fixes, the following metrics must be instrumented to validate the changes:
1. `buffer_size_bytes_at_stt_dispatch`: To prove the silent-buffer bug is fixed.
2. `vad_start_to_debounce_latency_ms`: To measure actual human pause lengths.
3. `vad_false_trigger_count`: Number of "speech too short" events per minute.
4. `frontend_starvation_events`: Count of times the jitter buffer hits 0 during an active turn.
5. `tts_phonemizer_warnings`: Count of `words count mismatch` logs per language.
6. `echo_cancellation_failures`: Instances where `barge_in` was triggered by the AI's exact generated transcript.

---

## Output Format Requirements

### 1. Root Cause Ranking
(See section A above)

### 2. Evidence from logs
- `STT receives recordings between 500KB and 5MB`: Evidence of unbounded `audio_buffer.extend(data)`.
- `"Thank you for watching"`: Textbook Whisper V3 silence hallucination.
- `"Speech too short, ignoring"`: Evidence of sensitive VAD noise triggers.
- `words count mismatch`: Evidence of `espeak` rejecting Devanagari unicode.

### 3. Debugging plan
1. Instrument the `audio_buffer` length at the moment `run_pipeline` is called.
2. Output the exact PCM duration (in seconds) sent to Whisper.
3. Track the frontend buffer size over time via WebSocket telemetry.

### 4. Required instrumentation
(See section L above)

### 5. Validation tests
1. Sit in silence for 60 seconds, then say "Hello." Verify the payload sent to STT is exactly ~1-2 seconds long, not 61 seconds.
2. Play the AI's voice loudly through speakers. Verify the VAD ignores it and does not trigger barge-in.
3. Speak a mix of English and Hindi. Monitor Kokoro logs for `mismatch` warnings.

### 6. Exact fixes
1. **Buffer Scope:** Move `self.audio_buffer.extend(data)` inside `if self.state in [SessionState.LISTENING, SessionState.DEBOUNCE]:`.
2. **Buffer Flush:** Clear `self.audio_buffer` upon entering the `IDLE` state, keeping only the rolling `vad_preroll_buffer`.
3. **Phonemizer:** Route Hindi/Marathi detected transcripts explicitly to Piper's `hi_IN` or `mr_IN` models instead of Kokoro.
4. **Starvation:** Increase frontend `minBuffer` and implement a "Stream End" marker from the backend instead of relying on starvation timeouts.

### 7. Fix priority order
1. Scope `audio_buffer` to `LISTENING`/`DEBOUNCE` only. (Fixes 5MB files & hallucinations)
2. Clear buffer explicitly on `IDLE`. (Fixes memory leaks)
3. Implement "Stream End" websocket packet. (Fixes premature `audio_finished`)
4. Route Indian languages to Piper. (Fixes phonemizer warnings)
5. Implement dynamic Echo Cancellation window. (Fixes self-interruption)
