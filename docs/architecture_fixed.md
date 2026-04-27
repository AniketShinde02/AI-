# Voice-First AI Assistant Architecture Document

## Document status

Version: 2.0  
Type: Software Architecture Document (SAD)  
Scope: Early-stage, implementation-guiding architecture for a voice-first AI assistant with cloud-backed intelligence and local Windows execution.

> **v2.0 Change:** Voice stack updated from LiveKit + Soniox → **GetStream Video + Vision Agents + Deepgram**. All references corrected. `nexus-2-architecture-v2.md` is the canonical master blueprint; this document is the implementation-level architecture reference. Both are now consistent.

This document follows a pragmatic version of common architecture documentation patterns: it covers context, logical architecture, process/flow, deployment, data and integration views, plus concrete prompts for architecture diagrams in Excalidraw.[web:245][web:247][web:243]

## 1. Architecture goals and constraints

### 1.1 Primary goals

- Enable a **voice-first, login-enabled assistant** that can execute real work tasks in browsers and Windows applications using cloud AI APIs and a local execution layer.[cite:164]
- Keep the architecture **simple enough** for a 1–2 month initial build by a solo developer, while avoiding traps that make future scaling impossible.[web:219][web:157]
- Support **public and logged-in website automation**, **Windows app control**, and **multilingual speech** (English, Hindi, Marathi direction) without requiring heavy local model inference.[web:43][web:52][web:38][web:223]
- Preserve a clean path to a **packaged Windows application with auto-updates** via Tauri later, without forcing desktop packaging into day-one scope.[web:169][web:170]

### 1.2 Key constraints

- Cloud AI models will be used for reasoning and generation; no heavy local LLMs.
- Windows is the primary desktop OS for local control.
- Architecture must support login and per-user context from early versions.
- Logged-in website automation and desktop control are allowed but must be governed by a clear safety/confirmation layer.

## 2. High-level architecture summary

### 2.1 Architecture pattern

The system is designed as a **cloud-backed modular monolith** with:

- a single primary backend application (Python), implemented as internal modules for sessions, orchestration, tools, memory, and outputs;[web:219][web:157]
- a separate **local Windows agent** process for PC and app control;[web:52]
- a **browser automation integration** (Browser Use) for web tasks;[web:43]
- a **realtime voice stack** built using GetStream Video + Vision Agents with Deepgram as STT;
- a **web/app UI** (Next.js) that will later be wrapped in a Windows application shell (Tauri) with updater support.[web:169][web:170]

This pattern is chosen over microservices to keep deployment and operational complexity manageable while still supporting clear boundaries between modules.[web:219][web:159][web:243]

### 2.2 Major components

1. **Client layer**  
   - Web UI (Next.js)  
   - Future Windows desktop app shell (Tauri)

2. **Realtime voice and session layer**  
   - GetStream Video + Vision Agents-based service handling STT (Deepgram), LLM routing, TTS, interruptions, and audio streaming sessions.

3. **Core backend (modular monolith)**  
   - Auth and user identity  
   - Conversation orchestrator  
   - Tool router  
   - Task manager  
   - Memory service  
   - Output generator  
   - Research orchestrator  
   - Audit/logging

4. **Tool execution layer**  
   - Browser automation adapter (Browser Use)  
   - Local Windows agent adapter (HTTP/WebSocket)  
   - Future research connectors (search, document stores)

5. **Local Windows agent**  
   - Local HTTP/WebSocket server  
   - Windows automation (pywinauto / input automation)  
   - File and folder utilities  
   - Safety/confirmation policies

6. **Data and storage layer**  
   - Relational DB (users, sessions, tasks, memory)  
   - Future vector store  
   - Object storage (markdown outputs, logs)

7. **Future packaging and updates**  
   - Tauri shell wrapping the web UI  
   - Tauri updater configuration with signed releases and update endpoints.[web:169][web:170]

## 3. Context view

