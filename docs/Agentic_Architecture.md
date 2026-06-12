# Nexus 2.0 Agentic Architecture

## 1. Design Goals

Nexus 2.0 is a **user-owned, agentic operating system** for the browser and desktop:
- Voice-first interface (STT → reasoning → TTS).
- Central "brain" that orchestrates many specialized sub-agents.
- Uses many free/cheap AI APIs and tools without collapsing under token/rate limits.
- Local-first: users bring their own keys; infra is thin cloud + desktop.

The architecture below is meant to be **buildable by a solo dev**, not a research lab.

---

## 2. High-Level System Map

Text diagram of the core components and flows:

```text
[User]
  │ (voice / text)
  ▼
[Input Layer]
  - STT (Deepgram / OpenAI / Groq)
  - Text input (Next.js / Tauri)
  │
  ▼
[Central Brain]
  - Orchestrator
  - Policy engine (safety, costing, routing)
  - Memory router (short/long-term)
  - Agent router (which sub-agent to wake)
  │
  ├──► [Reasoning Models Pool]
  │       (Groq, OpenRouter, free coding models, etc.)
  │
  ├──► [Sub-Agents Layer]
  │       - Browser Agent (PinchTab / Playwright)
  │       - PC Agent (Windows / filesystem / processes)
  │       - Research Agent (web search + RAG)
  │       - Data Agent (sheets / DB / CSV)
  │       - Memory Agent (summarization + indexing)
  │
  ├──► [Tools & APIs]
  │       - Browser automation
  │       - Filesystem & OS
  │       - External APIs (Notion, Google, etc.)
  │
  ▼
[Result Synthesizer]
  - Formats answer per user style
  - Annotates with traces
  │
  ├──► [Output: Text]
  └──► [Output: Voice]
```

---

## 3. Central Brain Architecture

Core responsibilities of the brain:
- Interpret user intent.
- Route to the right sub-agent(s).
- Choose appropriate models and tools based on cost/latency/quality.
- Maintain and query memory.
- Enforce safety and budget policies.
- Stream progress updates back to the user.

### 3.1 Core Data Structures

**Request envelope** (what every turn looks like inside Nexus):

```json
{
  "user_id": "uuid",
  "session_id": "uuid",
  "input": {
    "modality": "voice|text",
    "raw": "User raw text",
    "transcript": "Transcribed text if voice",
    "language": "en-IN"
  },
  "context": {
    "short_term": [...],
    "long_term_candidates": [...],
    "user_profile": {...}
  },
  "meta": {
    "client": "desktop|web",
    "latency_budget_ms": 2000,
    "max_cost_cents": 2
  }
}
```

**Task object** (created whenever work must be done):

```json
{
  "task_id": "uuid",
  "user_id": "uuid",
  "goal": "Find potential Instagram leads for website services",
  "status": "pending|running|completed|failed|cancelled",
  "subtasks": [ ... ],
  "agent_assignments": [ ... ],
  "tool_calls": [ ... ],
  "result": null,
  "created_at": "...",
  "updated_at": "..."
}
```

### 3.2 Brain Components

- **Intent Classifier**: cheap model that classifies every request into:
  - `small_talk`, `qa`, `browser_task`, `pc_task`, `research`, `multi-step_project`.
- **Planner**: heavier reasoning model that, when needed, decomposes into subtasks.
- **Agent Router**: maps subtasks to sub-agents (browser/pc/research/etc.).
- **Memory Router**: decides which memories to fetch and when to write new ones.
- **Policy Engine**: enforces rate/cost and safety rules:
  - Per-user daily token budget.
  - Provider-specific RPM/TPM limits.
  - Which models are allowed for which tasks (e.g., high-risk tasks require higher-accuracy models).
- **Streaming Engine**: manages SSE/WebSocket streams to the UI so nothing feels blocking.

Implementation: single FastAPI app with internal services modules (e.g. `core/orchestrator.py`, `core/policy.py`, `core/memory.py`, `core/agents.py`).

---

## 4. Multi-Model Routing (100+ APIs)

