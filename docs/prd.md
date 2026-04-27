# Voice-First AI Assistant PRD

## Document status

Version: 2.0  
Type: Master Product Requirements Document  
Scope: Single-source planning document for early product build  
Intended use: Feed into AI IDE, engineering planning, Excalidraw diagram generation, implementation sequencing

## Purpose of this PRD

This PRD is the primary product document for building a voice-first AI assistant that can listen, reason, ask follow-up questions, execute real tasks in browsers and Windows applications, and later ship as a packaged Windows app with login, account-backed context, and product-grade update flows. A good PRD should define what is being built, why it matters, who it serves, what is in scope, and what success looks like, while keeping supplementary technical detail in structured appendices rather than scattering it across vague notes.[web:100][web:232][web:240]

This document intentionally includes product requirements, feature framing, architecture direction, tool choices, flow definitions, technical boundaries, and Excalidraw prompts in one place because the current goal is to create a strong build-ready source document for AI-assisted development rather than maintain a separate PM-only artifact.[web:232][web:153]

## Product summary

The product is a login-enabled, voice-first AI assistant that uses cloud AI APIs for intelligence and a local Windows execution layer for machine control. It supports voice and text interaction, browser automation, Windows app control, file and utility actions, task clarification, history, account-backed context, and future deep research workflows. It is designed to begin as a cloud-backed product with local execution support and later evolve into a polished Windows application with in-app updates.[cite:164][web:43][web:169]

The product should feel like a practical operator, not a toy chatbot. It must listen in natural language, work across English, Hindi, and Marathi as a product goal, and perform meaningful computer actions rather than only produce chat responses.[web:38][web:223][cite:164]

## Product vision

Build a serious voice-first work assistant that can understand spoken intent, ask smart follow-up questions, operate real websites, control real Windows applications, and generate useful work outputs while remaining architecturally simple enough to ship in roughly 1–2 months for an initial working version.[cite:164][web:43][web:52]

## Problem statement

Users who want a real AI assistant currently have to combine separate tools for speech, browser automation, desktop automation, research, note generation, and memory. Most assistants either converse but cannot act, automate narrowly but cannot carry natural dialogue, or rely too much on local models and overload the user’s machine. This product exists to unify speech-first interaction, cloud reasoning, browser task execution, local PC control, and persistent context in one system.[cite:164][web:43][web:45][web:52]

## Product goals

### Primary goals

- Deliver a voice-first assistant that can understand user intent and complete real tasks.
- Support login-enabled, account-backed usage from early stage.
- Use cloud AI APIs instead of local model-heavy inference.
- Support browser automation on public and logged-in websites.
- Support Windows-local application and utility control.
- Support multilingual speech direction for English, Hindi, and Marathi.
- Create a realistic path to a packaged Windows app with updates later.[cite:164][web:183][web:169]

### Secondary goals

- Support text mode for precision-heavy workflows.
- Support structured markdown outputs for useful work artifacts.
- Introduce deep research mode in a planned way without bloating MVP.
- Build architecture cleanly enough that future scaling does not require rewriting the whole product.[web:100][web:219][web:163]

## Non-goals for MVP

- Fully local AI inference.
- Wake word activation.
- Full cross-platform desktop shipping.
- Team collaboration features.
- Marketplace-style integrations explosion.
- Heavy microservices or Kubernetes-style infra from the start.

## Target users

### Primary user

A Windows-based technical or power user who wants to operate the computer, browser, and assistant workflows through voice and text rather than manually orchestrating many tools. This user values speed, control, real task execution, and cloud intelligence more than consumer-style entertainment UX.[cite:164][cite:21]

### Secondary users

- Solo builders and founders.
- Developers.
- Researchers.
- Operators with repetitive browser and desktop tasks.
- Users who prefer multilingual speech interaction.

## Product principles

### Voice-first, not voice-bolted-on

