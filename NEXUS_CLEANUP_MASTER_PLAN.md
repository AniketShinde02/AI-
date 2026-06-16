# NEXUS_CLEANUP_MASTER_PLAN.md
## Final Delete / Archive / Keep / Rewrite List

### SAFE DELETE (Remove Immediately, No Impact)
| File | Reason |
|------|--------|
| `voice_agent/test_edge_tts.py` | Experimental test script |
| `voice_agent/test_gemini_tts.py` | Experimental test script |
| `voice_agent/test_groq.py` | Experimental test script |
| `voice_agent/test_isolation.py` | Experimental test script |
| `voice_agent/test_tts.py` | Experimental test script |
| `voice_agent/test_edge_output.raw` | Raw binary output of test |
| `voice_agent/test_gemini_output.raw` | Raw binary output of test |
| `voice_agent/debug_json.py` | Debug utility |
| `voice_agent/debug_json_v2.py` | Debug utility |
| `voice_agent/list_routes.py` | Debug utility |
| `voice_agent/agent_err.txt` | Log artifact |
| `voice_agent/agent_log.txt` | Log artifact |
| `voice_agent/linter_errors.txt` | IDE artifact |
| `voice_agent/mypy_results.txt` | IDE artifact |
| `voice_agent/backend_forensics.log` | Log artifact (regenerated on run) |
| `voice_agent/DEBUG_FORENSICS.txt` | Log artifact |
| `voice_agent/scratch/` (entire folder) | Scratch notes |

---

### SAFE ARCHIVE (Move to `archive_experiments/`, Not Delete)
| File | Reason |
|------|--------|
| `voice_agent/main.py` | Old Stream WebRTC entry point. Dead but has reference value. |
| `voice_agent/experimental/gemini_live_voice.py` | Will be promoted to production in V3 — move from `experimental/` to `providers/` after hardening |
| `voice_agent/memory_manager.py` | Stub for future memory. Keep but move to `core/` |

---

### KEEP (Active Production Code — Do Not Touch)
| File | Reason |
|------|--------|
| `voice_agent/ws_main.py` | Active production WebSocket server (needs fixes not deletion) |
| `voice_agent/config.py` | Environment config loader |
| `voice_agent/providers/stt.py` | Groq STT client wrapper |
| `voice_agent/providers/llm.py` | Groq LLM wrapper |
| `voice_agent/providers/tts_edge.py` | Edge TTS (Indian accent fallback → promote to primary) |
| `voice_agent/speech_cleaner.py` | Correct design, just wrong model name |
| `voice_agent/text_normalizer.py` | Useful text pipeline |
| `voice_agent/core/` (entire folder) | Memory, RAG Oracle, usage tracking |
| `voice_agent/tools/` (entire folder) | Tool implementations |
| `voice_agent/prompts.py` | Rich personality — MUST be wired into ws_main.py |
| `voice_agent/requirements.txt` | Now trimmed correctly |

---

### REWRITE (Code is Correct in Intent, but Must Change)
| File | What Must Change |
|------|-----------------|
| `voice_agent/ws_main.py` | Fix preroll buffer, wire prompts.py, add conversation history, remove inline prompt |
| `voice_agent/providers/tts.py` | Remove dead imports (`getstream`, `vision_agents`, `kokoro_onnx`), swap provider order to Edge TTS first |
| `voice_agent/providers/tts_gemini.py` | Remove dead imports (`getstream`, `vision_agents`), keep as fallback only |
| `voice_agent/providers/tts_edge.py` | Remove dead imports (`getstream`, `vision_agents`), add Hindi/Marathi language detection for voice switching |
| `voice_agent/speech_cleaner.py` | Change model from `llama3-8b-8192` to `llama-3.1-8b-instant` |

---

### Dead Import Emergency List (Will Crash on Clean Restart)
These files import packages that were uninstalled during Phase 2:
- `providers/tts.py`: `from getstream.video.rtc import PcmData`, `from vision_agents.core.tts.tts import TTS`, `from kokoro_onnx import Kokoro`
- `providers/tts_gemini.py`: `from getstream.video.rtc import PcmData`, `from vision_agents.core.tts.tts import TTS`
- `providers/tts_edge.py`: `from getstream.video.rtc import PcmData`, `from vision_agents.core.tts.tts import TTS`

**These must be fixed before the next server restart or the entire backend crashes.**