### 4.1 Model Registry

Instead of hardcoding providers, maintain a **model registry**:

```yaml
models:
  - id: qwen2.5-coder-7b-groq
    provider: groq
    type: coding
    cost_per_million: 0
    latency_ms_p50: 80
    max_tokens: 8_000
    strengths: ["code", "classification"]
    weaknesses: ["long narrative"]

  - id: llama-3.3-70b-openrouter
    provider: openrouter
    type: reasoning
    cost_per_million: 5
    latency_ms_p50: 450
    strengths: ["deep reasoning", "multi-step planning"]
    weaknesses: ["expensive"]

  - id: deepseek-v2-lite-together
    provider: together
    type: coding
    cost_per_million: 0
    latency_ms_p50: 120
    strengths: ["agents", "tool use"]
```

The registry is kept as a JSON/YAML file + in DB so the brain can update scores at runtime.

### 4.2 Routing Heuristics

For each request, the brain computes a **model score**:

```text
score = w1 * (1 / latency_ms) + w2 * quality_score - w3 * cost_score
```

Where:
- `latency_ms` comes from recent telemetry (p50 or p95).
- `quality_score` is derived from offline benchmarks + online success rates.
- `cost_score` increases when the user is on a free tier.

The router chooses:
- **Classifier model**: always the cheapest fastest (`qwen2.5-coder` / `gemma-2b`).
- **Planner model**: depends on task difficulty (complex browser project vs simple one-shot search).
- **Execution models**: coding models for writing scripts, summary models for results.

### 4.3 Provider & Key Management

Maintain a **key pool** for each provider:

```yaml
groq_keys:
  - alias: default
    key: env:GROQ_KEY_1
    max_rpm: 30
  - alias: backup
    key: env:GROQ_KEY_2
    max_rpm: 30
```

Runtime `KeyManager` keeps rolling counters per key and picks the next key with capacity.
If all keys for a provider are exhausted:
- Downgrade to another provider’s compatible model.
- Or throttle and return a "too busy, trying again" message instead of hard failing.

---

## 5. Persona & Memory System

Goal: treat each user like a **consistent person** Nexus knows well, without losing truthfulness.

### 5.1 Memory Scopes

- **Profile Memory (User Identity)**
  - Name, handle, timezone, language, roles ("Indie dev in Pune"), preferred tone ("direct, no sugarcoating").
  - Stored as one or a few documents per user.

- **Session Memory (Short-Term)**
  - Last N conversation turns with derived summary.
  - Stored per session; used heavily during the live conversation.

- **Task Memory**
  - Facts discovered while doing a specific task (e.g., competitor list, scraped leads).
  - Linked to `task_id` and can be reused later.

- **Long-Term Memory**
  - Extracted, distilled facts from profile, sessions, and tasks.
  - Embedded into vector store for retrieval.

### 5.2 Memory Write Pipeline

1. After each task or long session, the Memory Agent gets:
   - Conversation transcript
   - Task logs (actions taken, results)
2. It extracts **atomic memories**:
   - "User prefers short bullet answers for coding questions."
   - "User runs a web dev agency targeting Instagram creators."
   - "Lead: @handle, niche: fitness, follower_count: 32k."
3. Each memory is stored with:
   - `importance` (1–5)
   - `recency` (timestamp)
   - `source` (profile / session / task)
   - `embedding` for semantic retrieval.

### 5.3 Memory Read Pipeline

For each new message:

1. Build a **retrieval query**:
   - Based on user request + recent conversation summary.
2. Fetch:
   - Top K long-term memories by semantic similarity.
   - Top K high-importance memories regardless of similarity.
   - Profile memory.
3. Brain builds a **context pack**:

```text
[PROFILE]
- Name: Aniket
- Role: AI-augmented developer in Pune
- Preferences: Direct, no sugarcoating, forward-looking

[LONG-TERM]
- User is building Nexus 2.0 agentic OS.
- User prefers Firebase / NoSQL for flexibility.

[RECENT]
- Last 5 messages in this session.
```