Voice is a core interaction model. The product should optimize around realtime STT, interruptions, follow-up questioning, and fast responses. Stream Video + Vision Agents is specifically designed for realtime AI agents, including STT/LLM/TTS orchestration, tool use, interruptions, and agent workflows.

### Cloud-first intelligence, local execution only when needed

The main AI reasoning path should use cloud APIs to avoid heavy local laptop load. Local execution should exist only where machine access is required, such as file operations, Windows app control, and device-specific actions.[cite:164]

### Real tool boundaries

The assistant must not fake capabilities. Browser tasks must use browser automation. Windows tasks must use a local Windows agent. Realtime speech must use a dedicated speech stack. This avoids unreliable “pretend agent” behavior and makes failures explainable.[web:43][web:52][web:45]

### Product-ready identity and persistence

Because the long-term goal is a packaged product with stateful accounts, auth and user identity should exist from early stage. Authorization also matters for future MCP-like tool integrations and user-scoped memory/task history.[web:183][web:180]

### Clean architecture over overengineering

The product should avoid both extremes: a chaotic monolith and premature microservices. A modular monolith with strong internal boundaries is the best fit for an evolving product built by a small team or solo builder, while still allowing later extraction if needed.[web:219][web:157][web:159]

## User pain points

| Pain point | Current reality | Product response |
|---|---|---|
| Voice assistants feel slow or dumb | Lag, weak task execution, poor follow-up handling | Realtime voice pipeline + tool use |
| Browser bots are disconnected | Can automate websites but not the full workflow | Integrate browser automation into assistant orchestration [web:43] |
| Desktop automation is separate and brittle | Users need separate scripts/macros/tools | Local Windows agent for task execution [web:52] |
| Context is lost between sessions | Repeating instructions wastes time | Login + task history + memory [web:183][cite:164] |
| Local-only setups are heavy | Laptop gets overloaded | Cloud AI APIs, local execution only where necessary [cite:164] |
| Multilingual spoken interaction is weak | Code-switching and Indian languages are often poor | Prioritize English/Hindi/Marathi support |

## Product scope

### In scope for product direction

- Login and user identity.
- Voice and text interaction.
- Account-backed session history.
- Browser automation on public and logged-in sites.
- Windows app control via local execution layer.
- File and utility actions.
- Clarification questions during tasks.
- Markdown output generation.
- Product-ready packaging path.
- Planned deep research capability.

### Out of scope for initial release

- Wake word.
- Full unattended autonomy with no confirmation for risky actions.
- Multi-user organizations and workspaces.
- Complex billing systems.
- Local-model-first architecture.

## Architecture decision

## Recommended architecture

**Recommended pattern: cloud-backed modular monolith + local Windows agent + browser automation integration**.[web:219][web:159][web:163]

This means:
- one main backend product runtime,
- one main frontend surface,
- one login/auth model,
- one central orchestration layer,
- strong internal modules for sessions, tools, memory, research, tasks, and outputs,
- a separate local Windows companion process for PC access,
- external AI and automation providers connected through adapters.

### Why this is the best fit

A pure monolith is fast initially but can become a tangled god-app. Full microservices improve independent scaling but add deployment, monitoring, coordination, and interface complexity. Modular monolith is the middle path that preserves clean internal boundaries while keeping the first version buildable in a short timeline.[web:219][web:157][web:163]

### Architecture options considered

| Option | Pros | Cons | Fit |
|---|---|---|---|
| Simple monolith | Fastest to start | Can become messy very quickly | Acceptable only if strongly modularized |
| Modular monolith | Balanced complexity, easier shipping, future extraction possible | Requires discipline in boundaries | **Best choice** [web:219][web:157] |
| Microservices | Independent scaling, strong isolation | Too much ops burden for current stage | Not recommended now [web:159][web:163] |
| Event-driven distributed system | Good for high-scale async ecosystems | Extra complexity, not needed yet | Later only |
| Desktop-first everything | Nice packaging story | Slower initial delivery | Better as later packaging layer [web:169] |