### 3.1 External systems and dependencies

| System | Role in architecture |
|---|---|
| GetStream Video Cloud | Realtime audio sessions, WebRTC multiplexing, STT/LLM/TTS pipeline entry via Vision Agents. |
| Deepgram STT | Streaming multilingual speech-to-text for Hindi, Marathi, English; integrated via GetStream Vision Agents plugin. $200 free credit on signup. |
| LLM provider(s) | Cloud reasoning and generation for intent, planning, responses. |
| TTS provider(s) | Cloud text-to-speech for audible responses. |
| Browser Use | Browser automation engine controlled by the tool router for web tasks.[web:43] |
| Local Windows OS | Host for the local agent, running Windows apps to be controlled. |
| Auth/email provider | Handles auth flows (email login or OAuth) for user identity. |
| Storage/DB provider | Runs relational DB, object storage for outputs, optional vector DB later.[web:175][web:178] |

### 3.2 High-level data flow

At a high level, the flow is:

1. User speaks or types a request in the client UI.
2. Voice requests are streamed to GetStream Video; Deepgram handles STT via the Vision Agents framework, and the transcribed text is forwarded to the orchestrator.
3. The conversation orchestrator in the backend interprets intent and decides whether the request is:
   - conversational answer,
   - browser task,
   - Windows task,
   - research task,
   - or a combination.
4. The tool router calls Browser Use, the local Windows agent, or research workflows.
5. Tool outputs are fed back into the orchestrator.
6. The orchestrator produces a final response (text + voice) and updates memory/history.
7. The client displays results and plays audio.

## 4. Logical architecture view

### 4.1 Core backend modules (modular monolith)

Within the main backend application, modules are separated by responsibility.

- **API Layer**  
  HTTP/WebSocket entry point for the client. Handles authentication, routing, and request validation.

- **Auth & Identity Module**  
  User accounts, sessions, tokens. Ties user identity to memory, task history, tool permissions, and future MCP-like integrations.[web:183][web:180]

- **Conversation Orchestrator**  
  Central coordinator for conversation and task flows. Receives STT text and text inputs, manages turn state, tracks active tasks, and calls the tool router and output generator.

- **Voice Session Manager**  
  Manages mapping between GetStream Video sessions and backend user sessions. Coordinates with Vision Agents callbacks and TTS responses.

- **Tool Router**  
  Enforces a single interface by which the orchestrator calls tools. Tools include:
  - browser_task,
  - windows_task,
  - research_task,
  - file_task,
  - utility_task.

- **Browser Task Module**  
  Encapsulates Browser Use integration. Accepts high-level task specs, prepares prompts and state for the Browser Use agent, and interprets returned actions/results.[web:43]

- **Windows Task Adapter Module**  
  Encapsulates communication with the local Windows agent.
  - Handles request encoding (e.g., JSON over HTTP/WebSocket).
  - Enforces policy (which tasks are allowed, which require confirmation).
  - Normalizes responses from the local agent.

- **Research Module**  
  Orchestrates multi-step research tasks and uses tooling for web search and retrieval. Handles longer-running jobs and often writes full markdown outputs.

- **Memory Module**  
  Manages user profile memory, session memory, and long-term knowledge references. Future versions integrate with vector stores for semantic retrieval.[web:175][web:178]

- **Output Module**  
  Responsible for generating structured markdown documents, summaries, logs, and attaching them to tasks. Outputs are stored in object storage.

- **Audit & Logging Module**  
  Central logging for tool calls, errors, performance metrics, and user-facing logs.

### 4.2 Local Windows agent modules

The local Windows agent runs as a separate process on the user’s Windows machine.

- **Local Agent API**  
  Lightweight HTTP or WebSocket server that receives commands from the backend via a secure channel.

- **Windows App Controller**  
  Uses pywinauto and related libraries to launch apps, focus windows, interact with dialogs and controls, and send keyboard/mouse events.[web:52]

