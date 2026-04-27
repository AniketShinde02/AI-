# Nexus 2.0 – Full Architecture & Execution Blueprint (v2)

> Living system design + execution strategy for an AI-first autonomous productivity assistant (Nexus 2.0).

---

## 1. Purpose & Scope

This document is the **single-source architecture and execution blueprint** for Nexus 2.0.

It merges:
- The existing PRD, architecture doc, feature specs, DB schema, API contract, and AI context.
- A free-tier–first infra and tooling strategy.
- A realistic monetization and execution plan for an early-stage solo founder.

The goal is to:
- Avoid Nexus 1.0–style thrash.
- Ship a lean, monetizable, scalable system.
- Keep the complexity **just enough** to not block future growth.


---

## 2. Product & System Overview

### 2.1 Product Summary

Nexus 2.0 is a **voice-first, login-enabled AI assistant** that:
- Listens in natural language (starting with English), via streaming voice.
- Understands intent and asks clarifying questions.
- Executes **real work**:
  - Browser automation on public + logged-in sites.
  - Windows desktop control via a local agent.
  - File & folder operations and utility tasks.
- Generates structured outputs (markdown docs, summaries, logs).
- Maintains account-backed history and memory for each user.

The system starts as a **cloud-backed web app** with a Windows local agent and later becomes a packaged Windows desktop app (Tauri).

[cite:4][cite:6]


### 2.2 Architecture Pattern

Core pattern: **Cloud-backed modular monolith + local Windows agent + browser automation**.

- Backend: single FastAPI Python app structured into clear internal modules.
- Frontend: Next.js app deployed on Vercel.
- Voice: GetStream Video + Vision Agents (replacing all LiveKit references).
- Browser automation: Browser Use integration.
- Windows control: Python local agent using pywinauto.
- Data: Supabase Postgres + pgvector.

This pattern keeps ops simple while preserving good boundaries for future scaling.

[cite:6][cite:7]


---

## 3. High-Level System Map

### 3.1 Major Components

**Client Layer**
- Next.js web app (TypeScript) for voice + chat UI, task history, outputs, settings, and billing.
- Future Tauri Windows shell that wraps the web UI and adds desktop-native features.

**Voice & Realtime Layer**
- GetStream Video + Vision Agents for:
  - WebRTC voice sessions.
  - Streaming STT using Deepgram or similar.
  - TTS playback.
  - Interruption management.

**Core Backend (Modular Monolith)**
- FastAPI Python app with modules for:
  - Auth & identity
  - Conversation orchestrator
  - Voice session manager
  - Tool router
  - Task manager
  - Memory service
  - Output generator
  - Billing/quota
  - Audit & logs

**AI Layer**
- LLM router using OpenRouter to select models per task.
- Fast intent classifier using Groq-hosted Llama models.
- Specialized sub-agents for browser tasks, research, and memory extraction.

**Tool Execution Layer**
- Browser Use engine.
- Local Windows agent (Python + pywinauto) over HTTP/WebSocket.
- Future research workflows (LangGraph-based) for deep research.

**Data & Storage Layer**
- Supabase Postgres (tables for users, sessions, tasks, tool_runs, memory_items, output_documents).
- pgvector extension for semantic retrieval.
- Cloudflare R2 or Supabase Storage for markdown outputs and artifacts.

**Billing & Analytics**
- LemonSqueezy or Stripe for subscription billing.
- Langfuse for LLM tracing.
- Posthog for product analytics + feature flags.
- Sentry for error tracking.

[cite:4][cite:6][cite:9][cite:1][cite:7]


### 3.2 Data Flow (Simplified)

1. User speaks or types a request in the Next.js UI.
2. If voice, audio streams to GetStream Video + Vision Agents, which performs STT and sends text to the backend.
3. Backend orchestrator classifies intent (simple answer vs browser task vs Windows task vs research).
4. Tool router dispatches to Browser Use or Windows agent as needed.
5. Tool results are passed back through the orchestrator and summarized by the LLM.
6. Outputs are stored as markdown documents and linked to tasks.
7. Memory is updated with important facts and task context.

[cite:4][cite:5][cite:6]


---

## 4. Detailed Architecture by Layer

### 4.1 Frontend Layer (Next.js)

**Tech**
- Next.js + TypeScript.
- pnpm as package manager.
- TanStack Query for data fetching.
- GetStream JS SDK for voice/chat sessions.

**Key UI Surfaces**
- Conversation screen: voice button, text input, message list, live task status.
- Task timeline: list of tasks with status, type, and links to outputs.
- Outputs page: markdown document viewer.
- Settings: preferences, permissions, language direction (English first, Hindi/Marathi later).
- Billing: current plan, upgrade button, limits remaining.

The UI must call only the backend API client, never raw `fetch`, to keep network logic centralized.

