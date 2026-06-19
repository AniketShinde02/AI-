# NEXUS MASTER BRAIN

This document serves as the absolute source-of-truth for the Nexus AI architecture, environment configurations, external integrations, and future roadmaps. It is strictly based on the actual repository state and code implementations as of June 2026.

---

## 1. CURRENT ARCHITECTURE

### Voice Pipeline (`core/voice_session.py`, `core/gemini_live_manager.py`)
- **Mode A (Gemini Live)**: Bidirectional native WebRTC/WebSocket streaming directly to `gemini-2.5-flash-native-audio-latest`. Handles ultra-low latency voice.
- **Mode B (Fallback/Groq)**: VAD (Voice Activity Detection with 8-frame preroll) → STT (Groq `whisper-large-v3` or Gemini fallback) → Local Action Router → LLM (Groq `llama-3.3-70b-versatile`) → TTS (Edge-TTS `hi-IN-MadhurNeural` -> FFmpeg PCM conversion).
- **Enforcement**: All audio is processed locally first via `session.process_audio()` before routing to prevent duplicate execution loops.

### Chat Pipeline (`core/voice_session.py`)
- **Text Injection**: Text intents route directly into `run_llm_and_tts()`.
- **Output Scrubbing**: `core/output_processor.py` intercepts all LLM streams and regex-strips conversational friction (e.g., `<think>`, "I'm thinking", "As an AI") to ensure clean Trace logs and fast TTS execution.

### Tool Execution Pipeline (`core/action_router.py`, `tools/system.py`)
- **Intent Ownership**: The Action Router explicitly owns Action intents. If a keyword match (e.g., "open ", "close ") is triggered, it intercepts the prompt, executes the tool, and *bypasses the LLM entirely* for that turn.
- **Contract Schema**: All tools (`pc_open_app`, `pc_take_screenshot`) strictly return a 5-key deterministic dictionary (`success`, `tool`, `target`, `verification`, `execution_time`).

### Memory Pipeline (`core/lance_memory.py`, `core/database.py`)
- **Persistence**: SQLite database (`nexus.db`) synchronously stores conversation history via `db.save_message()`.
- **Semantic Archival**: Background task `extract_and_save_memory` uses `llama-3.1-8b` to summarize turns and embed them into LanceDB vector storage for persistent agent recall.

### Model Routing Pipeline (`core/model_router.py`)
- **Resilience**: Configured with a dynamic fallback cascade (`LLM_FALLBACK_PROVIDERS=["cerebras","gemini","deepseek","openrouter"]`).
- **Targeting**: Groq is utilized for fast text/tooling, Gemini for Vision and Live Voice, and Mistral/DeepSeek available via dynamic API client configuration.

### Browser Pipeline (`core/browser_agent.py`)
- **Execution**: Uses Microsoft Playwright. Handles `open_url`, `search`, `click`, `extract`, and `screenshot` entirely headless or visible depending on the capability request.

### PC Control Pipeline (`core/pc_control.py`, `core/app_discovery.py`)
- **Discovery**: Background crawler scans Start Menu for `.lnk` shortcuts, filtering out junk (`uninstall`, `help`) and mapping absolute paths to SQLite.
- **Execution**: Uses RapidFuzz (`token_set_ratio > 60`) to map voice intents to discovered apps. Executes via `os.startfile()`.
- **Verification**: Actively polls `psutil` asynchronously to mathematically verify process creation.
- **UI Sync**: Employs a 1.5s artificial wait post-verification to ensure TTS confirmation syncs with desktop visual rendering. Handles graceful `WM_CLOSE` and `minimize/maximize` via `pygetwindow`.

---

## 2. IMPLEMENTED FEATURES

*   **Dynamic Application Discovery**: Automatic scanning and indexing of Windows software into SQLite.
*   **RapidFuzz Voice-to-App Matching**: Intelligent algorithmic application resolution ignoring Hinglish slang.
*   **Dual-Engine Voice Transport**: Seamless fallback between Gemini Live API and Groq+EdgeTTS.
*   **Process Verification Loop**: Mathematical OS verification before confirming app launches.
*   **Graceful Window Management**: `pygetwindow` integration for WM_CLOSE, minimize, and maximize.
*   **Reasoning Filter**: Real-time streaming output processor that strips LLaMA 3.3 `<think>` tags and conversational prefixes.
*   **LanceDB Vector Memory**: Autonomous background extraction and semantic embedding of conversations.
*   **Dynamic Theme Engine**: Gemini Vision API dynamically extracting HEX palettes from uploaded desktop wallpapers.
*   **Hardware Telemetry**: Real-time CPU, RAM, and disk reading via `psutil`.

---

## 3. PARTIALLY IMPLEMENTED FEATURES