- **File & Folder Tools**  
  Provides operations like create folder, rename, move, copy, delete (with policy), and file inspection.

- **Input Automation Layer**  
  Handles typing sequences and advanced input actions (e.g., paste content, navigation shortcuts) in a controlled way.

- **Safety & Permissions Layer**  
  Enforces local policies: denies or requires confirmation for sensitive actions such as destructive changes, sending messages, or system configuration changes.

### 4.3 Browser automation module

- **Browser Use Integration**  
  The backend integrates Browser Use as a service (local or cloud) by passing high-level tasks with user goals and constraints. The automation framework navigates, clicks, fills, and scrapes pages.[web:43]

- **Task Translator**  
  Converts natural-language tasks into structured Browser Use goals.

- **Result Interpreter**  
  Converts Browser Use’s output (DOM content, extracted data) into summarizable content and tool results for the orchestrator.

## 5. Process / sequence view

### 5.1 Voice-driven browser task sequence

Example: *“Open my Gmail and summarize the last 5 unread emails.”*

1. User speaks the request in the UI.
2. Audio is streamed over GetStream Video (WebRTC).
3. Deepgram via Vision Agents converts audio to streaming text.
4. Vision Agents forwards transcribed text to the backend conversation orchestrator.
5. Orchestrator classifies this as a browser task with logged-in context.
6. Orchestrator checks user identity and permissions.
7. Tool router triggers Browser Use with a structured task:
   - open Gmail,
   - ensure logged-in state,
   - read last 5 unread emails,
   - return subject + preview text.
8. Browser Use performs actions and returns results.[web:43]
9. Orchestrator generates summary text.
10. Output module may generate a markdown summary.
11. TTS converts summarised response to audio.
12. UI plays audio and displays summary.
13. Memory and task history are updated.

### 5.2 Voice-driven Windows task sequence

Example: *“Create a folder called ‘Client Reports’ on the desktop and open it.”*

1. User speaks the request.
2. GetStream Video + Deepgram pipeline produces text and sends to backend.
3. Orchestrator classifies this as a Windows task.
4. Tool router sends a command to Windows Task Adapter.
5. Windows Task Adapter issues a `create_folder` command to the Local Agent API.
6. Local agent’s File & Folder Tools create the folder and return success.
7. Local agent’s Windows App Controller opens a file explorer window pointing to that folder.
8. Backend returns confirmation message.
9. TTS plays confirmation, UI shows task log.

### 5.3 Clarification / follow-up flow

When required parameters are missing (e.g., which email account, which app, which file), the orchestrator must:

1. Recognize the missing information.
2. Ask a clarifying question back via voice/text.
3. Wait for user response.
4. Merge the new details into the task.
5. Continue the same task flow.

## 6. Deployment view

### 6.1 Environments

- **Local machine (Windows)**  
  - Local Windows agent process  
  - Future Tauri shell  
  - Browser and apps under control

- **Cloud environment**  
  - Core backend modular monolith  
  - GetStream Video Cloud (managed, no self-hosting required)  
  - Browser Use deployment (self-hosted or managed)  
  - Relational DB  
  - Object storage  
  - Future vector DB  
  - Monitoring/logging stack

### 6.2 Communication channels

- Client ↔ Backend API: HTTPS.
- Client ↔ GetStream Video: WebRTC / WebSocket.
- GetStream ↔ Backend: Vision Agents SDK / WebSocket callbacks.
- Backend ↔ Browser Use: HTTP/WS API.[web:43]
- Backend ↔ Local Windows Agent: secure channel (tunnel/WebSocket) initiated from local machine.
- Backend ↔ DB: private network.
- Backend ↔ STT/LLM/TTS: HTTPS.

## 7. Data view (high level)

### 7.1 Main data entities

- **User**  
  id, auth fields, preferences, permissions.

- **Session**  
  session id, user id, active mode, timestamps.

- **Conversation turn**  
  session id, user message, assistant message, timestamps, metadata.