## High-level system design

### Main components

1. **Client UI layer**
   - Web app first or app-ready UI structure.
   - Future Windows-packaged shell.
   - Voice controls, task status, chat/history, outputs.

2. **Auth and user identity**
   - User accounts.
   - Session management.
   - User-scoped preferences, memory, history.

3. **Realtime voice layer**
   - Live audio streaming.
   - STT.
   - interrupt handling.
   - turn management.
   - TTS responses.

4. **Agent orchestration layer**
   - Intent understanding.
   - Task decomposition.
   - follow-up questions.
   - tool routing.
   - output composition.

5. **Tool execution layer**
   - Browser automation adapter.[web:43]
   - Windows agent adapter.[web:52]
   - filesystem utilities.
   - future research connectors.

6. **Memory and knowledge layer**
   - session memory.
   - user profile memory.
   - task history.
   - later vector retrieval / knowledge store direction.[web:175][web:178]

7. **Outputs and documents layer**
   - markdown generation.
   - task reports.
   - future export pathways.

8. **Packaging and update path**
   - future Tauri shell.
   - updater support via release endpoints or update service.[web:169][web:170]

## Proposed technology stack

| Layer | Proposed choice | Why |
|---|---|---|
| Frontend | Next.js web app, app-ready structure | Familiar productivity stack, easy to evolve |
| Voice agent runtime | Stream Video + Vision Agents | Realtime voice agent framework, interruptions, tool-friendly |
| STT | Streaming provider (e.g., Deepgram, Soniox) | Streaming STT, multilingual direction |
| LLM | Cloud API model router | Keep heavy inference off laptop |
| TTS | Cloud API provider, pluggable | Better latency/quality flexibility |
| Browser automation | Browser Use | Built for websites accessible to AI agents [web:43] |
| Windows app control | pywinauto-based local agent | Windows GUI automation and control [web:52] |
| Backend | Next.js API Routes (TypeScript) | Co-located with frontend, simpler solo-dev architecture |
| Packaging later | Tauri | Desktop shell + updater path [web:169] |
| DB | relational DB (Neon Postgres) | user data, sessions, tasks, memory |
| Cache / queue | optional later as needed | add only when real async pressure appears |

## Why Next.js primary backend

Next.js is the most practical backbone here because:
- Frontend and backend can be co-located in a single monorepo.
- TypeScript is shared across the stack.
- Stream Video and Stream Chat SDKs have excellent Node.js/React support.
- Agent orchestration can be built iteratively without requiring a heavy Python microservice from day one.
- The local Windows agent (Python) can still exist as a separate process for PC-level control.

This does not prevent a future Tauri desktop shell or a separate background worker; it just keeps the execution brain in the ecosystem that best fits the product’s actual tool needs for speed.

## Core modes

### Mode 1: quick assistant

Short answers, simple actions, quick context.

### Mode 2: voice task mode

Speech-led workflows where the assistant listens, reasons, asks for missing details, and executes.

### Mode 3: browser task mode

Tasks involving websites, navigation, forms, extraction, and logged-in web actions.[web:43]

### Mode 4: PC control mode

Tasks involving Windows apps, folders, typing, utility actions, focus switching, and local machine interactions.[web:52]

### Mode 5: output mode

Structured markdown answers, summaries, task logs, and generated deliverables.

### Mode 6: research mode

Planned deeper retrieval, synthesis, multi-step information gathering, and high-quality output generation.

## Functional requirements

### FR1. Login and identity

The product must support sign-in and user identity from early stage.

Acceptance criteria:
- user can sign up or sign in,
- user session persists securely,
- user history is account-scoped,
- user settings are retrievable,
- future tool permissions can be tied to account identity.

### FR2. Voice-first interface

The product must support voice as a first-class interface using a realtime architecture.

