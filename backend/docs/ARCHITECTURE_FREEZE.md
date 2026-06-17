# NEXUS 2.0 ARCHITECTURE FREEZE

> Status: FROZEN  
> Date: 2026-06-17  
> Objective: Protect the core architectural boundaries of the Nexus Desktop AI OS.  
> Mandate: No future feature may bypass these boundaries without a formal architecture review.

---

## 1. Core Engine
- **Responsibility**: Bootstrapping, session management, and routing.
- **Boundaries**: 
  - The Core Engine must remain a thin orchestrator. It delegates to specialized services (Voice, Tools, Memory) rather than handling logic directly.
  - Must operate strictly over `localhost` or Unix domain sockets. No public exposure.

## 2. Voice Pipeline
- **Responsibility**: Audio ingestion, VAD (Voice Activity Detection), STT (Speech-to-Text), LLM routing, and TTS (Text-to-Speech).
- **Boundaries**:
  - Voice pipeline operates exclusively on a streaming WebSocket layer.
  - Providers (Groq, EdgeTTS, Gemini) must implement the standard Provider abstract interface.
  - Fallback logic (e.g., Groq to Gemini) is handled at the provider router level, not inside the core WS loop.

## 3. Memory System
- **Responsibility**: Long-term state persistence across sessions.
- **Boundaries**:
  - Memory is extracted asynchronously after conversation turns (not in the critical response path).
  - Storage is exclusively via **SQLite (WAL Mode)**. `user_memory.json` is deprecated.
  - Facts, preferences, and goals are isolated into specific tables and injected into the LLM context dynamically.

## 4. Agent System
- **Responsibility**: Execution of persona-driven, tool-enabled tasks.
- **Boundaries**:
  - Agents are instantiated dynamically from the SQLite `agents` registry.
  - Agents are constrained by a strict `allowed_tools` list.
  - Agent state (active, idle, suspended) is persisted to SQLite to survive application restarts.

## 5. Tool Registry
- **Responsibility**: Secure execution of system and external capabilities.
- **Boundaries**:
  - Tools must define strict inputs and outputs (Zod/Pydantic schemas).
  - The registry acts as the sole executor. The LLM cannot bypass the registry to run raw code.
  - Scrapper OS and other external systems are registered here as Bridge Tools.

## 6. Theme Engine
- **Responsibility**: Visual presentation of the application.
- **Boundaries**:
  - Purely CSS-variable and token-driven. 
  - Themes may control colors, typography, layout density, and motion.
  - Themes may **NOT** control API calls, WS logic, memory, or database logic.
  - All UI components must consume from the Theme Provider, no hardcoded colors permitted.

## 7. Storage Layer
- **Responsibility**: Safe, concurrent persistence of all application state.
- **Boundaries**:
  - **SQLite (WAL mode)**: Sole authority for chats, sessions, memory, agents, and workflows.
  - **LanceDB**: Sole authority for embeddings (RAG/Knowledge).
  - **Local Filesystem**: Read-only operations for user documents (PDFs, codebases). Never modify original user files.
  - **JSON**: Allowed only for simple configuration and API key storage (which must be encrypted or rely on OS keystores).