- **Task**  
  id, user id, type (browser, windows, research, mixed), status, inputs, outputs.

- **Tool run**  
  task id, tool type, parameters, result, error state.

- **Memory item**  
  user id, type, content, importance, embeddings (future), references.

- **Output document**  
  id, user id, task id, markdown content location, creation date.

These entities will be elaborated in a separate DB schema document; the architecture document only needs to describe relationships at a high level.[web:245]

## 8. Technology choices and justification

### 8.1 Voice stack: GetStream Video + Vision Agents + Deepgram

- GetStream Video + Vision Agents is the chosen realtime voice stack. It handles WebRTC sessions, STT/LLM/TTS pipeline orchestration, interruption handling, and agent lifecycle — no self-hosted signalling server required.
- Deepgram provides streaming multilingual STT (English, Hindi, Marathi) via the Vision Agents plugin. $200 free credit on signup; latency and accuracy outperform alternatives at this price point.
- **Free tier math:** GetStream free tier = ~333,000 participant-minutes/month. Solo dev usage = 8 h × 60 min × 30 days = **14,400 min/month**. That is 4.3% of the free tier. GetStream covers solo development + early beta users with massive headroom — zero voice infrastructure cost until real scale.

### 8.2 Browser automation: Browser Use

- Browser Use targets exactly the problem of making websites accessible to AI agents and allowing them to execute tasks. Reusing this instead of writing custom Playwright/Selenium glue fits the “assemble, don’t reinvent” strategy.[web:43]

### 8.3 Windows automation: pywinauto local agent

- pywinauto provides programmatic Windows GUI automation using Win32 and UI Automation drivers, which enables app launching, focusing, clicking, and text entry. This aligns with the requirement to operate Windows apps and utilities from the assistant.[web:52]

### 8.4 Packaging and updater: Tauri

- Tauri v2’s updater plugin supports configuring update endpoints and signed releases, enabling automatic updates for packaged desktop apps. Designing with this in mind now keeps a clean path for future Windows packaging without forcing Tauri into MVP implementation.[web:169][web:170]

## 9. Security and safety considerations (architecture level)

### 9.1 Identity and authorization

- All tasks must be associated with an authenticated user.
- Tool permissions (browser, Windows, research) should be configurable per user.
- Future MCP-like integrations require adherence to authorization best practices: tokens must be audience-restricted, short-lived, and validated by servers before tool use.[web:183][web:180]

### 9.2 Sensitive actions

- The Windows agent must enforce local checks before destructive or irreversible actions.
- The backend must enforce confirmation flows for sensitive tool types (send message, delete data, etc.).

### 9.3 Data handling

- Browser automation should avoid storing unnecessary raw content and focus on derived summaries and task outcomes.
- Voice audio may be streamed but not stored by default unless explicitly needed for debugging.

## 10. Frontend performance & delivery architecture

### 10.1 SPA with virtual DOM

- The client is a **single-page application (SPA)** built with Next.js (React). Rendering uses React's virtual DOM; only components whose state or props change will re-render.
- Navigation uses client-side routing (Next.js Router) so page transitions do not require full HTML loads. Network calls are only for data, not markup.
- This approach minimizes DOM operations and provides snappy UI updates, matching patterns used in large-scale applications (Facebook, Instagram, Twitter).

### 10.2 Aggressive caching & network hygiene

- All static assets (JS, CSS, images, fonts) are served via a CDN with long-lived `Cache-Control` headers (e.g., 1 year) and content-hashed filenames for immutable caching.
- API endpoints specify `Cache-Control` and `ETag` headers; the client respects caching and avoids refetching unchanged data (304 Not Modified responses).
- Total HTTP requests are minimized by bundling, compressing assets (gzip/brotli), and eliminating unnecessary third-party scripts.
- A service worker (PWA-style) caches the application shell and critical API responses for instant reloads and offline resilience where applicable.

