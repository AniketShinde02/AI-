# Nexus V1 — Production State Manual

## 1. System Overview

Nexus V1 is a multi-modal desktop assistant capable of orchestrating web navigation, desktop applications, user memory, and file operations.
The architecture strictly enforces an **Observe-Decide-Execute-Verify** cycle for deterministic, safe, and verifiable operation.

## 2. Core Architecture

The architecture relies on stable, non-experimental foundations:

1. **WorkspaceManager**
   The sole source of truth for environmental context. Maintains `DesktopContext`, `BrowserContext`, `MemoryContext`, `ProviderContext`, and `ExecutionContext`. Fully thread-safe, utilizing TTL caches for real-time reactivity without state collisions.

2. **Action Router**
   A two-tiered routing engine. Utilizes `ModelRouter` for multi-provider fast-routing (Groq, Cerebras, Mistral, Gemini, OpenRouter) to semantically map user intentions to `capability_registry_def.py` tools.

3. **PlannerCompiler**
   Transforms complex natural language goals into a Directed Acyclic Graph (DAG) of capability tools. Supports dependencies, parallel nodes, and strict error bubbling.

4. **Execution Engine & Domain Executors (V1.6)**
   Executes tasks using `executor.py`. Procedural hooks have been replaced by object-oriented Domain Executors (`DesktopExecutor`, `BrowserExecutor`, `VisionExecutor`, `MemoryExecutor`, etc.). Each executor implements a standard contract wrapping execution with:
   - **Pre-flight**: Broadcasts state to `WorkspaceManager`.
   - **Retry**: Exponential backoff self-healing loops inside the executor.
   - **Validation**: Contract validation and non-blocking DB writes for verification.
   - **Isolation**: Providers (LLMs) supply reasoning, Executors perform deterministic work.

## 3. Capability Scope (35 Tools)

Nexus V1 ships with a validated library of 35 core capabilities across domains:
- **Desktop**: App management, Window control, OS manipulation (Clipboard, Explorer, Shortcuts).
- **Browser**: Playwright-based autonomous navigation, extraction, forms, Search, Tab control.
- **Vision**: OCR and Screen analysis via multimodal prompts.
- **Memory**: LanceDB integrated Task/Notes creation and Scrapper OS triggers.
- **Planner**: `run_task_card` preconfigured automation pipelines.

*(See `/docs/skills/` for detailed definitions).*

## 4. Verification & Safety

No raw tool executes blindly. Nexus relies on empirical evidence:
- **Visual Verification**: Screenshots confirm UI interactions.
- **Process Verification**: `psutil` confirms app states.
- **DOM Verification**: State matching ensures browser actions completed successfully.

## 5. Deployment & Reliability

Nexus V1 is certified Production Ready with >95% routing success rates, resilient state management, and strict isolation of runtime context. Architecture is intentionally frozen; future updates focus exclusively on prompt engineering, latency optimization, and capability plugins.