### 5.4 Behavioral Learning

Update profile and memory on patterns:
- If the user repeatedly rewrites answers shorter: update `preferred_length = short`.
- If user thumbs-down voice responses but thumbs-up text: reduce TTS use.

A simple heuristic engine updates profile fields when a pattern repeats (e.g. 5+ times).

### 5.5 Scaling Memory

As data grows:

- **Time-based pruning**: reduce importance of old low-value memories.
- **Clustering & summarization**:
  - Cluster similar memories (e.g. “Instagram lead candidates”) and replace them with a summary + pointer to full dataset.
- **Tiered storage**:
  - Hot: recent + important (fast vector DB).
  - Warm: older but referenced (cheaper storage).
  - Cold: archived exports (user-owned files).

---

## 6. Personalization vs Truthfulness

Nexus must be **personalized** but not delusional.

Strategies:

- Use persona data to adjust:
  - Tone (casual vs formal).
  - Level of detail.
  - Examples (using user’s domain: dev, agency, etc.).
- Never let persona override facts:
  - System prompt: "Adapt style to user preferences, but never modify factual content to flatter or agree."
- For controversial topics:
  - Present multiple viewpoints and clearly mark uncertainty.

This keeps Nexus "on the user’s side" without becoming an echo chamber.

---

## 7. Universal Task Execution System

Instead of hardcoding flows for each use case, define a **generic task graph**.

### 7.1 Task Graph Model

A task is represented as a DAG (Directed Acyclic Graph) of steps:

```json
{
  "task_id": "uuid",
  "goal": "Find potential Instagram leads for website services",
  "steps": [
    {
      "id": "s1",
      "type": "plan",
      "status": "completed",
      "output": "We will: 1) search IG, 2) scrape profiles, 3) filter, 4) store in sheet"
    },
    {
      "id": "s2",
      "type": "browser_search",
      "depends_on": ["s1"],
      "status": "running",
      "agent": "browser_agent",
      "params": {"query": "instagram marketing coaches"}
    },
    {
      "id": "s3",
      "type": "scrape_profiles",
      "depends_on": ["s2"],
      "agent": "browser_agent"
    },
    {
      "id": "s4",
      "type": "filter_leads",
      "depends_on": ["s3"],
      "agent": "data_agent",
      "params": {"criteria": {"followers_min": 5000}}
    },
    {
      "id": "s5",
      "type": "store_leads",
      "depends_on": ["s4"],
      "agent": "data_agent",
      "params": {"target": "google_sheet"}
    }
  ]
}
```

### 7.2 Agent Responsibilities

- **Planner (Brain)**:
  - Converts natural language goal into a coarse plan (list of step types).
- **Browser Agent** (PinchTab/Playwright):
  - Navigates to sites, runs focused searches, clicks, scrolls.
  - Returns structured data (DOM snippets, accessibility tree, extracted fields).
- **Data Agent**:
  - Cleans, filters, and transforms data.
  - Writes to user-owned destinations (Google Sheets, CSV, Firebase, etc.).
- **Research Agent**:
  - Fetches supporting info (guidelines, best practices).
- **Memory Agent**:
  - Stores useful results as task memories.

### 7.3 Execution Engine

- Maintains task state in DB (`tasks` and `task_steps` collections/tables).
- Uses a queue (Inngest, Celery, or simple background workers) to execute each step.
- Step transitions:
  - `pending → running → completed|failed`.
- UI subscribes to SSE/WebSocket for updates.

This allows any new use case to be handled by teaching the planner new step types, not writing new code flows.

---

## 8. Real-Time Behavior & Streaming

### 8.1 Non-Blocking Execution

- All heavy work (LLM calls, browser actions) runs in background workers.
- API returns quickly with `task_id`.
- Frontend opens a stream:
  - `GET /tasks/{task_id}/stream` (SSE) or WebSocket.

### 8.2 Stream Event Types

- `task.created` – when task is enqueued.
- `task.updated` – generic status updates.
- `step.started` / `step.completed` / `step.failed` – per-step events.
- `log` – textual logs for debugging.
- `partial_output` – partial reasoning or early summary.
- `final_output` – when task completes.

