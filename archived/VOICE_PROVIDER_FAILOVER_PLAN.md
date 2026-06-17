# VOICE_PROVIDER_FAILOVER_PLAN.md
## Rate Limit Resilience — Provider Failover Architecture

### Current State (Evidence)
- **Primary TTS:** Gemini (`generateContent` REST) — File: `providers/tts_gemini.py`
- **Fallback TTS:** Edge TTS — File: `providers/tts_edge.py`
- **STT:** Groq Whisper large-v3 only — File: `ws_main.py` Line ~840
- **LLM:** Groq llama-3.3-70b-versatile only — File: `providers/llm.py`

**Current Problem:** Single-point-of-failure on Groq for STT+LLM simultaneously. If Groq rate-limits, both input understanding and response generation fail together.

---

### Recommended Provider Hierarchy

#### Voice Input (STT) Chain
```
Primary:   Groq Whisper large-v3 (free, 7200 audio-minutes/day free)
Fallback:  Gemini speech-to-text (if Groq 429)
Emergency: Edge TTS voice-to-text is not viable — no free local STT in current setup
```

#### Voice Output (TTS) Chain
```
Primary (Target V3): Gemini Live (bidirectional stream, built-in TTS, zero TTFA)
Primary (Current):   Gemini TTS REST (generateContent, ~4-7s TTFA)
Fallback 1:          Edge TTS (en-IN-PrabhatNeural / NeerjaNeural, ~200ms TTFA, MP3)
Fallback 2:          OpenRouter with edge-compatible model (future)
```

#### LLM Chain
```
Primary:   Groq llama-3.3-70b-versatile (fast, free tier)
Fallback:  Gemini 2.0 Flash (via google-genai, free tier 1500 req/day)
Emergency: OpenRouter (requires API key — optional)
```

---

### Failover Logic Requirements

The existing `TTSProviderRouter` in `providers/tts.py` already implements a **chain fallback** pattern (Lines 89-120). The same pattern must be applied to STT and LLM:

```python
# Current TTS chain (existing, working):
base_chain = ["gemini", "edge"]
for p_key in chain:
    try:
        yield from provider.stream_audio(text)
        break  # Success
    except Exception:
        continue  # Try next
```

This pattern works correctly for TTS. It needs to be extended to:
1. **STT:** Catch `groq.RateLimitError` specifically, fallback to Gemini STT
2. **LLM:** Catch `groq.RateLimitError`, fallback to `google-genai` Flash

---

### Specific Rate Limit Signals to Catch

**Groq:**
```python
except groq.RateLimitError as e:
    # HTTP 429: Switch to fallback immediately
    # Do NOT retry Groq for at least 60 seconds
```

**Gemini REST TTS (current):**
```python
# asyncio.TimeoutError: API call timed out after 15.0s (tts_gemini.py line ~80)
# RuntimeError: GeminiTTS: API returned no response
```

---

### No-User-Visible-Failure Requirements
1. State machine must stay in THINKING, not crash to IDLE, during provider switch.
2. First audio chunk must be delivered before frontend shows a timeout.
3. Conversation history must survive the provider switch (no context loss).
4. Frontend must show "Working..." state, not "Error" state, during failover.
