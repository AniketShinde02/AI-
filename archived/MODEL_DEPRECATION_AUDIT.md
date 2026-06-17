# MODEL_DEPRECATION_AUDIT.md
## All Dead Model References, Deprecated APIs & Silent Failures

### 1. CONFIRMED DEAD: `llama3-8b-8192` (SpeechCleaner)
**File:** `d:\AI\backend\voice_agent\speech_cleaner.py`
**Line:** 10 — `self.model = "llama3-8b-8192"`
**Evidence (terminal log, verbatim):**
```
ERROR:nexus.speech_cleaner:❌ [SpeechCleaner] Failed: Error code: 400 - {'error':
{'message': 'The model `llama3-8b-8192` has been decommissioned and is no longer
supported. Please refer to https://console.groq.com/docs/deprecations...',
'type': 'invalid_request_error', 'code': 'model_decommissioned'}}
```
**Impact:** Every single user utterance is processed without filler removal. The SpeechCleaner silently passes raw text through on error, meaning the entire pipeline falls back to unclean input. 
**Replacement:** `llama-3.1-8b-instant` (confirmed live in `core/rag_oracle.py` Line 183)

---

### 2. LIVE: `llama-3.3-70b-versatile` (Main LLM)
**File:** `d:\AI\backend\voice_agent\providers\llm.py`
**Line:** 18 — `model: str = "llama-3.3-70b-versatile"`
**Status:** Currently active and working (confirmed by successful HTTP 200 logs).

---

### 3. LIVE: `llama-3.1-8b-instant` (RAG Oracle)
**File:** `d:\AI\backend\voice_agent\core\rag_oracle.py`
**Line:** 183 — `model="llama-3.1-8b-instant"`
**Status:** Live model. This is the exact replacement needed for the SpeechCleaner.

---

### 4. DEAD API: `getstream.video.rtc.PcmData` (Dead Import)
**File:** `d:\AI\backend\voice_agent\providers\tts.py`
**Line:** 5 — `from getstream.video.rtc import PcmData`
**File:** `d:\AI\backend\voice_agent\providers\tts_gemini.py`
**Line:** 7 — `from getstream.video.rtc import PcmData`
**Status:** The `getstream` package was uninstalled. These imports will cause ImportError at startup unless tts.py is still functioning (it might survive because `KokoroTTS` and `vision_agents.core.tts.tts` are referenced but not necessarily imported at module-load time due to lazy loading patterns).
**Risk:** HIGH. If these files are fully imported at startup, the backend will crash.

---

### 5. DEAD API: `vision_agents.core.tts.tts.TTS` (Dead Base Class)
**File:** `d:\AI\backend\voice_agent\providers\tts.py`
**Line:** 6 — `from vision_agents.core.tts.tts import TTS`
**File:** `d:\AI\backend\voice_agent\providers\tts_gemini.py`
**Line:** 9 — `from vision_agents.core.tts.tts import TTS`
**Status:** `vision_agents` is uninstalled. However, since `ws_main.py` imports `TTSProviderRouter` from `tts.py`, this WILL crash if the import chain executes fully.
**Note:** The backend is currently running, which means Python may be caching the old `.pyc` files from before uninstallation. After a clean server restart or `__pycache__` flush, this WILL fail.

---

### 6. DEAD IMPORT: `from kokoro_onnx import Kokoro` 
**File:** `d:\AI\backend\voice_agent\providers\tts.py`
**Line:** 10 — `from kokoro_onnx import Kokoro`
**Status:** `kokoro-onnx` was uninstalled. This import WILL fail on next clean restart.

---

### 7. DEAD FILE: `main.py` (Entire File is Dead)
**File:** `d:\AI\backend\voice_agent\main.py`
**Evidence:** 
- Line 9: `from vision_agents.core import Agent, AgentLauncher...` → uninstalled
- Line 10: `from vision_agents.plugins import getstream` → uninstalled
- Line 17: `from providers.tts import KokoroTTS` → Kokoro uninstalled
**Status:** `main.py` is the old Stream-WebRTC-based entry point. `ws_main.py` is the current active entry point. `main.py` is 100% dead and will crash on import.

---

### Silent Failure Risk Matrix
| Component | Status | Impact if Left |
|-----------|--------|----------------|
| `speech_cleaner.py llama3-8b-8192` | DEAD | No filler removal, raw LLM input forever |
| `tts.py getstream import` | DEAD (masked by cache) | Crash on next clean boot |
| `tts.py vision_agents import` | DEAD (masked by cache) | Crash on next clean boot |
| `tts.py kokoro_onnx import` | DEAD (masked by cache) | Crash on next clean boot |
| `main.py` (entire file) | DEAD | Do not import or execute |
