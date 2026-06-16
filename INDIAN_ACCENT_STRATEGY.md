# INDIAN_ACCENT_STRATEGY.md
## Enforcing Indian English Accent — Evidence-Based Analysis

### Current State (Evidence)
**File:** `d:\AI\backend\voice_agent\providers\tts_gemini.py`
**Lines 49-56 (Voice Mapping):**
```python
voice_map = {
    "sarah":             "Aoede",           # ← US/Neutral accent
    "nexus_male":        "Puck",            # ← US/Neutral accent
    "professional_male": "Fenrir",          # ← US/Neutral accent
    "casual_female":     "Kore"             # ← US/Neutral accent
}
```
**Finding:** ALL four Gemini voices are American/Neutral English. There is NO Indian English Gemini voice currently. Gemini TTS does not support regional accent selection as of June 2026.

**File:** `d:\AI\backend\voice_agent\providers\tts_edge.py`
**Lines 35-42 (Voice Mapping):**
```python
voice_map = {
    "sarah":             "en-US-JennyNeural",   # ← US accent
    "nexus_male":        "en-IN-PrabhatNeural", # ← Indian English ✅
    "professional_male": "en-US-GuyNeural",     # ← US accent
    "casual_female":     "en-IN-NeerjaNeural"   # ← Indian English ✅
}
```
**Finding:** Edge TTS has `en-IN-PrabhatNeural` and `en-IN-NeerjaNeural` — both are high-quality Indian English Microsoft Neural voices. These are the only voices currently available in Nexus with a consistent Indian accent.

---

### Why the Accent Changes
The system currently prioritizes Gemini TTS (US/Neutral accent) and only falls back to Edge TTS on failure. Since Gemini TTS almost always succeeds, the user hears US/Neutral accent by default.

**Accent source per turn (based on provider selection log):**
```
INFO:nexus.tts.router:[TTS] Provider Selected: gemini  ← Always first
```
Edge TTS (`en-IN`) is almost never reached because Gemini succeeds.

---

### Can We Enforce Indian English Regardless of Source Language?
**Yes.** The accent is determined by the TTS voice, not by the STT language or LLM response language. The LLM can respond in English, Hindi, Marathi, or Hinglish — the TTS voice renders it in the selected accent.

**Strategy:**
1. **Switch primary TTS from Gemini (US/Neutral) to Edge TTS (en-IN)** — This immediately gives consistent Indian English accent.
2. **Gemini TTS limitation is permanent** — Gemini does not offer `en-IN` or regional accents in the TTS API.
3. **For Hindi/Marathi language replies**: Edge TTS also has `hi-IN-MadhurNeural` (Hindi male) and `mr-IN-AarohiNeural` (Marathi female) — these can be used when the LLM responds in Hindi or Marathi, while maintaining Indian phonology throughout.

---

### Edge TTS Indian Voice Inventory (Available)
| Voice | Locale | Gender | Use Case |
|-------|--------|--------|----------|
| `en-IN-PrabhatNeural` | Indian English | Male | Nexus default male voice |
| `en-IN-NeerjaNeural` | Indian English | Female | Sarah/female voice |
| `hi-IN-MadhurNeural` | Hindi | Male | Hindi responses |
| `hi-IN-SwaraNeural` | Hindi | Female | Hindi female responses |
| `mr-IN-AarohiNeural` | Marathi | Female | Marathi responses |
| `mr-IN-ManoharNeural` | Marathi | Male | Marathi male responses |

---

### Recommended Strategy
1. **Set Edge TTS as the primary provider** in `providers/tts.py` (swap `base_chain` order from `["gemini", "edge"]` to `["edge", "gemini"]`).
2. **Keep Gemini TTS as fallback** only.
3. **Add language-based voice routing** in `tts_edge.py`: detect if LLM response contains Hindi/Marathi characters and switch to the appropriate voice automatically.
4. **Gemini Live (V3)**: When Gemini Live becomes primary, the voice accent is controlled by the `speech_config` in the Live session — a separate Hindi/Marathi prompt can enforce Indian phonetics.