### 10.3 Request management: debounce, throttle, cancellation

- User-driven API calls (search inputs, filter changes) are **debounced** (300–500 ms wait after last keystroke) to avoid flooding the backend.
- Repeated event handlers (scroll, resize) are **throttled** to fire at most once per configured interval.
- All in-flight requests use `AbortController`; obsolete or superseded requests are cancelled to prevent race conditions and wasted work.
- Polling is used sparingly; real-time features rely on websockets/streams instead.

### 10.4 API layer: single source of truth

- All network access goes through a **typed API client** combined with a query layer (TanStack Query / React Query).
- The query layer provides **request deduplication** (multiple components requesting the same data share a single network call), caching, retries, and background refetching.
- Components never call `fetch` directly; they consume data through the query client.
- List endpoints enforce **pagination and lazy loading** (cursor/offset); no API returns unbounded result sets.

### 10.5 Real-time updates via streaming

- Real-time data (chat messages, call state, AI streaming tokens) is delivered over persistent connections:
  - WebSockets for bidirectional updates (chat, agent status).
  - Server-Sent Events (SSE) for server-to-client streams (LLM tokens, progress).
  - Streaming HTTP responses for AI generation where appropriate.
- Polling is avoided for real-time features; HTTP is reserved for initial loads and non-real-time actions.

### 10.6 Feature flags & remote configuration

- All non-trivial features are guarded by **remote feature flags** (Firebase Remote Config or custom service).
- New features ship "dark" (code present but disabled); flags control visibility and behavior per user/segment.
- This enables **staged rollouts** (5% → 50% → 100%), instant rollback without app-store releases, and server-driven UI/behavior tuning.
- Feature flags also guard experiments and A/B tests, keeping the release process safe and reversible.

### 10.7 Component-level performance practices

- Components are kept small and focused; state is lifted only as high as needed to minimize re-render scope.
- Expensive subtrees are memoized (`React.memo`, `useMemo`, `useCallback`) to avoid unnecessary re-renders.
- Keys are stable and unique; prop changes are minimized where possible.
- DOM complexity is monitored; deeply nested structures and excessive node counts are avoided to keep layout/paint fast.

### 10.8 Frontend asset strategy

- Build pipeline outputs **minified, tree-shaken bundles** with code splitting. Non-critical routes and components are lazy-loaded.
- **Critical path assets** are preloaded; above-the-fold content is prioritized.
- Images are compressed and served in modern formats (WebP/AVIF); icons use SVG sprites or icon fonts.
- HTTP/2+ is used for multiplexing; assets are served with optimal cache headers via CDN.

### 10.9 Performance rules checklist

> - SPA with virtual DOM; no full page reloads for navigation.
> - All network calls go through a cached, deduped API client; pagination is mandatory for lists.
> - User-driven calls are debounced; in-flight requests are cancelled via `AbortController`.
> - Real-time features use websockets/streams, not polling.
> - Feature flags + remote config control rollouts; no big-bang releases.
> - Assets are bundled, minified, cached, and served via CDN with long TTLs.

## 10. Excalidraw prompts for diagrams

The following prompts are designed for Excalidraw AI’s text-to-diagram feature, following its recommendations to use clear groupings, limited color palettes, and understandable labels.[web:153][web:252]

### 10.1 System architecture diagram

