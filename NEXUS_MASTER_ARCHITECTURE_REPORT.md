# NEXUS DESKTOP AI OS — MASTER ARCHITECTURE REPORT
> Generated: 2026-06-17 | Sources: Live codebase audit + 52 web research sources
> Status: ARCHITECTURE AND ANALYSIS ONLY — NO CODE CHANGES

---

## TABLE OF CONTENTS

1. Product Reality
2. Full Codebase Review
3. Repository Inventory
4. Active Code Report
5. Dead Code Report
6. Duplication Report
7. Dependency Audit
8. Technical Debt Report
9. Documentation Cleanup Plan
10. Competitor Analysis (17 tools)
11. Data Storage Strategy
12. Memory Design
13. Session Design
14. Agent Design
15. Vector DB Recommendation
16. Scrapper OS Integration Design
17. Packaging Design
18. Risk Analysis
19. Cleanup Roadmap
20. Migration Roadmap

---

## 1. PRODUCT REALITY

Nexus is a **Desktop AI Operating System** distributed as a single executable (`Nexus.exe`).

### Core Constraints (Non-Negotiable)
- Each installation is **fully isolated**
- No central server, no shared memory, no shared database
- 500 users = 500 separate machines, not 500 concurrent connections
- Every user owns: API Keys, Chats, Memory, Knowledge Base, Agents, Files, Settings, Workflows
- Must be **offline-capable** for core features
- Must be **BYOK** (Bring Your Own Key) for all AI providers
- Must produce **one distributable EXE** via an installer

### What Nexus Is NOT
- NOT a SaaS
- NOT a cloud chatbot
- NOT a multi-tenant platform
- NOT a browser extension

---

## 2. FULL CODEBASE REVIEW

### Repository Root (`d:\AI\`)

Scanned via direct file analysis. Key findings:

```
d:\AI\
├── frontend/           Next.js 16.2 app (React 19 + Tailwind)
├── backend/
│   ├── voice_agent/    ACTIVE — Primary FastAPI backend (ws_main.py = 70KB god file)
│   │   ├── ws_main.py  — 70,576 bytes. Single entry point. Contains ALL routes.
│   │   ├── core/       — 10 Python files, mostly unimported by ws_main.py
│   │   ├── providers/  — STT, TTS providers (active)
│   │   ├── tools/      — Tool registry (active)
│   │   ├── experimental/ — 1 file (gemini_live_voice.py). NOT imported.
│   │   ├── archive_experiments/ — 1 file (main.py). GetStream experiment. DEAD.
│   │   └── venv/       — Python virtualenv (not to be committed)
│   └── src/backend/    — Separate backend (legacy, NOT used by current voice system)
├── Scrapper OS/        — Separate agent project. Standalone Python. Isolated.
├── hermes-agent/       — Full open-source AI CLI agent clone. NOT Nexus code.
├── windows_agent/      — Single subfolder (experiments/gemini_live). DEAD.
├── IRIS-AI-main/       — Competitor reference. NOT Nexus code.
├── Stonic-AI-Source-Code/ — Competitor reference. NOT Nexus code.
├── Nexus website/      — Separate marketing Next.js site. DEAD relative to current work.
├── experiments/        — 1 folder (gemini_live). DEAD.
├── NEXUS_BACKUPS/      — Stale backup. Review date.
└── docs/               — 21 markdown files (many obsolete — see Section 9)
```

### Backend Voice Agent — `ws_main.py` Architecture

`ws_main.py` is a **70KB god file** serving as:
1. FastAPI application entry point
2. WebSocket server (`/ws/nexus`, `/ws/gemini-live`)
3. STT pipeline orchestrator
4. VAD (Voice Activity Detection) controller
5. LLM routing logic (Groq → Gemini fallback)
6. TTS routing dispatcher
7. Memory extraction trigger
8. Tool registry + executor
9. OS automation endpoint host
10. Session manager

This is the **highest priority technical debt item** in the entire repository. Every other cleanup depends on eventually splitting this file.

### Frontend Architecture

```
frontend/src/
├── app/
│   ├── page.tsx           — Dashboard (23KB god component)
│   ├── agents/            — Static mock UI (no backend)
│   ├── automation/        — Static mock UI (no backend)
│   ├── chat/              — Partially wired
│   ├── memory/            — Partially wired
│   ├── trace/             — No data pipeline
│   ├── settings/          — Static
│   └── api/               — Multiple API routes (chat, groq, stream, trpc, suggestions)
├── components/
│   ├── ThreeOrb.tsx       — ACTIVE (3D orb on dashboard)
│   ├── NexusOrb.tsx       — DEAD (replaced by ThreeOrb.tsx)
│   ├── LightOrb.tsx       — DEAD (experimental orb)
│   ├── Header.tsx         — DEAD (replaced by TopNav.tsx)
│   ├── Sidebar.tsx        — DEAD (not used in layout.tsx)
│   ├── InputArea.tsx      — ACTIVE
│   ├── GeminiVision.tsx   — ACTIVE (camera/screen)
│   ├── SystemLogs.tsx     — ACTIVE
│   └── SystemTelemetry.tsx — ACTIVE
├── hooks/
│   ├── useNexusVoice.ts   — ACTIVE (21KB, primary WebSocket hook)
│   └── useHealthCheck.ts  — ACTIVE
└── lib/
    ├── firebase/          — WIRED (Firebase Admin for API routes)
    ├── trpc/              — WIRED (tRPC router, but minimal usage)
    └── stream.ts          — WIRED (GetStream, but experimental only)
```

---

## 3. REPOSITORY INVENTORY