Acceptance criteria:
- user can start a voice interaction session,
- streaming transcription is visible or usable,
- assistant handles interruptions,
- assistant responds with acceptable conversational latency,
- assistant can enter sleep mode on command.

### FR3. Multilingual speech direction

The product must target practical support for English, Hindi, and Marathi speech interaction. Streaming STT providers offer Hindi and Marathi support, making this direction realistic though real-world validation is still required.

Acceptance criteria:
- product can accept English input,
- product can accept Hindi input,
- Marathi direction is tested,
- mixed-language voice scenarios are evaluated.

### FR4. Text mode

The product must support text interaction and preserve shared session context between text and voice.

### FR5. Browser automation

The product must support browser task execution on public and logged-in sites.

Acceptance criteria:
- open website,
- navigate,
- read content,
- click,
- fill forms,
- ask follow-up questions if required inputs are missing,
- explain blocks and failures,
- support back-and-forth during browser tasks.[web:43]

### FR6. Windows app control

The product must support Windows-local actions through a local companion/agent.

Acceptance criteria:
- open app,
- focus app,
- type text,
- perform safe utility operations,
- support guided app interactions where technically feasible,
- require confirmation for sensitive tasks.[web:52]

### FR7. Task clarification and multi-turn execution

The product must ask clarifying questions when task details are incomplete and resume the same task after the answer.

### FR8. Output generation

The product must generate markdown outputs for work products such as summaries, logs, research notes, or reports.

### FR9. Session history and memory

The product must persist user history, task logs, and memory context in an account-scoped manner.

### FR10. Sleep mode

The product must support a voice command to enter sleep mode and require explicit user reactivation.

## Sensitive action policy

The assistant should not silently perform dangerous operations. The product should classify actions into safety bands:

- **Safe**: open app, create folder, search files, read page.
- **Caution**: typing in external apps, editing files, submitting forms.
- **Sensitive**: delete data, send irreversible messages, purchase actions, system configuration changes.

Sensitive actions should require confirmation or explicit user policy approval. This is a product requirement, not optional polish.

## MVP scope

### Must ship in first serious version

- login,
- voice input/output,
- text input/output,
- realtime assistant loop,
- browser task support,
- Windows agent support,
- safe local utilities,
- account-backed history,
- markdown outputs,
- sleep mode,
- basic multilingual validation path.

### Can be limited but planned now

- deep research,
- richer memory retrieval,
- vector retrieval,
- packaged desktop shell,
- in-app updater,
- stronger analytics,
- tool permission dashboards.

## Technical requirements and constraints

### Realtime voice

Stream Video + Vision Agents documents agent workflows for realtime audio/video agents, with integrations for streaming STT. This provides a strong foundation for low-latency voice-first product behavior.

### Browser automation

Browser Use is specifically positioned around making websites accessible to AI agents and supports the kind of web task execution this product needs.[web:43]

### Windows automation

pywinauto provides Windows GUI automation through Win32 and UI Automation access patterns, which aligns with the requirement for local Windows app control.[web:52]

### Packaging and updates

Tauri’s updater path provides a realistic foundation for later Windows desktop packaging and controlled app updates, which supports the long-term product shape without forcing packaging into day-one scope.[web:169][web:170]

## Data and memory direction

A later dedicated schema document can define exact tables, but the PRD needs the system to support at least these logical entities:

- users,
- sessions,
- conversations,
- tasks,
- tool runs,
- outputs,
- preferences,
- memory items,
- future embeddings / vector references.

Vector database and retrieval architecture should be treated as planned later-stage infrastructure, not as an excuse to overcomplicate the first build. Modern RAG and vector architecture guidance generally supports starting simple and evolving retrieval infrastructure based on real use cases rather than speculative complexity.[web:175][web:178]

## Success metrics

### Product success

- user can complete real end-to-end tasks through voice,
- voice interaction feels meaningfully usable,
- browser tasks complete with fewer dead ends,
- Windows actions work reliably for scoped task categories,
- outputs are useful enough to keep using,
- architecture does not require a rewrite immediately.

