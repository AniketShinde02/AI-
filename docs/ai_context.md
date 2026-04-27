# 12 – AI Context File

> Single source of truth for how AI tools (Cursor, Perplexity, Claude, etc.) should write code for this project.
>
> This file **overrides AI defaults**. If an AI conflicts with this file, this file wins.

---

## 1. Project identity

- Project type: **Voice-first, login-enabled AI assistant** with browser automation + Windows PC control.
- Runtime model: **Cloud-backed modular monolith backend** + **local Windows agent** + **browser automation**.
- Platforms:
  - Backend: Python.
  - Local agent: Python (Windows only for now).
  - UI: React/Next.js web app (later wrapped in Tauri for Windows).
- Core external tools:
  - **Stream Video + Vision Agents** for realtime voice.
  - **Browser Use** for web automation.[web:43][web:275]
  - **pywinauto** for Windows app control.[web:52][web:279][web:283]

AI assistants must not casually change these fundamentals.

---

## 2. High-level architecture (for AI)

### 2.1 Layers

- `frontend/` – Next.js app (TypeScript), voice & chat UI.
- `backend/` – Python modular monolith:
  - `api/` – HTTP/WebSocket endpoints.
  - `core/` – orchestration, voice, tools, tasks, memory.
  - `services/` – integration wrappers (Stream, Vision Agents, LLMs, Browser Use, DB, etc.).
  - `models/` – Pydantic models / ORM models.
- `windows_agent/` – Python Windows companion process for PC control.
- `docs/` – PRD, architecture, feature specs, etc.

### 2.2 Key modules AI should know

Backend `core/` modules (Python):

- `core/conversation.py` – Conversation orchestrator.
- `core/voice.py` – Voice session logic (hooks into Stream Video + Vision Agents service).
- `core/tools.py` – Tool router (`browser_task`, `windows_task`, `research_task`, etc.).
- `core/tasks.py` – Task lifecycle (create, update, log).
- `core/memory.py` – Memory API (user/session/task memory stubs).
- `core/outputs.py` – Markdown output generation (reports, logs).

Backend `services/` modules (Python):

- `services/stream_client.py` – Calls to Stream Video backend.
- `services/vision_agents_client.py` – Vision Agents integration.
- `services/llm_router.py` – LLM selection per use case (fast vs strong model).[web:266][web:269]
- `services/tts_client.py` – TTS provider calls.
- `services/browser_use_client.py` – Browser Use integration.[web:43][web:275]
- `services/windows_agent_client.py` – HTTP/WebSocket client to local Windows agent.
- `services/db.py` – DB session helpers.

Windows agent modules (Python):

- `windows_agent/server.py` – HTTP/WS server.
- `windows_agent/handlers/apps.py` – app launch/focus.
- `windows_agent/handlers/files.py` – file/folder ops.
- `windows_agent/handlers/input.py` – keyboard/mouse.
- `windows_agent/policy.py` – safety rules.

AI tools must respect and reuse this structure; do **not** invent random new top-level dirs.

---

## 3. Language & style rules

### 3.1 Backend (Python)

- Version: Python 3.11+.
- Style: **PEP8**, but prioritize clarity over over-abstracting.
- Typing: **use type hints everywhere** (`-> None` included).
- Frameworks:
  - HTTP: FastAPI or equivalent minimal ASGI (if needed).
  - Agents: Stream Video + Vision Agents for voice flows (do **not** roll your own STT loop).
- Error handling: raise meaningful exceptions or return `Result`-like objects; **never ignore exceptions**.
- Config: use environment variables via a central config module, don’t hard-code API keys.

### 3.2 Frontend (Next.js)

- Use **TypeScript**.
- Use **pnpm** as the package manager (do NOT use npm or yarn).
- Prefer React Server Components for heavy data fetching where relevant.
- Use standard hooks, avoid overcomplicated state management for MVP.
- Wrap voice logic in a dedicated hook, e.g. `useVoiceSession()`.

### 3.3 Windows agent (Python)

- Use `pywinauto` for GUI automation; UIA backend by default for modern apps.[web:52][web:283]
- Separate Windows-specific logic from generic command handling.

### 3.4 Naming conventions

- Python:
  - files: `snake_case.py`
  - classes: `PascalCase`
  - functions: `snake_case`
  - async functions: `async def` + `snake_case`
- TypeScript:
  - components: `PascalCase.tsx`
  - hooks: `useCamelCase.ts`
  - utilities: `camelCase.ts`

---

## 4. Tooling rules for AI

### 4.1 Voice tools

AI must treat voice as:

- An external session managed by Stream Video + Vision Agents.
- Backend should not manually implement WebRTC; it **calls Stream** services.

Patterns:

- When writing backend code, assume we already have a Stream Video + Vision Agents setup; backend receives **text** and **tool events** via the agent's callback/WebSocket layer, not raw audio.

### 4.2 Browser tools

- Use `services/browser_use_client.py` to trigger browser tasks.
- Do **not** write Selenium/Playwright unless explicitly requested.
- For new browser automation tasks, add new methods to the Browser Use client or wrapper, not new automation stacks.

### 4.3 Windows tools

- Use `services/windows_agent_client.py` on backend side; send structured JSON commands.
- Windows agent should use `pywinauto.Application` + UIA backend for app control, and `mouse`/`keyboard` helpers for input.[web:52][web:279][web:283]
- Prefer control-based actions (find and click a button) over raw coordinates.

### 4.4 Research & memory tools

- Treat Research as a longer-running task; use a separate orchestrator or LangGraph in future, **not** random chains of `requests.get` scattered across code.[web:276][web:271]
- For memory, always persist through `core/memory.py` → `services/db.py`, never direct DB calls from random modules.

---

## 5. How AI should use the docs

When AI is generating or editing code, it must:

1. Read the PRD summary:
   - `02_prd_master.md` – product goals and constraints.
2. Read architecture overview:
   - `07_architecture_doc.md` – components, flows, deployment.
3. Read feature-level behaviors:
   - `04_feature_specs.md` – voice, browser, Windows, research, memory.

Rules:
- Do **not** invent new features outside these docs.
- If a user prompt conflicts with docs, **ask for clarification** instead of silently violating docs.

---

## 6. Safety & permissions (coding rules)

- Treat **sensitive actions** as a separate class: deleting files, sending messages, changing system settings, purchases.
- All sensitive actions must be routed through:
  - backend policy checks, and
  - `windows_agent/policy.py` on local side.
- AI must never write code that performs sensitive actions without a clear `confirm` flag or user confirmation in the flow.

---

## 7. Testing & quality rules

- Write tests for core logic:
  - `core/conversation.py`
  - `core/tools.py`
  - windows agent handlers (`apps.py`, `files.py`)
- Use pytest for backend and agent code.
- Avoid huge god-functions; prefer small, testable functions.

---

## 8. Things AI must not do

1. Do **not**:
   - Switch architecture to microservices/k8s on its own.
   - Replace Stream Video + Vision Agents with another voice stack unless explicitly asked.
   - Replace Browser Use with Selenium/Playwright unless explicitly asked.[web:43][web:291]
   - Replace pywinauto with other desktop automation frameworks unless asked.[web:52][web:279]
2. Do **not**:
   - Hard-code API keys.
   - Add new database engines without updating docs.
   - Pull in huge new dependencies for small tasks.
3. Do **not**:
   - Ignore architecture or feature specs.
   - Invent new product behavior that contradicts PRD.

---

## 9. How to extend the project

When adding new capabilities, AI should:

1. Check if the feature is already described in PRD/architecture/specs.  
2. If it is new, add/update docs **first**, then code.  
3. Keep new modules consistent with existing directory and naming patterns.

Examples:

- New browser feature → add method in `services/browser_use_client.py` + wrapper in `core/tools.py`.
- New Windows action → add handler in `windows_agent/handlers/...` + client call in `services/windows_agent_client.py`.
- New research workflow step → add node in LangGraph graph (future), not random while loops.

---

## 10. Summary for AI

- This project is **voice-first**, **cloud + local hybrid**, **Python backend**, **Python Windows agent**, **React/Next frontend**.
- Use **Stream Video + Vision Agents** for voice pipeline; don't reinvent audio protocols.
- Use **Browser Use** for browser tasks; no fresh Selenium/Playwright stacks.[web:43][web:275][web:291]
- Use **pywinauto** for Windows control; no random pyautogui for core flows.[web:52][web:279][web:283]
- Respect PRD + architecture + feature specs.
- Always use **pnpm** for frontend tasks and prefer **stable** package versions.
- If in doubt, ask for clarification instead of making big architectural changes.
---

## 11. Technical Constraints (Package Management & Versioning)

- **Package Manager (Frontend)**: Always use `pnpm`. This is a project-wide requirement for the frontend directory.
- **Package Versions**: 
  - Use **stable versions** for all dependencies by default.
  - Use **latest** or **advanced (canary)** versions ONLY when specifically required for smooth integration of cutting-edge features or as advised by product specs.
  - Avoid using alpha/beta releases unless there is no stable alternative for a required capability.
- **Node.js**: Use a stable LTS version.