*   **Scrapper OS Bridge**: The API proxy routes (`/api/scrapper-os/*`) are built in `ws_main.py`, but deeply nested cross-agent task delegation is pending frontend mission UI wiring.
*   **Agent Swarm Registry**: The SQLite `agents` table and CRUD endpoints exist, but multi-agent crew execution loops are not dynamically spinning up processes yet.
*   **Browser Control**: Playwright `browser_agent.py` functions are built but rely on basic CSS selector strings; they lack a self-healing DOM-parsing model like modern Browser-Use agents.

---

## 4. PLANNED FEATURES

*   **Tavily AI / Web Research**: Deep, orchestrated background web research.
*   **Wake Word Engine**: Always-on listening via Porcupine.
*   **Rasa NLU Parsing**: Local, offline intent parsing bypassing LLM latency.
*   **Native Screen Share Processing**: Sending real-time 1FPS WebRTC canvas frames to Gemini Multimodal for constant screen context.

---

## 5. ENVIRONMENT AUDIT

An inspection of `d:\AI\backend\.env` and `d:\AI\frontend\.env`.

| Variable | Used? | Location | Purpose | Missing/Issue? |
| :--- | :--- | :--- | :--- | :--- |
| `GROQ_API_KEY` | Yes | Both | Primary Fast LLM | Duplicated in Frontend |
| `GEMINI_API_KEY` | Yes | Both | Live Voice / Vision | Exposed as `NEXT_PUBLIC_` in Frontend |
| `LLM_FALLBACK_PROVIDERS` | Yes | Both | Fault Tolerance | - |
| `THEME` / `NEON_COLOR` | Yes | Both | UI Styling | - |
| `TAVILY_API_KEY` | No | Both | Web Search | Dead Key / Coming Soon |
| `NEWSAPI_KEY` | No | Both | News Aggregation | Dead Key / Coming Soon |
| `DEEPGRAM_API_KEY` | No | Both | Fast STT | Dead Key / Coming Soon |
| `CAMB_AI_KEY` | No | Both | Indian TTS | Dead Key / Coming Soon |
| `ELEVENLABS_API_KEY`| No | Both | Premium TTS | Dead Key / Coming Soon |
| `CARTESIA_API_KEY` | No | Both | Realtime Voice | Dead Key / Coming Soon |
| `HUGGINGFACE_API_KEY`| No | Both | OS Models | Dead Key / Coming Soon |
| `FIREBASE_CREDENTIALS`| No | Both | Legacy Auth? | **Critical Security Leak** in `.env` |

**Audit Findings**:
1. **Critical Leak**: `FIREBASE_CREDENTIALS` is fully exposed as a raw JSON string containing a private key in the frontend `.env`.
2. **Duplication**: The frontend `.env` contains the entire backend API key suite. Next.js only exposes `NEXT_PUBLIC_` to the browser, but storing raw backend service keys in a React frontend directory is a bad security practice.
3. **Dead Keys**: Half of the `.env` file consists of API keys for services that are not implemented in the codebase (Tavily, NewsAPI, Deepgram, CambAI, ElevenLabs, Cartesia, HuggingFace).

---

## 6. API RATE LIMITS & PROVIDER CONSTRAINTS

To maintain uninterrupted voice operation, Nexus must gracefully navigate strict rate limits. The following constraints dictate our fallback strategies:

### Inference Engines (LLMs)
*   **Groq (Primary Fast Engine)**: 30 RPM / 14,400 RPD / ~6,000 TPM on Free Tier. Developer Tier removes bottlenecks for production.
*   **Cerebras (Fast OSS Engine)**: 1,000 RPM / 1,440,000 RPD / 1M TPM for `gpt-oss-120b`. Massive limits but fewer supported models.
*   **Gemini (Vision/Live Voice)**: 15 RPM / 1,500 RPD for Flash 1.5. *Critical Bottleneck*: 15 RPM is easily exhausted in active voice conversations.
*   **DeepSeek (Top Reasoning)**: Dynamic rate limiting based on load (typically 10-30 RPM). Returns 429 during high traffic.
*   **Mistral API**: Strict 1 RPS (Requests Per Second) global limit on Free Tier.
*   **SambaNova**: 240 RPM / 48,000 RPD on Developer Tier (Llama 3.3 70B). 200,000 TPD on Free Tier.
*   **OpenRouter**: 20 RPM / 50 RPD on Standard Free Tier. Scaled to 1,000 RPD with lifetime credits >$10.

### Voice & Audio Services
*   **ElevenLabs (Premium TTS)**: 10,000 characters per month on Free Tier. Extremely strict concurrency limits.
*   **Cartesia (Realtime Voice)**: 20,000 model credits/month. Concurrency limited to 2 simultaneous TTS streams, 8 STT streams.
*   **Deepgram (Fast STT)**: No permanent free tier ($200 initial credits). Concurrency limited to 1 stream on lower tiers.