| Folder | Purpose | Status | Used By | Dependencies |
|--------|---------|--------|---------|--------------|
| `backend/voice_agent/` | Primary voice AI backend | **ACTIVE** | Frontend WS | Groq, Gemini, EdgeTTS, silero-vad |
| `backend/voice_agent/core/` | Core utilities | **MIXED** | ws_main.py partially | See Dead Code section |
| `backend/voice_agent/providers/` | STT/TTS provider implementations | **ACTIVE** | ws_main.py | Groq, edge-tts, imageio-ffmpeg |
| `backend/voice_agent/tools/` | LLM tool definitions | **ACTIVE** | ws_main.py | pyautogui, psutil |
| `backend/voice_agent/experimental/` | Gemini Live experiments | **DEAD** | Nothing | — |
| `backend/voice_agent/archive_experiments/` | GetStream+Kokoro experiment | **DEAD** | Nothing | vision-agents, getstream |
| `backend/src/backend/` | Legacy backend (pre-refactor) | **DEAD** | Nothing | Firebase, Firestore |
| `frontend/src/` | Next.js UI | **ACTIVE** | User | React, Three.js, tRPC |
| `frontend/src/lib/stream.ts` | GetStream integration | **DEAD** | Nothing active | @stream-io/video-react-sdk |
| `frontend/src/lib/trpc/` | tRPC setup | **PARTIAL** | Some API routes | @trpc/* |
| `frontend/src/lib/firebase/` | Firebase Admin | **ACTIVE** | `/api/chat` route | firebase-admin |
| `Scrapper OS/` | Standalone scraping agents | **ISOLATED** | Nothing (separate project) | Playwright/Puppeteer |
| `hermes-agent/` | Hermes reference implementation | **REFERENCE ONLY** | Nothing | Complex (CLI framework) |
| `IRIS-AI-main/` | IRIS AI reference | **REFERENCE ONLY** | Nothing | — |
| `Stonic-AI-Source-Code/` | Stonic AI reference | **REFERENCE ONLY** | Nothing | — |
| `Nexus website/` | Marketing site | **DEAD** | Nothing | Next.js (separate) |
| `windows_agent/` | Windows automation experiment | **DEAD** | Nothing | — |
| `experiments/` | Gemini Live experiment | **DEAD** | Nothing | — |
| `NEXUS_BACKUPS/` | Frontend backup | **STALE** | Nothing | — |
| `docs/` | Documentation | **MIXED** | Humans only | — |

---

## 4. ACTIVE CODE REPORT

The following modules are confirmed to be in the **active execution path**:

### Backend (Confirmed Active)
| File | Role | Evidence |
|------|------|---------|
| `ws_main.py` | Entry point, all routes | Running in production terminal |
| `config.py` | Environment configuration | Imported by ws_main.py |
| `prompts.py` | System prompt builder | Imported by ws_main.py |
| `speech_cleaner.py` | Pre-LLM text cleaning | Imported by ws_main.py |
| `text_normalizer.py` | Post-LLM TTS normalization | Imported by ws_main.py |
| `pronunciation_dictionary.py` | TTS pronunciation fixes | Imported by ws_main.py |
| `providers/stt.py` | Groq Whisper STT | Imported + used in voice loop |
| `providers/tts.py` | TTS provider base + router | Imported + used |
| `providers/tts_edge.py` | Edge TTS implementation | Used as active TTS |
| `providers/tts_gemini.py` | Gemini TTS implementation | Used as primary TTS |
| `providers/llm.py` | Groq/Gemini LLM provider | Imported by ws_main.py |
| `core/gemini_live_manager.py` | Gemini Live session handler | Used via `/ws/gemini-live` |
| `core/memory_manager.py` | File-based memory R/W | Used for memory persistence |
| `core/rag_oracle.py` | RAG retrieval system | Initialized (empty) |
| `tools/__init__.py` | Tool registry | Imported by ws_main.py |
| `tools/file_tools.py` | File read/write tools | Registered in tool registry |
| `tools/memory_tools.py` | Memory update tools | Registered |
| `tools/system.py` | OS control tools | Registered |
| `tools/task_tools.py` | Task management tools | Registered |
| `tools/third_party_tools.py` | Weather + web tools | Registered |
| `greeting_cache.pkl` | Pre-cached greeting audio | Loaded on startup |

### Frontend (Confirmed Active)
| File | Role |
|------|------|
| `src/app/page.tsx` | Main dashboard |
| `src/app/layout.tsx` | Root layout |
| `src/hooks/useNexusVoice.ts` | Primary voice WebSocket hook |
| `src/hooks/useHealthCheck.ts` | Backend health polling |
| `src/components/ThreeOrb.tsx` | 3D orb animation |
| `src/components/InputArea.tsx` | Voice/text input |
| `src/components/GeminiVision.tsx` | Camera/screen share |
| `src/components/SystemLogs.tsx` | Live log display |
| `src/components/SystemTelemetry.tsx` | CPU/RAM metrics |
| `src/components/layout/TopNav.tsx` | Navigation bar |
| `src/lib/firebase/server.ts` | Firebase Admin (API chat) |

---

## 5. DEAD CODE REPORT

> Verified via import scanning. None of these files are imported by active execution paths.

### Backend Dead Code
| File | Reason | Action |
|------|--------|--------|
| `core/call_manager.py` | Uses `vision_agents.plugins.getstream` — experimental framework abandoned | **ARCHIVE** |
| `core/database.py` | Firebase/Firestore DB layer — no route in ws_main.py calls this | **ARCHIVE** |
| `core/usage.py` | Usage tracking stub — not called anywhere in ws_main.py | **ARCHIVE** |
| `core/registry.py` | Agent registry — not called anywhere in ws_main.py | **ARCHIVE** |
| `core/concurrency.py` | 640-byte concurrency util — not imported | **ARCHIVE** |
| `core/memory.py` | Duplicate memory file — `memory_manager.py` is the active one | **ARCHIVE** |
| `experimental/gemini_live_voice.py` | Standalone Gemini Live experiment — superseded by `gemini_live_manager.py` | **ARCHIVE** |
| `archive_experiments/main.py` | GetStream + Kokoro pipeline — obsolete architecture | **ARCHIVE** |
| `test_voice_suite.py` | Manual tests, not in CI | **KEEP** (manual use only) |
| `DEBUG_FORENSICS.txt` | Debug log file, no code | **DELETE** |

### Frontend Dead Code
| File | Reason | Action |
|------|--------|--------|
| `components/NexusOrb.tsx` | Replaced by `ThreeOrb.tsx` — not imported anywhere | **ARCHIVE** |
| `components/LightOrb.tsx` | Experimental orb — not imported anywhere | **ARCHIVE** |
| `components/Header.tsx` | Replaced by `layout/TopNav.tsx` | **ARCHIVE** |
| `components/Sidebar.tsx` | Not in `layout.tsx`, not in any page | **ARCHIVE** |
| `components/NexusStreamProvider.tsx` | GetStream provider — not used in layout | **ARCHIVE** |
| `lib/stream.ts` | GetStream connection — no active usage | **ARCHIVE** |
| `app/api/stream/` | GetStream token API — no active client consumption | **ARCHIVE** |
| `bones/` | Unknown stale folder | **INVESTIGATE then ARCHIVE** |
| `app/api-docs/page.tsx` | Static API documentation page — not linked | **KEEP** (informational) |

### Repository-Level Dead Folders
| Folder | Action |
|--------|--------|
| `Nexus website/` | **ARCHIVE** — separate old marketing site |
| `windows_agent/` | **ARCHIVE** — empty experiment |
| `experiments/` | **ARCHIVE** — single gemini_live folder |
| `NEXUS_BACKUPS/` | **DELETE** after verifying date |
| `backend/src/` | **ARCHIVE** — legacy backend, unused |

---

## 6. DUPLICATION REPORT

### Memory System Duplication ❌
| File | Type | Status |
|------|------|--------|
| `core/memory.py` | JSON memory system (3218 bytes) | DEAD |
| `core/memory_manager.py` | JSON memory system (1497 bytes) | **ACTIVE** |
| `tools/memory_tools.py` | Memory tools (wraps memory_manager) | **ACTIVE** |
| `backend/.nexus_states/user_memory.json` | Actual memory file | **ACTIVE** |

**Root Cause**: Two separate memory implementations co-exist. `memory.py` is likely an older version that was never removed when `memory_manager.py` was written.

### TTS System Duplication ⚠️
| File | Status |
|------|--------|
| `providers/tts.py` | Base class + router |
| `providers/tts_edge.py` | Edge TTS impl |
| `providers/tts_gemini.py` | Gemini TTS impl |

This is NOT duplication — it's the correct Provider pattern. No action needed.

### Orb Component Duplication ❌
| File | Status |
|------|--------|
| `components/NexusOrb.tsx` | DEAD |
| `components/LightOrb.tsx` | DEAD |
| `components/ThreeOrb.tsx` | **ACTIVE** |

Three orb implementations. Only one is used.

### Backend Duplication ❌
Two separate backend folders exist:
- `backend/voice_agent/` — **ACTIVE**
- `backend/src/backend/` — **DEAD** (legacy Firebase-based backend)

---

## 7. DEPENDENCY AUDIT

### Backend (`requirements.txt` + `venv`)

| Package | Used? | Where | Action |
|---------|-------|-------|--------|
| `fastapi` | ✅ YES | ws_main.py | **KEEP** |
| `uvicorn` | ✅ YES | ws_main.py | **KEEP** |
| `python-dotenv` | ✅ YES | config.py | **KEEP** |
| `groq` | ✅ YES | providers/stt.py, providers/llm.py | **KEEP** |
| `google-genai` | ✅ YES | gemini_live_manager.py, providers/llm.py | **KEEP** |
| `edge-tts` | ✅ YES | providers/tts_edge.py | **KEEP** |
| `silero-vad` | ✅ YES | ws_main.py (VAD) | **KEEP** |
| `imageio-ffmpeg` | ✅ YES | providers/tts_edge.py (PCM conversion) | **KEEP** |
| `numpy` | ✅ YES | Audio processing | **KEEP** |
| `pyautogui` | ✅ YES | tools/system.py | **KEEP** |
| `psutil` | ✅ YES | SystemTelemetry endpoint | **KEEP** |
| `python-multipart` | ✅ YES | FastAPI form data | **KEEP** |
| `pydantic-settings` | ✅ YES | config.py | **KEEP** |
| `httpx` | ✅ YES | Outbound API calls | **KEEP** |
| `soundfile` | ✅ YES | Audio file I/O | **KEEP** |
| `scipy` | ✅ YES | Audio resampling | **KEEP** |
| `getstream` | ❌ NO | Only `archive_experiments/main.py` | **REMOVE** |
| `vision-agents` | ❌ NO | Only `archive_experiments/main.py` | **REMOVE** |
| `vision-agents-plugins-getstream` | ❌ NO | Archive only | **REMOVE** |
| `elevenlabs` | ❌ NO | Not imported in any active file | **REMOVE** |
| `redis` | ❌ NO | Not imported in any active file | **REMOVE** |
| `aiortc` | ❌ NO | Old WebRTC experiment | **REMOVE** |
| `kokoro-onnx` | ❌ NO | Archive experiments only | **REMOVE** |
| `onnxruntime` | ⚠️ INDIRECT | Kokoro dependency. If Kokoro removed, review. | **REVIEW** |
| `deepgram-sdk` | ❌ NO | Not imported anywhere | **REMOVE** |
| `cartesia` | ❌ NO | Not in requirements.txt actually (remove from docs) | **REMOVE** |
| `firebase_admin` | ⚠️ PARTIAL | `core/database.py` (DEAD). Remove along with database.py | **REMOVE** |
| `firebase` (via venv) | ⚠️ PARTIAL | Only if database.py is removed | **REMOVE** |

**Estimated packages to remove: 9+ (getstream, vision-agents, elevenlabs, redis, aiortc, kokoro-onnx, deepgram-sdk, firebase_admin)**

### Frontend (`package.json`)

| Package | Used? | Where | Action |
|---------|-------|-------|--------|
| `next` | ✅ YES | Core framework | **KEEP** |
| `react` + `react-dom` | ✅ YES | All components | **KEEP** |
| `@react-three/fiber` + `drei` | ✅ YES | ThreeOrb.tsx | **KEEP** |
| `three` | ✅ YES | ThreeOrb.tsx | **KEEP** |
| `lucide-react` | ✅ YES | All pages | **KEEP** |
| `framer-motion` | ✅ YES | Animations | **KEEP** |
| `zod` | ✅ YES | Validation | **KEEP** |
| `tailwind-merge` + `clsx` | ✅ YES | Styling | **KEEP** |
| `@tanstack/react-query` | ✅ YES | via tRPC | **KEEP** |
| `@trpc/*` | ⚠️ PARTIAL | Only via `/api/trpc` route. No active client queries. | **EVALUATE** |
| `firebase` + `firebase-admin` | ⚠️ PARTIAL | `lib/firebase/server.ts` (used by `/api/chat`) | **KEEP IF CHAT ROUTE NEEDED** |
| `openai` | ⚠️ PARTIAL | `/api/chat/route.ts` (Groq via OpenAI compat) | **KEEP** |
| `@stream-io/node-sdk` | ❌ NO | Only stream token API (no active client) | **REMOVE** |
| `@stream-io/video-react-sdk` | ❌ NO | Only NexusStreamProvider.tsx (DEAD component) | **REMOVE** |
| `stream-chat` + `stream-chat-react` | ❌ NO | Not imported anywhere active | **REMOVE** |
| `gsap` | ⚠️ PARTIAL | Check if actually used in pages | **VERIFY** |
| `shadcn` | ⚠️ PARTIAL | UI primitives. Check usage. | **KEEP IF USED** |
| `boneyard-js` | ❌ UNKNOWN | Check `bones/` folder | **INVESTIGATE** |
| `@base-ui/react` | ⚠️ PARTIAL | Check if used in any component | **VERIFY** |
| `class-variance-authority` | ⚠️ PARTIAL | shadcn-style component variants | **KEEP IF USED** |
| `tw-animate-css` | ⚠️ PARTIAL | Tailwind animations | **KEEP IF USED** |
| `axios` | ⚠️ PARTIAL | Check if actually called over native fetch | **VERIFY** |

**Estimated frontend packages to remove: 4-6 (stream-chat, stream-chat-react, @stream-io/video-react-sdk, @stream-io/node-sdk)**

---

## 8. TECHNICAL DEBT REPORT

### 🔴 HIGH PRIORITY DEBT

| Debt | File | Complexity | Maintenance Cost | Risk |
|------|------|-----------|-----------------|------|
| `ws_main.py` is a 70KB god file | `ws_main.py` | HIGH | VERY HIGH | CRITICAL — every bug, every feature touches the same 1400-line file |
| `page.tsx` is a 23KB god component | `src/app/page.tsx` | HIGH | HIGH | MEDIUM — slow to modify, no component isolation |
| No authentication on any backend endpoint | All routes | MEDIUM | LOW | CRITICAL (security) — any process on the machine can call the AI |
| `user_memory.json` is a flat file used as a database | `memory_manager.py` | MEDIUM | MEDIUM | MEDIUM — no schema, no migration path, no concurrent write safety |
| Agents/Automation UI are 100% mock with no backend | Multiple pages | HIGH | HIGH | HIGH — feature gap disguised as working UI |
| RAG Oracle has no ingested data | `core/rag_oracle.py` | LOW | LOW | MEDIUM — Oracle initialized, embeddings empty |
| Two backend folders (`voice_agent/` + `src/backend/`) | Repo root | MEDIUM | HIGH | MEDIUM — confusion about which backend is live |

### 🟡 MEDIUM PRIORITY DEBT

| Debt | File | Risk |
|------|------|------|
| Dead packages in `requirements.txt` inflating install/startup time | `requirements.txt` | LOW |
| Dead frontend packages increasing bundle size | `package.json` | LOW |
| 5 dead core Python modules in `core/` | `core/` | MEDIUM — risk of future import confusion |
| 4 dead frontend components in `components/` | `components/` | LOW |
| No CI test pipeline (`test_voice_suite.py` exists but is manual only) | Root | MEDIUM |
| Gemini TTS rate-limited on free API tier | `providers/tts_gemini.py` | LOW |
| `greeting_cache.pkl` is a binary file in the repo | Root | LOW |

### 🔵 LOW PRIORITY DEBT

| Debt | Risk |
|------|------|
| Reference repositories (`hermes-agent/`, `IRIS-AI-main/`) bloating the repo | LOW |
| `backend/.nexus_states/` folder containing live data files | LOW |
| No `.gitignore` coverage for `__pycache__`, `.mypy_cache`, `venv/` | LOW |
| `DEBUG_FORENSICS.txt` checked into repo | VERY LOW |

---

## 9. DOCUMENTATION CLEANUP PLAN

### Current State: `docs/` has 21 files
After the session cleanup, this is the current docs inventory and recommended actions:

| File | Purpose | Status | Action |
|------|---------|--------|--------|
| `prd.md` | Product Requirements Doc | ACTIVE | **KEEP** |
| `architecture.md` | Base architecture | ACTIVE | **KEEP** |
| `Agentic_Architecture.md` | Agent system design | ACTIVE | **KEEP** |
| `feature_specs.md` | Feature specifications | ACTIVE | **KEEP** |
| `05_db_schema_data_model.md` | DB schema | ACTIVE | **KEEP** |
| `06_api_contract.md` | API contracts | ACTIVE | **KEEP** |
| `security_model.md` | Security design | ACTIVE | **KEEP** |
| `STABLE_ARCHITECTURE.md` | Architectural freeze doc | ACTIVE | **KEEP** |
| `SURVIVAL_GUIDE.md` | Dev onboarding | ACTIVE | **KEEP** |
| `memory_engine.md` | Memory subsystem spec | ACTIVE | **KEEP** |
| `deployment_runbook.md` | Deploy steps | REVIEW — overly complex for desktop | **REVIEW** |
| `ai_context.md` | AI prompt context | ACTIVE | **KEEP** |
| `async_task_queue.md` | 53KB queue architecture | OVERKILL for current state | **ARCHIVE** |
| `db_strucutre.md` | 71KB DB structure | May conflict with `05_db_schema` | **MERGE INTO `05_db_schema`** |
| `agent_trace_ui.md` | 41KB trace UI spec | UI spec, not architecture | **ARCHIVE** |
| `security_model.md` | 43KB security | Overkill for current local-only app | **SUMMARIZE + KEEP** |
| `03_repo_structure.md` | Repo structure | OUTDATED — mirrors no longer match | **UPDATE then KEEP** |
| `voice_stack_decision.md` | Voice stack choice | HISTORICAL | **ARCHIVE** |
| `prompt_engineering.md` | Prompt design | SMALL, useful | **KEEP** |
| `resources.md` | External links | KEEP for reference | **KEEP** |
| `CODE_REVIEW_MCP.md` | MCP review tool setup | Meta-doc | **KEEP** |
| `API.md` | 984 bytes — tiny API summary | Redundant with `06_api_contract.md` | **DELETE** |

### Recommended Final Docs Structure

```
docs/
├── architecture/
│   ├── overview.md         (merge: architecture.md + STABLE_ARCHITECTURE.md)
│   ├── memory.md           (keep: memory_engine.md)
│   ├── agents.md           (keep: Agentic_Architecture.md)
│   ├── storage.md          (NEW: data storage strategy from this report)
│   └── voice.md            (from: voice_stack_decision.md — archive rest)
├── development/
│   ├── setup.md            (NEW: setup guide for clean env)
│   ├── prd.md              (keep: prd.md)
│   ├── feature_specs.md    (keep)
│   ├── security.md         (summarize: security_model.md)
│   └── api.md              (merge: 06_api_contract.md + API.md)
├── database/
│   └── schema.md           (merge: 05_db_schema_data_model.md + db_strucutre.md)
└── archive/                (move everything else here)
```

---

## 10. COMPETITOR ANALYSIS

### Overview: 17 Tools Analyzed

---

### 1. AnythingLLM
- **Strengths**: Desktop-first, local-first, LanceDB by default, workspace isolation, zero-config
- **Weaknesses**: Limited voice, no real OS automation, single-user focus only in desktop mode
- **Architecture**: Electron + Node.js backend + LanceDB + pluggable LLM providers
- **Memory Strategy**: Workspace-scoped document memory via RAG; no personal preference memory
- **Agent Strategy**: Basic workflow agents, no persistent state between sessions
- **Storage Strategy**: LanceDB (vectors) + SQLite (chats/settings)
- **Lessons for Nexus**: ✅ Use LanceDB for vectors. ✅ Workspace isolation model. ⚠️ Nexus needs better long-term personal memory than AnythingLLM has.

### 2. Open WebUI
- **Strengths**: Python-first, Ollama-native, extensible pipelines, MCP support, active memory with tool calling
- **Weaknesses**: Heavy RAM for full stack, not meant for EXE packaging
- **Architecture**: FastAPI + Svelte frontend + SQLite + Chromadb/external vectors
- **Memory Strategy**: Active tool-based memory (save/search/update/delete) via model tool calling
- **Agent Strategy**: Model agents + MCP tool servers
- **Storage Strategy**: SQLite (chats) + ChromaDB or external VDB
- **Lessons for Nexus**: ✅ Active memory architecture (not passive). ✅ Tool-calling approach for memory CRUD. ✅ Model agent wrapping pattern.

### 3. LibreChat
- **Strengths**: Multi-provider unification, enterprise auth, agent chains, MCP support
- **Weaknesses**: Not desktop-first, cloud-heavy defaults, high complexity
- **Architecture**: Node.js/Express + MongoDB + React frontend
- **Memory Strategy**: Key-value memory injected by memory agent at conversation start
- **Lessons for Nexus**: ✅ Memory agent pattern at conversation start. ⚠️ MongoDB is wrong for Nexus — use SQLite instead.

### 4. Claude Desktop
- **Strengths**: MCP-first extensibility, local file access, project workspaces, polished UX
- **Weaknesses**: Cloud model dependency (no local LLM), proprietary
- **Architecture**: Electron + Anthropic API + local MCP servers
- **Memory Strategy**: Project workspaces + user-configurable MCP memory servers
- **Lessons for Nexus**: ✅ MCP tool interface for local tool access. ✅ Project scoping for memory isolation.

### 5. Cursor
- **Strengths**: BYOK, `.cursorrules` context persistence, agent-first in 2026, sandboxed agent execution
- **Weaknesses**: Not a general AI OS — it's a code editor. No voice. No personal memory globally.
- **Memory Strategy**: `.cursorrules` files + Memory Bank markdown files + optional MCP memory server
- **Lessons for Nexus**: ✅ BYOK model confirmed by the market. ✅ Explicit memory file pattern is adoptable.

### 6. ChatGPT Projects
- **Strengths**: Automated memory synthesis ("dreaming"), partitioned workspaces, zero-friction UX
- **Weaknesses**: Cloud-only, privacy concerns, no BYOK for memory
- **Memory Strategy**: Automated background synthesis of conversation history into structured dossier
- **Lessons for Nexus**: ✅ Background memory extraction (Nexus already does this). ✅ Memory management UI (show user what's stored).

### 7. Mem0
- **Strengths**: Dedicated persistent memory layer, cross-session recall, semantic deduplication
- **Weaknesses**: External dependency (cloud or self-hosted), adds latency
- **Architecture**: Vector DB + LLM extraction + structured entity memory
- **Lessons for Nexus**: ✅ Entity extraction rather than raw log storage. ✅ Semantic deduplication to prevent bloat.

### 8. Open Interpreter
- **Strengths**: Conversational OS control, privacy-first, offline capable, direct code execution
- **Weaknesses**: High risk (executes arbitrary code), limited multi-session memory
- **Architecture**: Python CLI + local LLM (Ollama) + direct subprocess execution
- **Lessons for Nexus**: ✅ Natural language → OS action model. ✅ Sandboxed execution with confirmation prompts.

### 9. OpenDevin (OpenHands)
- **Strengths**: Multi-step autonomous workflows, environment interaction, Docker sandboxing
- **Weaknesses**: Heavy (Docker required), not desktop-native
- **Lessons for Nexus**: ✅ Agent lifecycle management patterns. ✅ Execution sandboxing.

### 10. Continue.dev
- **Strengths**: BYOK IDE integration, supports local models via Ollama, codebase context
- **Weaknesses**: IDE extension, not general desktop OS
- **Lessons for Nexus**: ✅ Codebase RAG indexing patterns. ✅ Local embedding approach.

### 11. Flowise
- **Strengths**: Visual workflow builder, LangChain-native, node-based pipelines
- **Weaknesses**: Complex for non-technical users, cloud-focused default
- **Lessons for Nexus**: ✅ Visual automation pipeline UI inspiration for Automation page.

### 12. Langflow
- **Strengths**: React-Flow based visual editor, multi-agent workflows
- **Weaknesses**: Not desktop-first
- **Lessons for Nexus**: ✅ Visual graph for agent/workflow design.

### 13. CrewAI
- **Strengths**: Multi-agent coordination, role assignment, sequential task pipelines
- **Weaknesses**: Cloud API dependent, no personal memory
- **Lessons for Nexus**: ✅ Agent role definitions (Researcher, Executor, Planner). ✅ Sequential task delegation pattern.

### 14. AutoGen
- **Strengths**: Multi-agent conversations, code execution, human-in-the-loop
- **Weaknesses**: Complex setup, heavy dependencies
- **Lessons for Nexus**: ✅ Human-in-the-loop confirmation before risky actions.

### 15. IRIS AI
- **Strengths**: Voice-first, personality-driven, multi-modal (available in local repo)
- **Weaknesses**: Reference architecture — evaluate patterns
- **Lessons for Nexus**: ✅ Study voice pipeline patterns. ✅ Personality system design.

### 16. Hermes
- **Strengths**: CLI-first, production-grade skills system, plugin architecture, MCP integration (visible in local repo)
- **Architecture**: Python CLI + skills/ + plugins/ + MCP servers
- **Lessons for Nexus**: ✅ `skills/` folder pattern for modular agent capabilities. ✅ Plugin isolation design.

### 17. Stonic AI
- **Strengths**: Voice-first desktop agent (from local reference)
- **Lessons for Nexus**: ✅ Voice latency optimizations. ✅ TTS caching patterns.

---

## 11. DATA STORAGE STRATEGY

### The Right Storage Layer for Each Data Type

| Data Type | Storage | Reason |
|-----------|---------|--------|
| Active conversation context | **RAM only** | Ephemeral. Never persist raw token windows. |
| Agent execution state (running) | **RAM only** | Ephemeral. Clear on shutdown. |
| Conversations / Chat History | **SQLite (WAL mode)** | ACID, offline, portable, zero-config |
| Sessions / Workspaces | **SQLite (WAL mode)** | Structured, queryable |
| Agent Metadata / Registry | **SQLite (WAL mode)** | Structured, persistent |
| Memory (facts, preferences, goals) | **SQLite (WAL mode)** | Structured schema, conflict resolution |
| Workflow Definitions (Automation) | **SQLite (WAL mode)** | Persistent, structured |
| Settings / User Preferences | **JSON (config file)** | Flat config, human-readable |
| API Keys | **JSON (encrypted or OS keystore)** | Never in SQLite unencrypted |
| Knowledge Embeddings (RAG) | **LanceDB** | Embedded-first, no server needed |
| Document embeddings | **LanceDB** | Same as above |
| Local Files (PDFs, docs, images, audio) | **Local Filesystem** | Never modify originals |
| Export files / Backups | **JSON or ZIP** | Portable |
| Search result cache | **SQLite or RAM** | Temporary retrieval results |

### Critical Rules
1. **Do NOT use JSON as a database** — `user_memory.json` is the current violation. Migrate to SQLite.
2. **Do NOT store entire chat history in vector DB** — vectors are for knowledge, not conversations.
3. **Do NOT store API keys in SQLite in plaintext** — use OS keystore or encrypted JSON.
4. **SQLite in WAL mode** is the production-grade standard for local AI apps in 2026 (confirmed by AnythingLLM, Open WebUI, LibreChat architecture research).

---

## 12. MEMORY DESIGN

### Philosophy
Inspired by: ChatGPT (automated synthesis), Open WebUI (active tool-based memory), Mem0 (entity extraction + deduplication)

### Memory Schema (SQLite)

```
memories table:
- id           TEXT PRIMARY KEY (uuid)
- category     TEXT  (preference | fact | goal | project | person | habit)
- key          TEXT  (e.g., "preferred_language")
- value        TEXT  (e.g., "Hinglish")
- confidence   REAL  (0.0–1.0, extracted by LLM)
- source       TEXT  (session_id that generated it)
- created_at   TEXT  (ISO8601)
- updated_at   TEXT  (ISO8601)
- expires_at   TEXT  (NULL = permanent)
```

### Memory Extraction Process
1. After each conversation turn (background async task)
2. LLM (fast model, e.g., Llama 3.1 8B) scans the last N turns
3. Extracts: facts, preferences, goals, projects
4. Deduplicates against existing memories before inserting
5. Confidence score determines if memory overwrites or appends

### Memory Injection
At every LLM call:
1. Query SQLite: `SELECT key, value FROM memories WHERE category IN ('preference','fact','goal') ORDER BY updated_at DESC LIMIT 20`
2. Format as compact context block
3. Prepend to system prompt

### Memory Retention / Pruning
- Permanent: preferences, goals, identity facts
- Ephemeral: session context, search results (expire in 7 days)
- Size limit: 50 active memories per category max
- Pruning: remove lowest-confidence entries when limit exceeded

### Memory Conflict Resolution
- If `key` already exists: compare confidence scores
- Higher confidence → overwrite
- Equal confidence → append with timestamp note

---

## 13. SESSION DESIGN

### User Expectation
```
Close Nexus → Reopen Nexus → Continue exactly where they left off
```
(Comparable to browser tab restoration)

### Session Storage Schema (SQLite)

```
sessions table:
- id              TEXT PRIMARY KEY
- name            TEXT (auto or user-named)
- created_at      TEXT
- last_active     TEXT
- workspace_id    TEXT (FK → workspaces)
- active_agent_id TEXT (FK → agents)

messages table:
- id              TEXT PRIMARY KEY
- session_id      TEXT (FK)
- role            TEXT (user | assistant | tool)
- content         TEXT
- timestamp       TEXT
- tokens          INTEGER (optional)
- model           TEXT (which LLM responded)
```

### Restoration Workflow
1. On startup: load `last_active` session from SQLite
2. Restore last 20 messages as visible history
3. Rebuild conversation_history list in memory (last N turns for LLM context)
4. Restore agent state (active agent, active tools)
5. Resume exactly

### Chat Persistence
- Every message streamed from the LLM is persisted to SQLite **incrementally** (not at the end)
- If Nexus crashes mid-response, the partial response is recoverable

---

## 14. AGENT DESIGN

### Agent Registry Schema (SQLite)

```
agents table:
- id              TEXT PRIMARY KEY
- name            TEXT
- role            TEXT (researcher | executor | planner | companion)
- persona         TEXT (system prompt override)
- allowed_tools   JSON (list of tool_ids)
- created_at      TEXT
- is_active       BOOLEAN
- memory_scope    TEXT (shared | isolated)
```

### Execution Model
```
User Input
    ↓
Orchestrator (ws_main.py / future: orchestrator.py)
    ↓
Active Agent (resolve from registry)
    ↓
LLM Call (with agent persona + allowed tools injected)
    ↓
Tool Calls (if LLM requests tool execution)
    ↓
Tool Executor (validate tool against agent.allowed_tools)
    ↓
Response → TTS → User
```

### Permissions Model
Each agent has a declared `allowed_tools` list. The Tool Executor rejects calls to tools not in this list. This is the **security boundary** for agents.

### Agent Lifecycle
1. **Created**: User or system creates agent record in SQLite
2. **Active**: Agent is selected, persona injected into LLM context
3. **Executing**: Agent is processing a task (tool calls in flight)
4. **Idle**: Waiting for next turn
5. **Suspended**: Agent deactivated, state preserved in SQLite

### Failure Recovery
- Tool failures: log error, continue with next tool call or ask user
- LLM timeout: retry once, then fallback model
- Agent crash: reload from SQLite registry, resume from last message

---

## 15. VECTOR DB RECOMMENDATION

### ✅ RECOMMENDATION: LanceDB

**Rationale:**

| Criterion | LanceDB | ChromaDB | Qdrant |
|-----------|---------|----------|--------|
| Desktop suitability | ✅ Embedded-first (no server) | ✅ Embedded mode | ❌ Requires external process |
| Packaging (EXE) | ✅ Library, like SQLite | ✅ Library | ❌ Sidecar binary needed |
| RAM usage | ✅ Low (disk-based, lazy) | ✅ Low-Medium | ❌ Higher (server overhead) |
| Performance | ✅ High (Rust-based, Lance format) | ✅ Good | ✅ High |
| Zero-config | ✅ Yes | ✅ Yes | ❌ Needs configuration |
| Backup strategy | ✅ Single folder (copy = backup) | ✅ Single folder | ⚠️ More complex |
| Upgrade path | ✅ Python package update | ✅ Python package update | ❌ Binary upgrade needed |
| Production precedent | ✅ Used by AnythingLLM desktop | ✅ Used by many | ✅ Used in cloud |

**Conclusion**: LanceDB is the correct choice for Nexus. It runs entirely in-process (like SQLite for vectors), requires no server management, produces a simple folder structure that is trivially backed up, and has been proven by AnythingLLM for exactly this use case.

### Storage Path (Post-Migration)
```
%APPDATA%\Nexus\
├── nexus.db          (SQLite — chats, sessions, agents, memory, settings)
├── knowledge/
│   └── [lancedb_tables]/  (LanceDB — document + knowledge embeddings)
├── files/            (User's uploaded documents, originals untouched)
└── config.json       (API keys, user preferences — encrypted or OS keystore)
```

---

## 16. SCRAPPER OS INTEGRATION DESIGN

### Current State
```
d:\AI\Scrapper OS\AI-OS-3-scrapping-agents\
├── HR Finding Automation/
├── Internet Download Automation/
├── google-maps-scraper/
├── google-search-scraper/
└── job-scraper-test/
```

Scrapper OS is a **collection of standalone scraping agents** (not a unified service). No single API endpoint exists yet. Each scraper is a separate project.

### Recommended Architecture: Loose Bridge Pattern
```
Nexus Voice Backend
    ↓  (registers ScrapperOS tool)
Tool Registry (/execute-tool)
    ↓  (when user asks: "scrape Google Maps for restaurants")
ScrapperOS Bridge Service (localhost:8010)
    ↓  (HTTP API: POST /run-scraper)
ScrapperOS Runner (selects and executes correct scraper)
    ↓
Results → JSON
    ↓
Nexus Tool Response → LLM → User
```

### API Boundary Design
The Scrapper OS Bridge should expose:

```
POST /run-scraper
Body: { "scraper": "google-maps", "query": "restaurants in Pune", "limit": 20 }
Response: { "status": "ok", "results": [...], "count": 20 }

GET /health
GET /scrapers  (list available scrapers)
```

### Security Controls
- Bridge only accepts connections from `localhost`
- Nexus passes a local-only shared secret in headers
- Scraper processes are spawned as isolated subprocesses
- Results are size-limited (max 1MB per response)
- Nexus tool registry treats Scrapper OS as an **optional capability** — graceful failure if service not running

### Resource Requirements
- Bridge: 1 FastAPI process (port 8010), ~50MB RAM idle
- Each scraper spawn: 150-400MB RAM (Playwright/Chromium), short-lived

### Failure Handling
- If Bridge not running: tool returns `{"error": "ScrapperOS not available"}`
- If scraper timeout: Bridge kills subprocess, returns timeout error
- Nexus informs user with voice response: "Scrapper OS is not responding"

---

## 17. PACKAGING DESIGN

### Target
```
Nexus-Setup.exe  (Windows Installer, ~200-400MB)
```

### Recommended Packaging Stack: Tauri + PyInstaller Sidecar

**Why NOT Electron**: Electron bundles Chromium (adds 100MB+), Node.js overhead, bloated install.  
**Why Tauri**: Uses system WebView (no Chromium), tiny binary core, Rust backend, Python sidecar support.

### Component Packaging

| Component | Technology | Bundle Strategy |
|-----------|-----------|-----------------|
| Frontend UI | Next.js → static export | Export to `out/` folder, served by Tauri WebView |
| Backend | Python FastAPI → PyInstaller | `nexus-backend.exe` sidecar binary (pyinstaller --onefile) |
| SQLite DB | `nexus.db` | Created in `%APPDATA%\Nexus\` on first launch |
| LanceDB | Python library (in pyinstaller bundle) | No separate install needed |
| PyAutoGUI | Python library (in pyinstaller bundle) | No separate install needed |
| VAD Model | `silero_vad.onnx` | Bundle in pyinstaller assets |
| Greeting Cache | `greeting_cache.pkl` | Bundle in pyinstaller assets |

### Installer Strategy (NSIS or Inno Setup)
1. Install Nexus files to `%LOCALAPPDATA%\Nexus\`
2. Create `%APPDATA%\Nexus\` for user data (never overwritten on update)
3. Create Start Menu shortcut
4. Register as startup app (optional, user choice)

### Updater Strategy
1. Tauri has a built-in updater system (checks GitHub Releases or custom update server)
2. On update: replace Nexus binary and `nexus-backend.exe`
3. **Never** touch `%APPDATA%\Nexus\` (user data) during update
4. Run SQLite migrations on startup (`PRAGMA user_version` check)

### Local Storage Paths
```
%APPDATA%\Nexus\
├── nexus.db              ← Production database (never delete)
├── knowledge/            ← LanceDB vector store
├── files/                ← User documents
├── config.json           ← Encrypted settings + API keys
└── logs/                 ← Rolling log files

%LOCALAPPDATA%\Nexus\
├── nexus.exe             ← Tauri desktop app
├── nexus-backend.exe     ← PyInstaller Python backend
└── assets/               ← Bundled voice models, greeting cache
```

---

## 18. RISK ANALYSIS

### Architecture Risks

| Risk | Severity | Impact | Mitigation |
|------|---------|--------|-----------|
| `ws_main.py` god file creates deployment-blocking bugs | 🔴 HIGH | Every backend change is high-risk | Split into service modules ASAP |
| No auth on WebSocket means any local process can use Nexus AI | 🔴 HIGH | Security bypass | Add local shared-secret token auth |
| `user_memory.json` flat file can corrupt on concurrent writes | 🟡 MEDIUM | Memory loss | Migrate to SQLite |
| Firebase dependency in frontend API routes creates cloud coupling | 🟡 MEDIUM | Breaks offline use | Evaluate and remove if possible |
| GetStream + tRPC dependencies add 40MB+ to bundle with zero usage | 🟡 MEDIUM | Larger install, slower startup | Remove unused packages |

### Performance Risks

| Risk | Severity | Mitigation |
|------|---------|-----------|
| Three.js ThreeOrb renders every frame even when idle | 🟡 MEDIUM | Add visibility-based suspend |
| `useNexusVoice.ts` is 21KB and handles all WebSocket state | 🟡 MEDIUM | Split into smaller hooks |
| SQLite write blocking voice pipeline if not on WAL mode | 🟡 MEDIUM | Enable WAL on first run |
| VAD model loads on every server start (200ms+ latency) | 🟢 LOW | Already uses `lifespan` (one-time load) |

### Packaging Risks

| Risk | Severity | Mitigation |
|------|---------|-----------|
| PyInstaller bundle can fail for complex packages (torch, silero) | 🔴 HIGH | Test build pipeline early; use `--hidden-import` |
| Tauri requires Windows WebView2 (pre-installed on Win10+) | 🟢 LOW | Installer can include WebView2 bootstrapper |
| Python version mismatch in PyInstaller | 🟡 MEDIUM | Pin Python 3.11 in CI, freeze venv |

### Dependency Risks

| Risk | Severity | Mitigation |
|------|---------|-----------|
| `silero-vad` PyTorch dependency is 2GB+ install | 🔴 HIGH | Use ONNX version (already using onnxruntime) |
| Groq API rate limits block production usage | 🟡 MEDIUM | Implement exponential backoff + queue |
| Gemini API key expiry breaks ALL AI functionality | 🔴 HIGH | BYOK model — Nexus should never use its own keys |

---

## 19. CLEANUP ROADMAP

### Phase 1 — Repository Audit ✅ DONE
- [x] Full codebase scan
- [x] Import verification
- [x] Dependency audit
- [x] Dead code identification

### Phase 2 — Documentation Cleanup
- [ ] Archive `docs/async_task_queue.md`, `agent_trace_ui.md`, `voice_stack_decision.md`
- [ ] Merge `db_strucutre.md` into `05_db_schema_data_model.md`
- [ ] Delete `docs/API.md` (redundant with `06_api_contract.md`)
- [ ] Update `03_repo_structure.md` to reflect current actual structure
- [ ] Consolidate `architecture.md` + `STABLE_ARCHITECTURE.md` into single authoritative file

### Phase 3 — Dead Code Removal (No Risk)
- [ ] Delete `core/memory.py` (duplicate of `memory_manager.py`)
- [ ] Delete `DEBUG_FORENSICS.txt`
- [ ] Archive `core/call_manager.py`, `core/database.py`, `core/usage.py`, `core/registry.py`, `core/concurrency.py`
- [ ] Archive `experimental/gemini_live_voice.py`
- [ ] Archive `archive_experiments/main.py`
- [ ] Archive frontend: `NexusOrb.tsx`, `LightOrb.tsx`, `Header.tsx`, `Sidebar.tsx`, `NexusStreamProvider.tsx`
- [ ] Archive `lib/stream.ts`
- [ ] Archive `app/api/stream/`

### Phase 4 — Dependency Cleanup
Backend `requirements.txt`:
- [ ] Remove: `getstream`, `vision-agents`, `vision-agents-plugins-getstream`, `elevenlabs`, `redis`, `aiortc`, `kokoro-onnx`, `deepgram-sdk`
- [ ] Re-pin remaining packages to exact versions for PyInstaller stability

Frontend `package.json`:
- [ ] Remove: `@stream-io/node-sdk`, `@stream-io/video-react-sdk`, `stream-chat`, `stream-chat-react`
- [ ] Verify and possibly remove: `boneyard-js`, `@base-ui/react` (if unused)

### Phase 5 — Architecture Consolidation
- [ ] Move `backend/src/backend/` to archive
- [ ] Rename `backend/voice_agent/` → `backend/nexus_core/` (clearer intent)
- [ ] Add `.gitignore` entries: `venv/`, `__pycache__/`, `.mypy_cache/`, `*.pkl` (optionally)
- [ ] Create single `ARCHITECTURE_FREEZE.md` documenting locked decisions

### Phase 6 — Folder Structure Migration
- [ ] Migrate `user_memory.json` → SQLite `memories` table
- [ ] Create `%APPDATA%\Nexus\` directory structure on startup
- [ ] Move runtime data files out of repo (`*.pkl`, `.nexus_states/`)
- [ ] Add data path config to `config.py`

### Phase 7 — Architecture Freeze
- [ ] Document all final architectural decisions in `ARCHITECTURE_FREEZE.md`
- [ ] Establish protected modules (don't touch without review)
- [ ] Set up basic CI: `py_compile` check + frontend build check on every push

---

## 20. MIGRATION ROADMAP

### Current State
```
d:\AI\
├── frontend/           Next.js dev server (port 3939)
├── backend/voice_agent/ FastAPI + WebSocket (port 8001)
├── [17 other folders]  Mix of active, dead, and reference code
└── docs/               Fragmented documentation
```

### Target State
```
d:\AI\
├── nexus/
│   ├── frontend/       Next.js (static export for Tauri)
│   ├── backend/        Python FastAPI (modules, not god file)
│   │   ├── main.py     Entry point (thin orchestrator only)
│   │   ├── routes/     Route handlers (one file per domain)
│   │   ├── services/   Business logic (voice, memory, agents)
│   │   ├── providers/  STT, TTS, LLM providers
│   │   └── tools/      Tool registry
│   ├── data/           Local user data (gitignored)
│   │   ├── nexus.db
│   │   └── knowledge/
│   └── scripts/        Build, dev, packaging scripts
├── scrapper-os/        Bridge service (isolated)
└── docs/               Curated documentation only
```

### Migration Steps

**Step 1 (1–2 days): Cleanup (Phases 2–4)**
- Archive all dead code and documentation
- Remove unused packages
- Zero risk to current running system

**Step 2 (2–3 days): Memory Migration**
- Introduce SQLite `nexus.db` in `%APPDATA%\Nexus\`
- Write migration script: `user_memory.json` → `memories` table
- Add SQLite WAL mode on init
- Keep JSON fallback for 1 release cycle

**Step 3 (3–5 days): Chat History to SQLite**
- Add `sessions` and `messages` tables to SQLite
- Wire persistence to the WebSocket voice loop
- Frontend reads from SQLite via backend API

**Step 4 (5–7 days): ws_main.py Decomposition**
- Extract route handlers to `routes/voice.py`, `routes/tools.py`, `routes/memory.py`, etc.
- Extract business logic to `services/voice_pipeline.py`, `services/tts_orchestrator.py`
- Main `ws_main.py` becomes thin orchestrator (~200 lines)
- No behavior change — pure structural refactor

**Step 5 (Ongoing): Agents + Automation Backend**
- Add `agents` table to SQLite
- Wire agents page to real backend
- Add `workflows` table
- Wire automation page to real backend

**Step 6 (Future): Packaging**
- Configure Tauri with Python sidecar
- PyInstaller backend bundle
- NSIS installer
- Auto-updater setup

### Validation Steps (Each Migration Step)
1. `python -m py_compile` on all Python files
2. `pnpm build` on frontend (no TS errors)
3. Voice pipeline E2E test (speak → transcribe → respond → TTS plays)
4. Memory persistence test (write → restart → read back)

### Rollback Plan
- Every change goes in its own git commit
- Git tag before each major step: `v0.1-pre-sqlite`, `v0.2-pre-decompose`, etc.
- Rollback: `git revert` to tag

### Success Criteria
- [ ] Single `ws_main.py` reduced to < 300 lines
- [ ] All pages wired to real backend (no mock data)
- [ ] Memory in SQLite (not JSON)
- [ ] Zero dead files in active source directories
- [ ] Zero unused packages in `requirements.txt` and `package.json`
- [ ] `pnpm build` and `py_compile` pass clean in CI
- [ ] Frontend static export works (for Tauri packaging)
- [ ] Voice E2E test passes

---

## SUMMARY: DECISIONS FROZEN

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Vector Database | **LanceDB** | Embedded, no server, proven in AnythingLLM desktop |
| Structured Database | **SQLite (WAL mode)** | Standard for local-first AI, portable, offline |
| Desktop Packaging | **Tauri + PyInstaller sidecar** | Smallest bundle, native WebView, Rust core |
| Memory Architecture | **SQLite extraction + LLM summarization** | Inspired by ChatGPT + Mem0 |
| Agent Design | **Registry-based with allowed_tools** | Lightweight permission boundary |
| Scrapper OS | **Bridge service (localhost:8010)** | Loose coupling, independent lifecycle |
| Memory File | **Migrate from JSON → SQLite** | Concurrent safety, structured queries |
| Auth | **Local shared-secret token** | Minimum viable auth for desktop isolation |
| BYOK | **Yes — mandatory** | Desktop-first, privacy-first |
| Session Restoration | **SQLite sessions table** | Like browser tab restoration |

---

*End of Report. No code changes permitted until user review.*
