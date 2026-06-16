# HERMES_EXTRACTION_PLAN.md
## What to Take From Hermes — Evidence-Based, No Blind Copying

### Hermes Architecture Observed
**Source:** `d:\debugging\Stonic-AI-Source-Code\Hermes-Agent\`

Hermes is a multi-platform **messaging-first** agent (Telegram, Discord, Slack, WhatsApp). It does NOT have a real-time voice pipeline. It handles voice as optional file attachments with STT (via OpenAI Whisper API), not as a streaming microphone loop.

**Key File:** `gateway/run.py` (~816KB — the Hermes "God File" equivalent)
**Voice Evidence from `run.py`:**
```python
# No STT provider → graceful degradation
if "No STT provider" in error or error.startswith("Neither VOICE_TOOLS_OPENAI_KEY..."):
    _no_stt_note = "[The user sent a voice message but I can't listen to it right now]"
```

Hermes's voice is asynchronous (file upload), not real-time streaming. IRIS and Nexus are real-time.

---

### What is Actually Extractable

#### 1. State Isolation Pattern (HIGH VALUE)
**Evidence:** `gateway/run.py` defines `_release_running_agent_state()`, `_clear_session_boundary_security_state()`, `_interrupt_and_clear_queue()` as separate, named methods.

The key insight: Hermes has **strict separation of per-turn state vs. per-session state**:
```python
# Per-turn state (cleared on every turn end):
_running_agents, _pending_messages

# Per-session state (NOT cleared between turns):
_session_model_overrides, _voice_mode, _pending_approvals
```
**Apply to Nexus:** In `ws_main.py`, the `VoiceSession` class mixes all state together. The preroll buffer bug exists partly because there's no clear boundary between "turn state" (should reset) and "session state" (should persist).

#### 2. Generation Counter for Stale Task Prevention (HIGH VALUE)
**Evidence from `run.py`:**
```python
run_generation = ...
# Only release slot if this run's generation still owns it.
# A /stop or /new that bumped the generation while we were
# unwinding has already installed its own state...
self._release_running_agent_state(session_key, run_generation=run_generation)
```
Nexus already has a `turn_id` pattern in `ws_main.py` (`if turn_id != self.current_turn_id: return`), which is the same concept. **This is already correctly implemented in Nexus.** No changes needed.

#### 3. Dependency Checking at Startup (`main.py` pattern)
**Evidence:** `hermes_cli/main.py` checks for `node`, `browser`, `ripgrep`, `ffmpeg` before launching.
**Apply to Nexus:** Create a startup health check that validates GROQ_API_KEY, GEMINI_API_KEY, and silero_vad model presence before accepting WebSocket connections.

#### 4. FFmpeg Dependency (NOT APPLICABLE)
Hermes requires ffmpeg for voice message conversion (OGG → WAV). Nexus receives raw PCM directly from the browser. **No ffmpeg needed in Nexus.**

#### 5. `[[audio_as_voice]]` Directive Pattern (INTERESTING)
**Evidence from `run.py`:**
```python
if "[[audio_as_voice]]" in content:
    has_voice_directive = True
```
Hermes uses in-band text directives to signal whether a response should be spoken or just displayed as text. This is a clean way to gate TTS — only synthesize audio for responses that make sense to speak aloud.
**Apply to Nexus:** The LLM could be instructed to prefix certain responses with `[SPEAK]` or `[TEXT_ONLY]` to skip TTS on long code blocks or markdown tables.

---

### What NOT to Copy

| Pattern | Why NOT |
|---------|---------|
| Hermes's full `gateway/run.py` | 816KB god file. Same anti-pattern as `ws_main.py`. |
| Hermes's STT (file upload) | Nexus needs real-time streaming, not async file transcription |
| Hermes's Discord/Telegram adapters | Not relevant to Nexus's WebSocket-browser architecture |
| Hermes's auth/pairing system | Nexus uses Firebase Auth |
