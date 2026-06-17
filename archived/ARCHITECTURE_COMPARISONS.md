# Cross-Repository Architecture Comparisons

This document compares the current architecture of Nexus against three reference implementations: **IRIS-AI**, **Stonic-AI**, and **Hermes Agent**. The goal is to identify architectural patterns, mistakes to avoid, and features worth transplanting.

## 1. Hermes Agent (The Headless Brain)
**Paradigm**: Pure Python 3.11, Headless, Modular, Multi-Interface.

### Core Strengths
* **Headless Decoupling**: Hermes separates the core "Agent Loop" (`hermes_state.py`, `run_agent.py`) from the frontend interfaces. The `gateway/` architecture allows the exact same AI brain to interact via CLI, Telegram, Discord, Slack, etc., without altering the core logic.
* **State-of-the-Art Package Management**: Uses `uv` (Rust-based) for lightning-fast, reproducible dependency management via `uv.lock` and `pyproject.toml`.
* **Universal Context Protocol (MCP)**: Implements Model Context Protocol (`mcp_serve.py`), enabling secure, standardized connections to arbitrary local data sources (files, databases, GitHub).
* **Local Persistence**: Bypasses heavy cloud databases for long-term memory, utilizing local Markdown (`SOUL.md`, `MEMORY.md`) and a local SQLite database with Full Text Search (FTS5).
* **Sub-Agent Orchestration**: `batch_runner.py` allows spawning isolated background processes for parallel task delegation without blocking the primary conversation loop.

### Learnings for Nexus
1. **Adopt the Headless Core**: Nexus should solidify `ws_main.py` into a pure, headless engine, totally independent of the Next.js frontend.
2. **Implement MCP**: Adopting the Model Context Protocol will allow Nexus to interface with local files, codebases, and databases without writing custom, brittle tools for every integration.
3. **Migrate to `uv`**: Replace `pip` with `uv` in the backend to dramatically reduce installation times and Docker build costs, enforcing strict locking.

---

## 2. IRIS-AI (The Native Desktop App)
**Paradigm**: Electron, Node.js, Vite, Native-First.

### Core Strengths
* **Deep OS Integration**: Direct access to local OS APIs (`telekinesis.ts`, `ghost-control.ts`) allows IRIS to manipulate desktop windows and accessibility trees natively.
* **Dedicated RAG Oracle**: Centralized `RAG-oracle.ts` abstraction providing focused retrieval mechanisms.
* **Deep Research**: Built-in, multi-step autonomous research loops (`deep-research.ts`).

### Learnings for Nexus
1. **RAG Centralization**: Nexus currently relies on fragmented vector databases; it should adopt a dedicated Oracle pattern.
2. **Avoid Native Monoliths**: IRIS bundles heavy native Node modules and UI logic in the Electron main process, making it difficult to deploy to the cloud. Nexus successfully decouples Voice into a dedicated Python WebSocket backend; this decoupling must be preserved.
3. **Telekinesis via Daemon**: Instead of making Nexus a heavy Electron app, create an optional "Nexus Companion Daemon" (derived from IRIS's Telekinesis) that runs locally while the Nexus brain stays in the cloud.

---

## 3. Stonic-AI (The Prototype Node Wrapper)
**Paradigm**: Javascript/Electron UI wrappers around basic API calls.

### Core Strengths
* **Quick Prototyping**: Fast time-to-market using pre-built web technologies wrapped in Electron.

### Learnings for Nexus
1. **Language Choice**: Python is the industry standard for AI. Hermes proves that a pure Python backend is infinitely more capable of integrating PyTorch, Pandas, ML pipelines, and local AI models than Node.js (which Stonic relies heavily upon). Nexus's current use of FastAPI/Python is the correct path and should not revert to a Node-based AI core.
2. **Avoid Shallow Wrappers**: Stonic's architecture lacked a deep reasoning loop, acting more as a shallow API pass-through. Nexus must focus on the deeper "Agent Loop" demonstrated by Hermes (`hermes_state.py`) to achieve autonomy.

---

## Final Verdict for Nexus Evolution
To achieve a production-grade, state-of-the-art system, **Nexus must merge its existing Web/Cloud strengths with Hermes's Headless Python Architecture.** 

1. Refactor `ws_main.py` using the **Hermes Gateway pattern** to fully separate the WebSocket transport layer from the core Agent loop.
2. Introduce **Model Context Protocol (MCP)** support to standardize tool access.
3. Move away from raw `pip` to **`uv`** for all Python dependencies.
4. If desktop control is ever needed, deploy a lightweight local Daemon (learning from IRIS), while keeping the core intelligence inside the Python backend.
