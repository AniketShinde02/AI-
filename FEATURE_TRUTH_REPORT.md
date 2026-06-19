# NEXUS FEATURE TRUTH REPORT

> Date: 2026-06-17
> Objective: Identify which features are real, partial, or completely mocked.

## Feature Status Matrix

| Feature              | UI Component                                | Backend         | Status            | Notes                                                                                                                      |
| -------------------- | ------------------------------------------- | --------------- | ----------------- | -------------------------------------------------------------------------------------------------------------------------- |
| **Trace**      | `frontend/src/components/SystemTrace.tsx` | `ws_main.py`  | **REAL**    | Listens to actual WebSocket events emitted by the backend agent state.                                                     |
| **Memory**     | `frontend/src/app/memory/page.tsx`        | `GET /memory` | **PARTIAL** | UI fetches from a real endpoint, but the backend is reading from a flat `user_memory.json` file. Needs SQLite migration. |
| **Agents**     | `frontend/src/app/agents/page.tsx`        | *None*        | **MOCK**    | UI renders a hardcoded array (`const AGENTS = [...]`). No API calls are made. No database backing exists.                |
| **Automation** | `frontend/src/app/automation/page.tsx`    | *None*        | **MOCK**    | UI renders a hardcoded array (`const SAMPLE_MISSIONS = [...]`). No workflow execution engine or database exists.         |
| **Dashboard**  | `frontend/src/app/page.tsx`               | `ws_main.py`  | **REAL**    | Voice interface, Chat, and Telemetry are connected to actual backend streams.                                              |

## Next Steps

To remove fake systems from Nexus:	

1. **Agents**: Must be backed by a new SQLite `agents` table.
2. **Automation**: Must be backed by a new SQLite `workflows` table.
3. **Memory**: Must be migrated from JSON to a robust SQLite schema.