### 8.3 Parallel vs Sequential Steps

- Steps with no `depends_on` or disjoint dependencies can run in parallel.
- Planner can annotate steps with `parallelizable: true`.
- Execution engine uses worker pool to run multiple steps concurrently, within safe resource limits.

---

## 9. Voice Command Integration

### 9.1 Flow

```text
Mic → STT → Brain → Planner → Agents → Synthesizer → TTS → Speaker
```

### 9.2 Components

- **STT**:
  - Streaming STT (Deepgram/Groq/OpenAI) sending partial transcripts.
  - Brain treats STT as a source of text turns.

- **Voice Session Manager**:
  - Handles join/leave, barge-in (interrupt existing TTS), and push-to-talk.

- **Prompt Transformation**:
  - Voice-specific patterns ("uh", "like", etc.) cleaned.
  - Add metadata: microphone state, noise level, language.

- **TTS**:
  - Streaming TTS for quick feedback.
  - Uses small chunks (sentence-level) to reduce latency.

- **Error Handling**:
  - If STT confidence < threshold, ask user to repeat.

---

## 10. Local-First, User-Owned Infra

### 10.1 Deployment Shape

- **Desktop App**: Tauri app (Rust + webview) provides:
  - Local UI and voice capture.
  - Local agent for PC control (Windows / macOS).
  - Stores local config (API keys, preferences) encrypted.

- **Cloud Backend (Thin)**:
  - FastAPI service on Render / Railway / Vercel functions for orchestrator.
  - Only stores minimal metadata if user opts in (tasks, memory, logs).

### 10.2 BYOK (Bring Your Own Keys)

- Users paste keys into Tauri UI for providers (Groq, OpenAI, Deepgram, etc.).
- Keys stored locally (OS keychain or encrypted file).
- Desktop app calls providers directly when possible:
  - LLM, STT, TTS requests originate from user’s machine.
- Backend is mostly coordination + webhooks + memory.

### 10.3 Workload Distribution

- **Local Machine**:
  - Voice capture (mic) + TTS playback.
  - PC control (filesystem, apps).
  - Potentially STT/LLM when local models (Ollama) are used.

- **Cloud**:
  - Orchestrator & memory.
  - Heavy LLM reasoning (unless user has GPU).
  - Browser automation (PinchTab, if hosted) or local version within Tauri.

This keeps costs low for you and lets power users scale themselves.

---

## 11. API Scaling & Key Management

### 11.1 100+ APIs Without Chaos

- Keep a **unified tool schema** internally:

```json
{
  "id": "search_web",
  "category": "research",
  "input_schema": {"query": "string"},
  "output_schema": {"results": "array"},
  "providers": ["serpapi", "tavily", "custom"]
}
```

- Each provider implementation conforms to this schema and is selected by policy.

### 11.2 Key Rotation & Limits

- Per-provider key pool with usage counters.
- Store usage stats in DB:
  - calls, tokens, last_used, error rates.
- When one key reaches 80% of expected quota, de-prioritize it.

### 11.3 Cost Optimization

- Default to **free/cheap models** (Groq, DeepSeek, etc.).
- Only escalate to expensive models on:
  - High-value tasks (user marked as important).
  - Chronic failures with cheap models.

---

## 12. Prompt Engineering Layer

### 12.1 Prompt Templates

Maintain strongly typed prompt templates for each task:

- **Browser Control**:

```text
You are the Browser Agent for Nexus.
You receive:
- GOAL: high-level goal
- SNAPSHOT: simplified DOM/accessibility tree
- HISTORY: past actions

You must:
- Decide the NEXT ACTION only.
- Output JSON strictly in this format:
  {"kind": "click|type|scroll|navigate|none", "target": "ref", "text": "..."}
```

- **PC Control**:

```text
You control the user's PC via a limited set of safe commands.
Never execute destructive actions without explicit confirmation.
Output JSON-only commands, one at a time.
```

