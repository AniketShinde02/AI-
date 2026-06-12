# Project Structure

## Root
- `run.ps1`: Unified startup script for Windows.
- `CHANGELOG.md`: Project evolution tracking.
- `.planning/`: GSD workflow state and codebase mapping.

## Backend (`backend/voice_agent/`)
- `main.py`: Entry point, FastAPI server, and agent session logic.
- `providers/`: Custom provider implementations (LLM, STT, TTS).
  - `llm.py`: Groq streaming implementation.
- `core/`: Orchestration logic (CallManager, Concurrency).
- `venv/`: Local Python dependencies.

## Frontend (`frontend/`)
- `src/app/`: Next.js App Router (Layouts, Pages).
- `src/components/`: UI elements.
  - `InputArea.tsx`: Chat and Voice control.
  - `ChatArea.tsx`: Message display.
- `src/contexts/`: Global state (NexusContext).
- `src/lib/`: Utilities and API clients (tRPC).
