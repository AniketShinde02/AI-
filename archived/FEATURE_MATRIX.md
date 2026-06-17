# Nexus Feature Matrix

| Feature | Status | Notes |
|---------|--------|-------|
| **Voice** | Partially Implemented / Broken | Uses WebSocket for streaming. Multiple TTS providers exist (Gemini, Edge, Kokoro remnants). Subject to crashes if interface contracts mismatch (e.g. `dict` vs `PcmData`). |
| **Chat** | Implemented | Fully functional via Next.js frontend (`app/chat`) and REST/WS. |
| **Memory** | Partially Implemented | Database models exist (`core/memory.py`), frontend page exists (`app/memory`), but full integration is incomplete. |
| **Agents** | Experimental | Frontend page exists (`app/agents`), but routing and orchestration logic is basic. |
| **Automation** | Experimental | Frontend page exists (`app/automation`), backend hooks are not fully fleshed out. |
| **Browser** | Experimental | Basic web search tools exist in `third_party_tools.py`. Playwright MCP plugin installed but not fully integrated into core loop. |
| **Vision** | Experimental | `vision_agents` directory exists, but not wired into the main WebSocket stream. |
| **Desktop Control** | Implemented (IRIS-AI) | Exists in `IRIS-AI-main/src/main/logic/telekinesis.ts` and `ghost-control.ts`. Not unified with Nexus web backend. |
| **Files** | Implemented | Robust file tools exist in `backend/voice_agent/tools/file_tools.py`. |
| **Tools** | Implemented | `system.py`, `third_party_tools.py`, `task_tools.py` exist and function. |
| **Research** | Implemented (IRIS-AI) | `deep-research.ts` exists in the Electron app. |
| **Code Generation** | Implemented (IRIS-AI) | `iris-coder.ts` exists in the Electron app. |
| **Settings** | Implemented | Dedicated frontend page (`app/settings`) controlling Voice Studio and agent personas. |
| **Profiles** | Dead Code / Missing | No dedicated multi-user profile abstraction found. |
| **Personalization** | Dead Code / Missing | Static prompt injection exists, but dynamic personalization memory is rudimentary. |
| **Model Routing** | Implemented | `tts_router.py` actively routes between Gemini and Edge TTS. |
| **RAG** | Partially Implemented | `RAG-oracle.ts` exists in IRIS-AI, and SQLite local vector stores exist, but fragmented. |