### Suggested early metrics

- successful completion rate on core browser tasks,
- successful completion rate on core Windows tasks,
- perceived latency satisfaction from the initial user,
- clarification recovery rate,
- repeat usage frequency,
- crash/failure rate by tool type.

## Risks

| Risk | Impact | Response |
|---|---|---|
| Voice latency feels bad | Voice-first proposition collapses | prioritize realtime stack and streaming STT [web:45][web:38] |
| Windows automation unreliability | trust in assistant drops | start with controlled task set and confirmations [web:52] |
| Logged-in automation introduces security risk | user trust and safety issue | explicit permissions and confirmation policy [web:183] |
| Scope explosion | 1–2 month goal breaks | keep MVP narrow but end-to-end |
| Architecture drift | future scaling gets painful | lock modular monolith boundaries now [web:219][web:157] |

## Release strategy

### Release philosophy

Ship a thin but real end-to-end slice first. Do not build isolated subsystems that look impressive in demos but do not connect into one usable product.

### Thin-slice release target

The first meaningful release should support:
1. login,
2. voice session,
3. one fast answer flow,
4. one browser task flow,
5. one Windows task flow,
6. one markdown output flow,
7. task history.

That is enough to prove the product loop without drowning in feature breadth.

## Product dependencies

| Dependency | Role |
|---|---|
| Stream Video + Vision Agents | Realtime voice agent runtime |
| Streaming STT provider(s) | Streaming multilingual STT direction |
| Cloud LLM provider(s) | reasoning, planning, generation |
| TTS provider(s) | spoken output |
| Browser Use | browser execution [web:43] |
| pywinauto or equivalent local Windows layer | Windows app control [web:52] |
| Auth provider / login stack | identity and sessions |
| Relational DB | account, history, tasks |

## Excalidraw prompts

These prompts are intended to help generate product diagrams directly in Excalidraw AI or similar diagramming tools. Excalidraw supports AI-generated architecture diagrams and recommends consistent nodes, colors, and clear structure in prompts.[web:153]

### Prompt 1: Product system architecture diagram

```text
Create a clean software architecture diagram for a voice-first AI assistant product.

Style:
- modern hand-drawn architecture diagram
- clear grouping boxes
- dark text on light background
- use 5 main color groups only
- arrows should show direction of data flow
- keep labels short but technical

Show these groups from left to right:

1. User Interfaces
- Voice UI
- Text Chat UI
- Future Windows Desktop App Shell

2. Client and Session Layer
- Session State
- Auth Client
- Task Timeline UI
- Settings UI

3. Core Cloud Backend (grouped as modular monolith)
Inside this box show modules:
- API Gateway
- Auth and User Identity
- Conversation Orchestrator
- Voice Session Manager
- Tool Router
- Task Manager
- Memory Service
- Output Generator
- Research Orchestrator
- Audit and Logs

4. External AI and Tool Providers
- STT Provider
- LLM Provider Router
- TTS Provider
- Browser Automation (Browser Use)

5. Local Windows Companion
- Local Agent API
- Windows App Controller
- File and Folder Tools
- Input Automation Layer
- Safety and Permissions Layer

6. Data Layer
- Relational Database
- Future Vector Store
- Object Storage / Output Files

7. Future Delivery Layer
- Tauri Desktop Shell
- Updater Service

Arrows:
- User Interfaces to Core Cloud Backend
- Voice UI to STT and TTS through Voice Session Manager
- Tool Router to Browser Automation
- Tool Router to Local Windows Companion
- Core Cloud Backend to Data Layer
- Future Tauri Desktop Shell connects to Client and Local Windows Companion
- Updater Service connects to Tauri Desktop Shell

Add one note on the diagram:
"Recommended architecture: cloud-backed modular monolith + local Windows agent"
```

