# 🛡️ Code Review MCP: Nexus Voice Assistant

**Role:** Senior Architecture Reviewer  
**Context:** Nexus Voice Agent v3 (Autonomous Mode)  
**Engine:** code-review-graph + tRPC + Stream WebRTC

---

## 1. 🏗️ Architecture Analysis (MCP - Map)

The project follows a clean **Modular Context Planning** structure:
- **Core Engine**: `code-review-graph` handles codebase intelligence and wiki generation.
- **Backend Hub**: `backend/voice_agent/` acts as the RTC bridge using `vision_agents`.
- **Frontend Hub**: Next.js + tRPC + Stream SDK for the premium UI.
- **Context Orchestration**: `sync-context.ps1` bridges the intelligence layer with the runtime.

### Current File Splits (SRP Check)
- ✅ `main.py`: Handles Agent lifecycle and RTC events.
- ✅ `providers/stt.py`: Encapsulates Groq Whisper logic.
- ✅ `NexusContext.tsx`: Manages complex RTC state and audio binding.
- ⚠️ `page.tsx`: At 500+ lines, it's nearing the "god file" threshold. UI components (Shell, Tabbed Sidebars) should be extracted.

---

## 2. 🔍 Identified Bugs (The "Brutal Truth")

### A. Voice Loop Failure (Scenario 1)
- **Symptom**: User speaks, but the agent doesn't reply. Transcript doesn't appear in UI.
- **Root Cause**:
    1. **Track Binding Error**: `NexusContext.tsx` uses `call.state.participants$` (Observable) instead of `call.state.participants` (Array) for track selection. This prevents the Agent's audio from being bound to the `<audio>` element.
    2. **Event Payload Mismatch**: In `main.py`, the `@agent.on("transcript")` handler might be receiving the raw text string or an event object. Lack of type checking here is brittle.
    3. **Mic Track Publishing**: Ensure the frontend is actually publishing to the specific `callId` the backend is joined to.

### B. Missing Documentation/Logs
- **Symptom**: User expects "logs and md files" to be created.
- **Observation**: `TRPC_API.md` is created, but `CONTEXT_SUMMARY.md` points to files that might be missing or in different locations.

---

## 3. 🛠️ Implementation Plan (Correction)

### Phase 1: Robust Audio Binding
- Update `NexusContext.tsx` to use stable `call.state.participants`.
- Change `<audio>` element from `display: none` to `opacity: 0` to avoid browser constraints.

### Phase 2: Backend Transparency
- Add `agent_transcript` forwarding to ensure UI shows what the agent *heard*.
- Implement a `ping` system via `send_custom_event` to verify the bridge is active before voice starts.

### Phase 3: UI Component Splitting
- Extract `Shell.tsx` and `InteractionSidebar.tsx` from `page.tsx` to maintain <400 line target.

---

## 4. 📡 tRPC API Review

The tRPC extraction is working well. 
Current endpoints:
- `getSuggestions`: ✅
- `chat`: ✅
- `getVoiceSession`: ✅ (Returns `streamToken` and `callId`)

**Suggestion**: Add a `getSystemHealth` endpoint to report backend process status (VAD latency, LLM connectivity) directly to the UI.
