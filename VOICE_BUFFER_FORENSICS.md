# VOICE_BUFFER_FORENSICS.md
## Finding A Validated — Confirmed Root Cause

### Evidence Summary
Terminal log proof (verbatim):
```
🎤 [VAD] Speech start detected (preroll=409600B, state was listening)
🎤 [VAD] Speech end — duration=2.30s
🛰 [STT] Dispatching 15.4 seconds (491520 bytes)
```
User spoke 2.3 seconds. Backend dispatched 15.4 seconds. **Delta = 13.1 seconds of stale audio.**

---

### Exact Root Cause — Three Compounding Bugs

#### Bug 1: Preroll Buffer Never Clears Between Turns
**File:** `d:\AI\backend\voice_agent\ws_main.py`
**Line:** `self.vad_preroll_buffer: Deque[bytes] = deque(maxlen=50)  # ~2-3 seconds context`

The comment says "2-3 seconds context." This is **wrong.**

**Math:**
- Frontend sends audio chunks of 8192 bytes (confirmed from log: `MIC_FRAME_RECEIVED bytes=8192`)
- `maxlen=50` means the deque holds 50 × 8192 = **409,600 bytes**
- At 16kHz, 16-bit mono: bytes_per_second = 16000 × 1 × 2 = **32,000 bytes/sec**
- 409,600 ÷ 32,000 = **12.8 seconds of stale audio**
- This is the 409,600B confirmed in every log line.

#### Bug 2: Preroll is Prepended to Active Speech Buffer
**File:** `d:\AI\backend\voice_agent\ws_main.py`
**Function:** `process_audio()`
```python
preroll_context = b"".join(self.vad_preroll_buffer)
self.audio_buffer = bytearray(preroll_context) + self.audio_buffer
```
The 12.8 seconds of stale preroll is **prepended** to the actual speech, so the entire 15.4 second blob gets sent to Groq.

#### Bug 3: Preroll Accumulates During THINKING and SPEAKING States
**File:** `d:\AI\backend\voice_agent\ws_main.py`
**Function:** `process_audio()` (guard block):
```python
# During post-TTS guard:
self.vad_preroll_buffer.append(data)  # Still accumulates!
```
While the AI is synthesizing and speaking, audio continues streaming from the microphone and gets appended to the preroll. By the time the user speaks their next word, the buffer already contains 10-12 seconds of silence/room noise.

---

### Current (Broken) Flow
```
Mic (continuous stream) → process_audio()
  ↓
  vad_preroll_buffer.append(data)  ← ALWAYS accumulates, never resets
  ↓
  [VAD speech_start detected]
  ↓
  preroll_context = b"".join(vad_preroll_buffer)  ← 12.8s blob
  ↓
  audio_buffer = preroll_context + active_speech  ← 15.4s total
  ↓
  STT dispatch → Groq Whisper → 15.4 seconds sent
```

### Correct Target Flow
```
Mic → process_audio()
  ↓
  preroll_ring_buffer: 500ms max (8,000 bytes = 0.5s × 16,000 × 2)
  ↓
  [VAD speech_start detected]
  ↓
  audio_buffer = preroll_context (500ms) + active_speech (2.3s)  ← 2.8s total
  ↓
  [VAD speech_end detected]
  ↓
  preroll_buffer.clear()  ← CRITICAL: reset after dispatch
  ↓
  STT dispatch → Groq Whisper → 2.8 seconds
```

### Fix Required
1. Change `maxlen=50` to `maxlen=8` (8 × 8192 = 65,536 bytes = ~2 seconds max)
2. Add `self.vad_preroll_buffer.clear()` immediately after prepending it to `audio_buffer`
3. Stop accumulating preroll during THINKING and SPEAKING states (gate it behind state check)