### Prompt 2: Voice and task flow diagram

```text
Create a workflow diagram for a voice-first AI assistant handling real tasks.

Style:
- workflow / flowchart
- decision diamonds for branching
- consistent rectangles for processing steps
- soft neutral colors
- include failure and clarification paths

Flow:
1. User speaks request
2. Audio stream starts
3. Speech-to-text streaming
4. Intent and task classification
5. Decision: simple answer or tool task?
6. If simple answer -> generate response -> text + voice output -> save history
7. If tool task -> decision: browser task, Windows task, research task, or mixed task
8. Decision: is information missing?
9. If yes -> ask follow-up question -> wait for user answer -> resume task
10. If browser task -> send to browser automation -> collect result
11. If Windows task -> send to local Windows agent -> collect result
12. If research task -> run research workflow -> generate markdown output
13. Merge task results
14. Generate final response
15. Save session, task log, and memory
16. Return text + optional voice response

Show error branches:
- browser blocked
- app control failed
- missing permissions
- user confirmation required

Add a small side note:
"Sleep mode can pause voice handling until manual reactivation"
```

### Prompt 3: Modular monolith internal structure diagram

```text
Create an internal architecture diagram of a modular monolith backend for a voice-first AI assistant.

Style:
- technical architecture diagram
- one large box representing the modular monolith
- inner modules with arrows between them
- separate external systems outside the box

Inside the modular monolith box include:
- API Layer
- Auth Module
- Session Module
- Conversation Orchestrator
- Voice Module
- Tool Routing Module
- Browser Task Module
- Windows Task Adapter Module
- Research Module
- Memory Module
- Output Module
- Audit / Logging Module

Outside the box include:
- Client App
- STT Provider
- TTS Provider
- LLM Router
- Browser Use
- Local Windows Agent
- Database
- Vector Store (future)
- Object Storage

Show:
- API Layer entry point
- Conversation Orchestrator coordinating Voice, Tool Routing, Research, Memory, and Output
- Browser Task Module calling Browser Use
- Windows Task Adapter calling Local Windows Agent
- Memory Module using Database and future Vector Store
- Output Module writing generated markdown to Object Storage

Add a footer label:
"Chosen over microservices for faster delivery and lower operational complexity in early stage"
```

### Prompt 4: Product mode map

```text
Create a capability map diagram for a voice-first AI assistant.

Center node: Voice-First AI Assistant

Around it place six mode clusters:
- Quick Answer Mode
- Voice Task Mode
- Browser Automation Mode
- Windows Control Mode
- Output Generation Mode
- Research Mode

For each mode show 3 to 5 child capabilities.
Examples:
Quick Answer Mode -> factual answers, clarifications, summaries
Voice Task Mode -> listen, interrupt, ask follow-up, respond
Browser Automation Mode -> navigate, fill forms, extract data, logged-in tasks
Windows Control Mode -> open apps, focus windows, type text, create folders
Output Generation Mode -> markdown docs, reports, summaries, logs
Research Mode -> gather sources, synthesize, structure output

Use colored clusters and arrows from the center node.
Add one side note:
"All modes share identity, memory, task history, and tool permissions"
```

## Open decisions still acknowledged inside PRD

The PRD is intentionally strong, but a few implementation details still require later decision-making:

- final frontend packaging timing,
- exact auth provider,
- exact DB selection,
- exact LLM/TTS provider mix,
- exact permission UX for sensitive actions,
- exact retrieval stack timing for deep research.

These do not block the product direction or architecture choice. They are implementation-level decisions, not reasons to keep the PRD vague.

## Final product statement

This product should be built as a login-enabled, cloud-backed, voice-first AI assistant with a modular monolith core, a local Windows execution agent, browser automation integration, multilingual speech direction, markdown output generation, and a clear path to future Windows packaging and updates. That is the most realistic architecture and product scope for shipping something useful fast without painting the system into a corner.[web:219][web:169]