[cite:7][cite:6]


### 4.2 Voice & Realtime Layer

**Stack**
- GetStream Video + Vision Agents as the central voice agent runtime.
- Streaming STT provider (e.g., Deepgram) integrated via Vision Agents.
- TTS provider (OpenAI TTS or ElevenLabs).

**Responsibilities**
- Establish low-latency audio sessions.
- Provide streaming transcripts.
- Handle interruptions (user talking over assistant).
- Manage sleep mode (ignore audio until reactivated).

**Behaviour**
- Frontend requests a Stream token from backend.
- UI joins a Stream/Vision Agents session.
- STT results are emitted as text events.
- Backend registers callbacks to receive text and tool events rather than raw audio.

[cite:3][cite:5]


### 4.3 Core Backend — Modular Monolith

**Framework**
- FastAPI (ASGI) with type hints and Pydantic models.

**Modules**

- `api/`
  - HTTP routes: auth, sessions, messages, tasks, documents, billing, Stream token.
  - WebSocket/SSE endpoints for task status streaming.

- `core/conversation.py`
  - Main orchestrator: receives user turns, calls intent classifier, decides next actions.
  - Decides whether to:
    - respond directly via LLM,
    - trigger browser_task,
    - trigger windows_task,
    - or start a research_task.

- `core/voice.py`
  - Connects to GetStream/Vision Agents callbacks.
  - Maps Stream events to session and message records.

- `core/tools.py`
  - Tool routing: `browser_task`, `windows_task`, `research_task`, `file_task`, `utility_task`.
  - Applies safety and confirmation rules for risky operations.

- `core/tasks.py`
  - Task lifecycle: create, update, state transitions, event logs.
  - Ensures consistent state machine: `pending → running → succeeded/failed/cancelled`.

- `core/memory.py`
  - Memory CRUD: store profile/session/task memories.
  - Importance scores and future embedding hooks.

- `core/outputs.py`
  - Generates markdown docs for research and complex tasks.
  - Writes documents to DB and/or object storage.

- `core/billing.py`
  - Plan metadata and quota checks.
  - Metrics: task runs, browser tasks, research tasks, voice minutes.

- `core/audit.py`
  - Logs tool runs, errors, and key security-relevant events.

[cite:6][cite:7]


### 4.4 Services Layer (Integrations)

- `services/stream_client.py`
  - Communicates with GetStream backend.

- `services/llm_router.py`
  - Routes prompts to OpenRouter models.
  - Example policies:
    - intent classification → fast Llama via Groq.
    - simple Q&A → GPT-4o-mini.
    - complex planning → GPT-4o or Claude 3.5.

- `services/tts_client.py`
  - Wraps TTS provider.

- `services/browser_use_client.py`
  - Wraps Browser Use HTTP/WebSocket API.
  - Accepts high-level goals and constraints.

- `services/windows_agent_client.py`
  - Connects to local agent via HTTP/WebSocket.
  - Sends structured JSON commands.

- `services/db.py`
  - Supabase Postgres connection and session management.

- `services/storage.py`
  - Abstraction over Supabase Storage / Cloudflare R2.

- `services/queue.py`
  - Inngest or equivalent job queue integration for async tasks.

- `services/billing_client.py`
  - LemonSqueezy/Stripe checkout and webhooks.

[cite:7][cite:1]


### 4.5 Local Windows Agent

**Implementation**
- Python 3.11+
- FastAPI or Starlette for local HTTP/WS server.
- pywinauto for app/window control.

**Modules**
- `windows_agent/server.py` — HTTP/WS server.
- `handlers/apps.py` — open/focus apps.
- `handlers/files.py` — file and folder operations.
- `handlers/input.py` — keyboard/mouse.
- `policy.py` — local safety rules (deny or confirm destructive actions).

**API Contract**
- Single `POST /agent/actions` endpoint with `{ action, request_id, params }` envelope.
- Responses include status (`succeeded`/`failed`), result, and error fields.

[cite:1][cite:5][cite:7]


### 4.6 Browser Automation

**Stack**
- Browser Use as the sole browser automation engine.

**Responsibilities**
- Use the user’s local browser profile initially to reuse logged-in sessions.
- Support navigation, form filling, clicking, and extraction.
- Return structured result data plus plain text summary.
- Provide explicit error messages for blocked logins, captchas, and layout changes.

The goal is to **not** reinvent Playwright automation but to wrap Browser Use in a stable API.

[cite:5]


### 4.7 Data & Storage

**DB: Supabase Postgres**
- Tables:
  - `users`, `sessions`, `conversation_turns`,
  - `tasks`, `task_events`, `tool_runs`,
  - `memory_items`, `output_documents`,
  - plus a new `billing_usage` table.

**Vector Search: pgvector**
- Add `embedding` columns where needed (e.g., memory_items).