- **Agent Coordination**:

```text
You are the Nexus Planner.
Given the user GOAL and CONTEXT, break the work into a small number
of steps using these step types: [browser_search, scrape, filter, store, summarize,...].
Return a JSON task graph with nodes and dependencies.
```

### 12.2 Verifying Task Completion

- For each step type, define **success predicates**:
  - `browser_search`: page contains at least N matching items.
  - `scrape_profiles`: extracted array non-empty and well-formed.
  - `store_leads`: sheet/DB row count increased by N.

- Agent must include **self-check prompts**:

```text
Before returning SUCCESS, check if the above predicate is true.
If not, either retry with adjusted parameters or mark FAILED with reason.
```

- The brain inspects these signals and may:
  - Retry.
  - Switch tools.
  - Ask user for clarification.

---

## 13. Multimodal Extensions

### 13.1 Camera & Vision

- Use local camera through Tauri + optional Google Live API for advanced vision.
- Flow:
  - Tauri captures image/stream.
  - Sends to Vision Agent API (e.g., Gemini Vision, OpenAI Vision).
  - Vision Agent returns structured description + potential actions.

Example use cases:
- Read text from screen or physical documents.
- Inspect screenshots during browser/PC automation.

### 13.2 Audio Inputs Beyond Voice

- Allow uploading audio files for transcription + analysis.
- Later, support background transcription (meeting assistant mode).

---

## 14. Performance & UX Constraints

### 14.1 Responsiveness Targets

- First response within **<800ms** for simple Q&A.
- For heavy tasks, immediate acknowledgment + task_id + progress bar.
- Continuous typing effect / voice streaming so user never feels blocked.

### 14.2 Operational Safeguards

- Hard timeouts per step (e.g., 30s for browser step).
- Circuit breakers for flaky APIs.
- Retries with backoff for network errors.
- Graceful degradation: "I could not complete step X, but here is partial progress."

---

## 15. Trade-Offs & What Not to Overbuild

You are a solo dev; perfection kills shipping.

Skip or postpone:

- Full-blown LangGraph-style DAG editor; start with JSON and server-side planning.
- Perfect research pipelines; a simple web search + summary loop is enough early.
- Massive evaluation harnesses; instead, collect real user thumbs-up/down signals.
- Managing every API under the sun; support 3–5 best free/cheap ones well, add more later.

Aim for:

- **Reliability over flash**: a smaller set of capabilities that almost never fail.
- **User-owned keys**: let the user scale themselves instead of you burning runway.
- **Incremental complexity**: once the core agent loop is solid, layer on research, vision, etc.

---

## 16. Modular Architecture Layers

Layers, top to bottom:

1. **Interface Layer**
   - Tauri desktop, Next.js web.
   - Voice UI, chat UI, task history, status panel.

2. **Gateway Layer**
   - Auth, rate limiting, logging.
   - Routes requests to orchestrator.

3. **Brain Layer**
   - Orchestrator, planner, policy engine.
   - Model router, agent router, memory router.

4. **Agent Layer**
   - Browser Agent, PC Agent, Research Agent, Data Agent, Memory Agent.

5. **Tool Layer**
   - Concrete integrations: PinchTab, OS commands, Google APIs, Firestore/DB, Sheets.

6. **Storage Layer**
   - User config, tasks, logs, memories, embeddings.

7. **Infra Layer**
   - Render/Railway/Vercel cloud + local desktop app.

Each layer has a clear responsibility and minimal knowledge of the layer below.

---

## 17. Summary

This blueprint gives you:
- A **central brain** with clear routing and policy.
- A scalable, flexible **multi-agent system** not bound to a single provider.
- A user-owned, local-first model that avoids centralized cost blow-up.
- A universal task execution framework using task graphs.
- Practical constraints and trade-offs for a solo dev.

From here, the next step is to:
1. Implement the data models (tasks, memories, profiles).
2. Build the orchestrator + one sub-agent (Browser Agent with PinchTab).
3. Wire up voice input and a simple memory loop.
4. Iterate in tight loops with real usage.