```text
Create a software architecture diagram for a voice-first AI assistant.

Style:
- hand-drawn Excalidraw style
- soft colors, limited palette (5 colors max)
- clear grouping boxes for layers
- arrows showing main data flow

Groups and elements:

Client Layer:
- Web UI (Next.js)
- Future Windows App Shell (Tauri)

Voice and Session Layer:
- GetStream Video + Vision Agents
- Deepgram STT (via Vision Agents)
- TTS Provider (OpenAI TTS / ElevenLabs)

Core Backend (Modular Monolith):
- API Layer
- Auth & Identity
- Conversation Orchestrator
- Voice Session Manager
- Tool Router
- Browser Task Module
- Windows Task Adapter
- Research Module
- Memory Module
- Output Module
- Audit & Logs

Tool & Provider Layer:
- Browser Use
- LLM Provider
- STT Provider (Deepgram)
- TTS Provider

Local Windows Agent:
- Local Agent API
- Windows App Controller (pywinauto)
- File & Folder Tools
- Safety & Permissions

Data Layer:
- Relational DB
- Future Vector Store
- Object Storage (markdown outputs)

Future Delivery:
- Tauri Updater Service

Arrows:
- Client -> API Layer
- Voice UI -> GetStream Video + Vision Agents -> Conversation Orchestrator
- Tool Router -> Browser Use
- Tool Router -> Local Windows Agent
- Core Backend -> Data Layer
- Tauri Shell <-> Client Layer and Local Windows Agent

Add footer note:
"Architecture: cloud-backed modular monolith + local Windows agent + browser automation"
```

### 10.2 Voice and task flow diagram

```text
Create a flowchart for a voice-first AI assistant executing tasks.

Style:
- flowchart with rectangles and diamonds
- horizontal layout
- small labels on arrows

Steps:
1. User speaks request
2. Audio streamed to GetStream Video
3. Deepgram STT converts to text (via Vision Agents)
4. Conversation Orchestrator receives text
5. Decision: simple answer or task? (diamond)
6a. Simple answer -> generate answer -> send to TTS + UI -> save history
6b. Task -> classify task type (browser, Windows, research, mixed)
7. Decision: is information missing? (diamond)
8a. If missing -> ask clarification -> user reply -> go back to classification
8b. If complete -> route to appropriate tool:
   - Browser Use
   - Local Windows Agent
   - Research workflow
9. Tool executes and returns result
10. Orchestrator merges results and context
11. Output Module generates markdown if needed
12. Final response -> TTS + UI -> history and memory update

Include error paths:
- Browser blocked or login failure
- Windows action denied by permissions
- LLM error -> fallback message

Add side note:
"Sleep mode: gate at step 1; ignore audio when sleep is active"
```

### 10.3 Deployment diagram

```text
Create a deployment diagram for the voice-first AI assistant.

Style:
- boxes for nodes
- labels for processes inside nodes
- arrows for network connections

Nodes:
- User Device (Windows)
  - Web UI / App Shell
  - Local Windows Agent
  - Browser and Apps

- Cloud Backend
  - Modular Monolith Backend
  - Relational DB
  - Object Storage
  - Logging / Monitoring

- GetStream Video Cloud
  - Vision Agents (managed, no self-host)

- Browser Automation Cluster
  - Browser Use Service

- AI Providers
  - STT Provider (Deepgram)
  - LLM Provider
  - TTS Provider

Connections:
- User Device <-> Cloud Backend (HTTPS)
- User Device <-> GetStream Video (WebRTC/WebSocket)
- Cloud Backend <-> GetStream (Vision Agents SDK connection)
- Cloud Backend <-> Browser Use (HTTPS or WebSocket)
- Cloud Backend <-> AI Providers (HTTPS)
- Cloud Backend <-> DB and Storage (private network)
- Cloud Backend <-> User Device Local Agent (secure WebSocket or tunnel)

Add small notes on arrows with protocols where relevant.
```

## 11. Open architecture questions

- Which relational database (e.g., Postgres vs. others) is chosen for the first build.
- Which specific LLM and TTS providers are used initially.
- Exact mechanism for secure communication between backend and local Windows agent (direct WebSocket vs. relay service).
- ~~Voice infrastructure provider~~ — **Resolved:** GetStream Video + Vision Agents (cloud-managed). No self-hosting required.

These details can be filled in as implementation decisions while preserving the architecture described above.

---

This architecture document should now be kept in sync with the PRD and used as a reference while building feature specs, DB schema, and the AI context file.