**Storage**
- Supabase Storage or Cloudflare R2 for markdown docs and files.

[cite:9]


### 4.8 Billing & Analytics

**Billing**
- LemonSqueezy or Stripe subscriptions.
- Webhook endpoint updates `users.plan` and resets monthly usage.

**Analytics & Observability**
- Langfuse for LLM traces and prompt performance.
- Posthog for product funnels and feature usage.
- Sentry for error reporting.

These are critical to debug browser and Windows automation reliability.

[cite:4][cite:6]


---

## 5. Database Schema & Extensions

### 5.1 Core Tables (from Existing Schema)

You already have a strong relational schema:
- `users` — accounts and settings.
- `sessions` — interaction sessions.
- `conversation_turns` — messages.
- `tasks` — high-level tasks.
- `task_events` — event logs per task.
- `tool_runs` — each tool invocation.
- `memory_items` — persistent memory.
- `output_documents` — markdown docs.

[cite:9]


### 5.2 New Fields for Billing & Plans

Extend `users`:
- `plan` — `free`, `pro`, `power`.
- `plan_renews_at` — timestamp.

New table `billing_usage`:
- `user_id` — FK to users.
- `metric` — e.g., `tasks`, `browser_tasks`, `research_tasks`, `voice_minutes`.
- `period` — date or month.
- `count` — integer.

This lets you enforce quotas and display remaining usage in the UI.


### 5.3 RLS & Security

Supabase RLS rules should enforce that:
- A user can only see their own rows in all user-scoped tables.
- System-level tables (plan metadata) are read-only.

[cite:9]


---

## 6. API Contract Highlights

Your existing contract is good: versioned RESTful API, JSON payloads, consistent error shapes.

Key surfaces:
- `/api/v1/auth/*` — registration, login, current user.
- `/api/v1/sessions` — create sessions.
- `/api/v1/sessions/{id}/messages` — send messages.
- `/api/v1/tasks` and `/api/v1/tasks/{id}` — task listing and status.
- `/api/v1/tasks/{id}/documents` — task outputs.
- Local `/agent/actions` on Windows.

New endpoints needed:
- `/api/v1/billing/portal` — get checkout URL.
- `/api/v1/billing/webhook` — handle payment events.
- `/api/v1/usage` — show current usage and limits.

[cite:1]


---

## 7. Free-Tier–First Stack Strategy

### 7.1 Infra

- **Frontend:** Vercel free tier for Next.js.
- **Backend:** Railway $5/mo starter; autosleep off.
- **Database:** Supabase free tier.
- **Object Storage:** Cloudflare R2 free tier.
- **Queue:** Inngest free tier.

This keeps infra spend minimal while supporting production-grade hosting.


### 7.2 Core Services

- **Auth:** Supabase Auth (free, integrated with Postgres and RLS).
- **LLM:** OpenRouter; start with GPT-4o-mini and Groq Llama for cost and speed.
- **STT:** Deepgram, using free credits and cheap streaming.
- **TTS:** OpenAI TTS or ElevenLabs, pay per use.
- **Automation:** Browser Use (OSS) and local Windows agent.
- **Analytics:** Posthog, Langfuse, Sentry — all have generous free tiers.

[cite:4][cite:5][cite:6][cite:7]


### 7.3 Vector DB Choices

Start with **pgvector on Supabase** instead of adding a separate vector database.
- No extra hosting.
- Good enough for semantic memory retrieval and simple RAG.
- You can revisit Qdrant/Turso later only if you hit scaling limits.

[cite:5][cite:9]


---

## 8. Monetization Model & Flows

### 8.1 Plans

**Free**
- 20 tasks/month.
- 5 browser tasks/month.
- English only.

**Pro ($15/month)**
- 200 tasks/month.
- 50 browser tasks/month.
- Priority queue.
- Basic research tasks.

**Power ($39/month)**
- Unlimited normal tasks.
- 500 browser tasks/month.
- Research mode unlocked.
- Priority support.


### 8.2 Quota Enforcement

- Billing middleware runs before tool execution.
- Checks `billing_usage` for current period.
- If exceeding quota:
  - Return a specific error code (e.g., `QUOTA_EXCEEDED`).
  - Frontend shows upgrade modal.


### 8.3 Why This Can Make Money Fast

- Browser automation of logged-in sites is painful and high-value.
- Windows control saves time for power users.
- Paying users are more likely to be devs, founders, and operators with real automation problems.

[cite:4]


---

## 9. Gaps, Risks, and Simplifications

### 9.1 Strong Existing Choices

- Modular monolith over microservices.
- Browser Use for browser automation.
- pywinauto for Windows control.
- Detailed DB schema and API contract.
- AI context file controlling architecture and code style.

[cite:4][cite:5][cite:6][cite:7][cite:9][cite:1]


