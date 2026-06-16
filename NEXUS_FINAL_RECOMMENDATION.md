# NEXUS_FINAL_RECOMMENDATION.md
## Final Architecture Decision — Evidence Based

### Decision: OPTION C — Hybrid Architecture

**Reasoning:**
- Option A (Keep current pipeline as-is): Rejected. The current pipeline has 3 confirmed critical bugs that make it 10-18 seconds slow. It cannot become competitive without the fixes regardless.
- Option B (Gemini Live primary, current pipeline fallback): Partially correct, but Gemini Live on free tier has strict RPM limits that make it dangerous as the sole primary for a production assistant.
- Option C (Hybrid): **Correct.** Fix the current pipeline first (making it 2-3s), then layer Gemini Live on top as the fast path. This gives reliability + speed.

---

### The Hybrid Plan (Ordered by Priority)

#### Immediate Fixes (Critical — Backend Will Crash Without These)
These are not architectural decisions. They are bugs.

1. **Fix `providers/tts.py`**: Remove dead `getstream`, `vision_agents`, `kokoro_onnx` imports. These WILL crash the backend on a clean restart.
2. **Fix `providers/tts_gemini.py`**: Remove dead `getstream`, `vision_agents` imports.
3. **Fix `providers/tts_edge.py`**: Remove dead `getstream`, `vision_agents` imports.

#### Phase V3.1 — Pipeline Repair (Makes current architecture viable)
4. **Fix preroll buffer**: `ws_main.py` — change `maxlen=50` to `maxlen=8`. Expected improvement: STT payload drops from 15.4s to 2.5s. Latency drops by ~8 seconds.
5. **Fix SpeechCleaner model**: `speech_cleaner.py` — change `llama3-8b-8192` to `llama-3.1-8b-instant`. Restores filler removal.
6. **Swap TTS to Edge TTS (Indian accent)**: `providers/tts.py` — change provider chain from `["gemini", "edge"]` to `["edge", "gemini"]`. Restores Indian accent.
7. **Wire `prompts.py` into `ws_main.py`**: Replace minimal inline prompt with `get_nexus_system_prompt()`. Restores Nexus personality.
8. **Add conversation history**: Add rolling 8-turn message buffer to every LLM call. Restores cross-turn coherence.

**Expected outcome after V3.1:** Total latency drops to 2-3 seconds. Indian accent consistent. Personality consistent.

#### Phase V3.2 — Gemini Live Fast Path (Makes architecture excellent)
9. **Harden `experimental/gemini_live_voice.py`**: Add reconnection, interruption handling, conversation injection, tool call interception.
10. **Add as `/ws/nexus-live`** route with automatic failover to `/ws/nexus` (current pipeline) if Gemini Live session fails or rate-limits.
11. **Frontend switch**: Frontend detects which mode is active and shows the correct state UI.

**Expected outcome after V3.2:** Gemini Live path achieves 700ms TTFA. Fallback to repaired pipeline gives 2-3s.

---

### Success Metrics

| Metric | Current | V3.1 Target | V3.2 Target |
|--------|---------|-------------|-------------|
| TTFA (Time to First Audio) | 10-18s | 2-3s | 0.7-1s |
| STT payload size | 15.4s | 2.5s | N/A (Gemini Live handles) |
| Indian accent | Inconsistent | Consistent (Edge TTS) | Consistent (Gemini Live config) |
| Filler removal | Broken | Working | Working |
| Personality | Minimal | Full | Full |
| Cross-turn memory | None | 8-turn rolling | Full session (Gemini Live native) |
| Backend crash risk | High (dead imports) | Zero | Zero |