### Rate Limit Evasion Strategy (Implemented)
Nexus prevents 429 catastrophic failures via **Immediate Async Failover**. If Groq exhausts its 30 RPM, `voice_session.py` instantly catches the 429 exception and cascades to Cerebras or Gemini. For TTS, if Gemini exhausts its 15 RPM, it falls back to unmetered **Edge TTS**.

---

## 7. FREE SERVICES AUDIT

Research and recommendations for scaling Nexus without API costs.

### No API Key Needed
*   **DuckDuckGo Search** (`duckduckgo-search`): Already used in `third_party_tools.py`. Excellent for fast, free keyword searches.
*   **Nominatim Geolocation**: Free OSM geocoding for local weather/location resolution.
*   **Public Weather (Open-Meteo)**: Requires no API key, provides highly accurate hourly forecasting natively.
*   **RSS Sources / GDELT**: Free parsing of global news streams.
*   **Edge-TTS**: Microsoft's free Neural TTS. Already integrated natively in `tts_edge.py`.

### API Key Required (With Generous Free Tiers)
*   **Browser Automation (Browserbase / ScrapperOS)**: For bypassing Cloudflare bot-protection.
*   **Vision / Multimodal (Gemini Flash)**: 15 RPM free tier, sufficient for local desktop vision.
*   **Fast LLM (Groq)**: Generous daily token limits for `llama-3.3-70b-versatile`. Already primary.
*   **Reranking (Cohere)**: 1,000 free API calls/month. Excellent for LanceDB RAG sorting.
*   **Embeddings (Google AI Studio)**: Free `text-embedding-004` usage.

---

## 8. MULTI-MODEL BRAIN DESIGN

To permanently eliminate model-specific hacks (e.g., Gemini string parsing, Groq custom tool schemas), Nexus must adopt a **Provider-Agnostic Core**:

1. **Standardized Tool Registry**: A singular `capabilities.py` that outputs tools strictly in the **OpenAI JSON Schema standard**. All providers (Mistral, Gemini, Groq) natively accept this standard.
2. **Unified Action Interception**: Continue using `core/action_router.py` to catch voice intents *before* they reach the model. This guarantees that whether Nexus uses Cerebras or DeepSeek tomorrow, "open chrome" executes locally in 0ms.
3. **Universal Message Bus**: A single `messages` table in SQLite. When switching from Groq to Gemini, the backend normalizes the `system`, `user`, and `assistant` dictionary mappings to match the target provider's SDK requirements on the fly.
4. **Decoupled System Prompting**: `prompts.py` must never contain "Do not use `<think>` tags" because Gemini doesn't use them, but DeepSeek R1 does. Prompts should be injected based on the `engine_mode` variable dynamically.

---

## 9. EXTERNAL RESEARCH COMPARISON

Analysis of related agent architectures:

*   **Stonic AI**: Uses a tight React/Electron bridge for instant PC control. *Nexus equivalent*: `pc_control.py` via FastAPI websocket is faster and avoids Electron overhead.
*   **IRIS AI**: Pioneers the Bidirectional WebSocket Voice pipeline. *Nexus equivalent*: `gemini_live_manager.py` successfully replicated this sub-second TTFA transport.
*   **Hermes Agent**: Relies heavily on long-running state machines and complex LangGraph execution loops. *Nexus equivalent*: Nexus is built for "Daily Needs" (fast, instant tool execution) and avoids complex graph loops for simple tasks.
*   **Open Interpreter / Computer Use**: Rely on taking a screenshot, letting a Vision model determine X/Y coordinates, and clicking. *Nexus equivalent*: Nexus uses absolute OS paths (`os.startfile`) and API-level window handles (`pygetwindow`), which is infinitely faster, cheaper, and more reliable than visual coordinate guessing.

---

## 10. FINAL RECOMMENDATIONS

**HIGH IMPACT**
1. **Frontend Security Purge**: Delete the backend service keys (Groq, Cerebras, DeepSeek, Firebase) from `frontend/.env`. They do not belong there and pose an immediate security risk.
2. **Playwright Auto-Healing**: Upgrade `browser_agent.py` to use an accessibility-tree (AOM) parser rather than raw CSS selectors, allowing the agent to robustly click elements on dynamic React/Next.js websites.

**MEDIUM IMPACT**
3. **Tavily / Perplexity Integration**: Wire up the dead `TAVILY_API_KEY` to provide deep web research capabilities when local RAG fails.
4. **Porcupine Wake Word**: Implement the offline wake-word engine to allow hands-free triggering of the WebSocket pipeline.

**LOW IMPACT**
5. **Delete Dead Dependencies**: Remove remaining test scripts and unused provider integrations (e.g., Cartesia, ElevenLabs) to reduce container size and boot time.