### 9.2 Weaknesses (Fixed in This Blueprint)

- Conflicting voice stack (LiveKit vs GetStream): resolved in favor of GetStream.
- Lack of billing: now defined with plan/usage tables and middleware.
- No async queue: Inngest introduced.
- No observability: Langfuse/Posthog/Sentry added.


### 9.3 Overengineering to Avoid

- Multi-vector DB setups.
- Complex LangGraph research flows before basic tasks are stable.
- Tauri packaging before web app is solid.
- Custom LLM proxy infra.

[cite:4][cite:5][cite:6]


---

## 10. Execution Roadmap (Founder-Focused)

### 10.1 First 30 Days — MVP

**Goal:** A user can sign up, talk to the assistant, run one browser task and one Windows task, and see results.

Steps:
1. Supabase project + schema + RLS.
2. FastAPI backend with auth and session endpoints.
3. Next.js frontend with login and basic chat UI.
4. GetStream voice loop with Deepgram STT.
5. Browser Use integration for one end-to-end browser task.
6. Windows agent with 2–3 commands.
7. Billing integration with basic quotas.

[cite:4][cite:6]


### 10.2 First 90 Days — First Paying Users

- Stabilize reliability of browser and Windows tasks.
- Add 10–15 high-value automation recipes.
- Add basic memory retrieval.
- Improve error handling and messaging.
- Launch to small beta, iterate, then do a public launch.


### 10.3 Six Months — Stable SaaS

- Broader Windows command set.
- Simple research mode.
- Tauri-packaged Windows app.
- Harden observability and alerting.
- Start pushing for 100+ paying users.

[cite:4]


---

## 11. Guidance for Non-Senior Founder

**Focus hard on:**
- Getting the request→response→task→result loop working.
- Logging everything (tasks, tool runs, errors).
- Billing and quotas from day one.

**Ignore early:**
- Fancy UI polish.
- Full multilingual support.
- Perfect test coverage (focus tests on orchestrator and tools).
- Tauri packaging.

**Use AI coding tools for:**
- Converting DB schema to models.
- Writing boilerplate FastAPI endpoints.
- Writing pywinauto handlers.
- Drafting tests for orchestrator logic.

[cite:7]


---

## 12. Excalidraw Architecture Prompt

Use this prompt in Excalidraw AI:

> Create a professional architecture diagram for Nexus 2.0, an AI-first autonomous productivity assistant.
> 
> Style:
> - Modern startup CTO style
> - Hand-drawn Excalidraw look
> - 6 color groups: client (blue), voice (purple), backend (green), AI+tools (orange), data (gray), billing+analytics (red)
> - Clear group boxes and short technical labels
> - Arrows with labels to show data flow
> 
> Groups:
> 
> 1. Client Layer (blue):
>    - Next.js Web App (voice UI, chat UI, task timeline, outputs, billing)
>    - Tauri Desktop Shell (future)
> 
> 2. Voice / Realtime (purple):
>    - GetStream Video + Vision Agents
>    - Deepgram STT
>    - TTS Provider
> 
> 3. Core Backend — FastAPI Modular Monolith (green):
>    - API Layer
>    - Auth & Identity
>    - Billing / Quota Middleware
>    - Conversation Orchestrator
>    - Voice Session Manager
>    - Tool Router
>    - Task Manager
>    - Memory Module
>    - Output Generator
>    - Audit & Logs
> 
> 4. AI & Tools (orange):
>    - AI Layer: Groq (intent), OpenRouter (GPT-4o / Claude) for reasoning
>    - Tool Execution: Browser Use, Windows Agent (pywinauto), Inngest Queue
> 
> 5. Data & Storage (gray):
>    - Supabase Postgres + pgvector (users, sessions, tasks, memory, embeddings)
>    - Cloudflare R2 / Supabase Storage (markdown outputs, files)
>    - Supabase Realtime (task updates)
> 
> 6. Billing & Observability (red):
>    - LemonSqueezy (subscriptions, webhooks)
>    - Langfuse (LLM traces)
>    - Posthog (product analytics, feature flags)
>    - Sentry (error tracking)
> 
> Arrows:
> - Next.js → GetStream → Deepgram STT → Backend Orchestrator
> - Next.js → API Layer (HTTPS)
> - Orchestrator → Tool Router → Browser Use
> - Orchestrator → Tool Router → Windows Agent
> - Orchestrator → Memory Module → Supabase
> - Output Generator → Cloudflare R2
> - API Layer → Billing / Quota → LemonSqueezy
> - Backend → Langfuse / Posthog / Sentry
> - Supabase Realtime → Next.js (task status updates)
> 
> Add footer note: "Nexus 2.0 — Cloud-backed modular monolith + local Windows agent + browser automation. Free-tier–optimized, monetization-ready."
