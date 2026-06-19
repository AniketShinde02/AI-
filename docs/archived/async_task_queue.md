# Nexus 2.0 — Async Task Queue

**Version:** 1.0  
**Last Updated:** 2025  
**Stack:** FastAPI + Inngest + Supabase Postgres + SSE (sse-starlette) + Next.js

---

## Table of Contents

1. [Why Async Is Non-Negotiable](#1-why-async-is-non-negotiable)
2. [Architecture Overview](#2-architecture-overview)
3. [Inngest Setup with FastAPI](#3-inngest-setup-with-fastapi)
4. [Task Functions](#4-task-functions)
5. [Task State Machine](#5-task-state-machine)
6. [SSE for Real-time Status](#6-sse-server-sent-events-for-real-time-status)
7. [Event Payload Schemas](#7-event-payload-schemas)
8. [Error Handling & Dead Letter Queue](#8-error-handling--dead-letter-queue)
9. [Local Development Flow](#9-local-development-flow)

---

## 1. Why Async Is Non-Negotiable

### The Problem with Synchronous Task Execution

A naive implementation of Nexus would look like this:

```python
@router.post("/tasks/browser")
async def create_browser_task(body: CreateBrowserTaskRequest):
    result = await execute_browser_task(body.goal)  # blocks for up to 5 minutes
    return result
```

This will fail in production in multiple ways:

| Issue | Impact |
|---|---|
| HTTP connection timeout | Railway/Vercel/proxies default to 30–60s request timeout. Browser tasks take 30s–5min. The connection dies. |
| User stares at a spinner | No feedback during execution. User thinks it's frozen and refreshes (or leaves). |
| No retry capability | If the task crashes halfway, there's no way to retry without losing state. |
| Cannot scale | One long-running task blocks an entire ASGI worker slot. |
| Mobile/battery/network | User closes the app. Task is gone. |

### Task Duration Reality Check

| Task Type | Typical Duration | 99th Percentile |
|---|---|---|
| Windows control (open app, move file) | 1–5 seconds | 15 seconds |
| Browser automation (simple form fill) | 5–30 seconds | 2 minutes |
| Browser automation (multi-step research) | 30s–3 minutes | 5 minutes |
| Research mode (web + synthesis) | 2–5 minutes | 10 minutes |
| Memory extraction (post-session) | 10–45 seconds | 2 minutes |

Only Windows control tasks are fast enough to be tolerable synchronously, and even those should be async for architectural consistency. Once you have one async task type, make them all async — the consistency is worth more than the minor overhead.

### The Async Architecture Solves All of This

- **No HTTP timeouts:** The endpoint returns `202 Accepted` with a `task_id` in under 100ms.
- **Real-time feedback:** SSE stream sends `task.step_completed` events as the task progresses.
- **Durable execution:** Inngest stores the event and function state. If the worker crashes, it retries from the last checkpoint.
- **Scalable:** Inngest manages concurrency, rate limiting, and backpressure automatically.
- **Client-disconnection safe:** The task runs to completion regardless of whether the frontend is connected.

---

## 2. Architecture Overview

### Full Request Lifecycle

```
┌──────────────────────────────────────────────────────────────────────┐
│                          CLIENT (Next.js)                            │
│  1. POST /api/v1/tasks/browser                                       │
│     { goal: "Book a flight to NYC", url: "google.com/flights" }      │
└──────────────────────┬───────────────────────────────────────────────┘
                       │ HTTP POST
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       FastAPI Endpoint                               │
│  2. Validate request + check quota (see monetization_model.md)       │
│  3. Create task row in Supabase: { status: "pending", id: "abc123" } │
│  4. Send Inngest event: nexus/task.browser.requested                 │
│  5. Return 202: { task_id: "abc123", stream_url: "/tasks/abc123/stream" } │
└──────────────────────┬───────────────────────────────────────────────┘
                       │ inngest.send(event)
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      Inngest Cloud / Dev Server                      │
│  6. Receives event, routes to matching function                      │
│  7. Respects priority field (free=0, pro=5, power=10)                │
│  8. Picks up by available worker slot                                │
└──────────────────────┬───────────────────────────────────────────────┘
                       │ HTTP POST to /api/inngest
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    Inngest Worker (FastAPI process)                  │
│  9.  Update task status: pending → queued → running                  │
│  10. Execute task in steps:                                          │
│       step.run("launch-browser") → update DB                        │
│       step.run("navigate-to-url") → update DB                       │
│       step.run("execute-goal")   → update DB                        │
│       step.run("capture-result") → update DB                        │
│  11. Update task status: running → completed (or failed)             │
│  12. Send nexus/usage.increment event                                │
└──────────────────────┬───────────────────────────────────────────────┘
                       │ DB update triggers SSE
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     SSE Stream (FastAPI)                             │
│  GET /api/v1/tasks/abc123/stream                                     │
│  13. Polls DB for task updates every 500ms (or uses PG LISTEN/NOTIFY)│
│  14. Sends SSE events to connected frontend:                         │
│       event: task.queued      → { status: "queued" }                │
│       event: task.started     → { status: "running" }               │
│       event: task.step        → { step: "navigate-to-url", ... }    │
│       event: task.completed   → { result: {...}, status: "completed" }│
└──────────────────────┬───────────────────────────────────────────────┘
                       │ EventSource messages
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                          CLIENT (Next.js)                            │
│  15. Updates Agent Trace UI with live step progress                  │
│  16. Shows completion with result / error                            │
└──────────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

**Why Inngest over Celery/RQ/BullMQ?**
- Inngest is cloud-hosted — zero Redis/RabbitMQ infra to maintain
- Free tier (100k events/month) is sufficient for early-stage Nexus
- Built-in: retries, dead letter queue, rate limiting, step checkpointing, priority
- Excellent developer experience with local dev server and function replay UI
- Works natively with FastAPI via its Python SDK

**Why SSE over WebSockets?**
- SSE is one-directional (server → client), which is all we need for task status
- Works over standard HTTP/2 with no protocol upgrade
- Simpler to implement, no connection management complexity
- Vercel edge network handles SSE efficiently

---

## 3. Inngest Setup with FastAPI

### Installation

```bash
pip install inngest
# In requirements.txt:
inngest==0.4.0
```

### InngestClient Initialization

```python
# services/inngest_client.py

import inngest
from app.core.config import settings

inngest_client = inngest.Inngest(
    app_id="nexus-backend",
    api_key=settings.INNGEST_EVENT_KEY,      # Send events from FastAPI
    signing_key=settings.INNGEST_SIGNING_KEY, # Verify requests from Inngest cloud
    is_production=settings.ENVIRONMENT == "production",
    logger=None,  # Will use default Python logging
)
```

### Mount Inngest in FastAPI App

```python
# main.py

from fastapi import FastAPI
from inngest.fast_api import serve
from services.inngest_client import inngest_client
from services.inngest_functions import (
    handle_browser_task,
    handle_windows_task,
    handle_research_task,
    handle_memory_extract,
    handle_usage_increment,
    check_plan_expirations,
)

app = FastAPI(title="Nexus 2.0 API", version="2.0.0")

# Mount Inngest endpoint — Inngest cloud POSTs to /api/inngest to invoke functions
serve(
    app,
    inngest_client,
    functions=[
        handle_browser_task,
        handle_windows_task,
        handle_research_task,
        handle_memory_extract,
        handle_usage_increment,
        check_plan_expirations,
    ],
    serve_path="/api/inngest",  # URL that Inngest will call
)

# Include other routers
from app.api.v1 import tasks, users, billing
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(billing.router, prefix="/api/v1")
```

### Environment Variables

```bash
# .env

# Inngest
INNGEST_EVENT_KEY=evt_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
INNGEST_SIGNING_KEY=signkey-prod-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# In local dev, these aren't needed — dev server auto-configures
# INNGEST_DEV_SERVER_URL=http://localhost:8288
```

---

## 4. Task Functions

### 4.1 Browser Task Function

Browser tasks are the most complex — they control a headless browser, may span multiple pages, and need step-level checkpointing to survive retries without restarting from scratch.

```python
# services/inngest_functions/browser_task.py

import inngest
from datetime import datetime
from services.inngest_client import inngest_client
from app.db.session import get_async_db_session
from app.models.task import Task, TaskStatus
from app.services.browser_agent import BrowserAgent
from sqlalchemy import text


@inngest_client.create_function(
    fn_id="nexus/browser-task",
    trigger=inngest.TriggerEvent(event="nexus/task.browser.requested"),
    retries=2,
    timeout="10m",
    priority=inngest.Priority(run="event.data.priority"),
    rate_limit=inngest.RateLimit(
        limit=10,
        period="1m",
        key="event.data.user_id",  # Per-user rate limit: 10 browser tasks/min max
    ),
)
async def handle_browser_task(ctx: inngest.Context, step: inngest.Step) -> dict:
    """
    Execute a browser automation task for the user.

    Event: nexus/task.browser.requested
    Payload: BrowserTaskEventData (see section 7)

    Steps:
      1. Mark task as running in DB
      2. Initialize browser agent
      3. Execute goal (may involve multiple sub-steps)
      4. Capture result
      5. Mark task as completed
      6. Track usage
    """
    data = ctx.event.data
    task_id:  str = data["task_id"]
    user_id:  str = data["user_id"]
    goal:     str = data["goal"]
    url:      str | None = data.get("url")
    priority: int = data.get("priority", 0)
    timeout:  int = data.get("timeout_seconds", 600)

    # ── Step 1: Mark as running ──────────────────────────────────────────────
    async def _mark_running():
        async with get_async_db_session() as db:
            await db.execute(
                text("""
                    UPDATE tasks
                    SET status = 'running', started_at = NOW(), updated_at = NOW()
                    WHERE id = :task_id
                """),
                {"task_id": task_id},
            )
            await db.commit()
        return {"status": "running"}

    await step.run("mark-running", _mark_running)

    # ── Step 2: Launch browser ───────────────────────────────────────────────
    async def _launch_browser():
        # BrowserAgent manages Playwright lifecycle
        # Returns serializable session config (not the agent object itself)
        agent = BrowserAgent(timeout_seconds=timeout)
        session_id = await agent.start()
        return {"session_id": session_id}

    browser_config = await step.run("launch-browser", _launch_browser)
    session_id = browser_config["session_id"]

    # ── Step 3: Navigate to starting URL (if provided) ───────────────────────
    if url:
        async def _navigate():
            agent = BrowserAgent.from_session(session_id)
            await agent.navigate(url)
            return {"navigated_to": url}

        await step.run("navigate-to-url", _navigate)

    # ── Step 4: Execute goal (LLM-driven browser automation) ─────────────────
    async def _execute_goal():
        agent = BrowserAgent.from_session(session_id)
        result = await agent.execute_goal(
            goal=goal,
            user_context=data.get("user_context"),
            max_steps=20,
        )
        return {
            "success": result.success,
            "summary": result.summary,
            "screenshots": result.screenshot_urls,
            "steps_taken": result.steps_taken,
            "data_extracted": result.data_extracted,
        }

    execution_result = await step.run("execute-goal", _execute_goal)

    # ── Step 5: Cleanup browser ──────────────────────────────────────────────
    async def _cleanup():
        agent = BrowserAgent.from_session(session_id)
        await agent.close()
        return {"closed": True}

    await step.run("cleanup-browser", _cleanup)

    # ── Step 6: Mark completed in DB ─────────────────────────────────────────
    async def _mark_completed():
        async with get_async_db_session() as db:
            await db.execute(
                text("""
                    UPDATE tasks SET
                        status       = 'completed',
                        result       = :result,
                        completed_at = NOW(),
                        updated_at   = NOW()
                    WHERE id = :task_id
                """),
                {
                    "task_id": task_id,
                    "result":  execution_result,
                },
            )
            await db.commit()
        return {"completed": True}

    await step.run("mark-completed", _mark_completed)

    # ── Step 7: Track usage ──────────────────────────────────────────────────
    await step.send_event(
        "track-usage",
        inngest.Event(
            name="nexus/usage.increment",
            data={"user_id": user_id, "metric": "browser_task", "task_id": task_id},
        ),
    )

    # ── Step 8: Trigger memory extraction ────────────────────────────────────
    await step.send_event(
        "extract-memory",
        inngest.Event(
            name="nexus/session.memory.extract",
            data={"user_id": user_id, "task_id": task_id, "summary": execution_result.get("summary")},
        ),
    )

    return execution_result
```

### 4.2 Windows Task Function

Windows tasks are fast (<5s typically) but still benefit from async execution for consistency and retry capability.

```python
# services/inngest_functions/windows_task.py

@inngest_client.create_function(
    fn_id="nexus/windows-task",
    trigger=inngest.TriggerEvent(event="nexus/task.windows.requested"),
    retries=1,   # Windows tasks are idempotent — retry once on failure
    timeout="30s",
    priority=inngest.Priority(run="event.data.priority"),
)
async def handle_windows_task(ctx: inngest.Context, step: inngest.Step) -> dict:
    """
    Execute a Windows control task (open app, move file, control UI, etc.)

    Event: nexus/task.windows.requested
    Payload: WindowsTaskEventData (see section 7)
    """
    data = ctx.event.data
    task_id:  str = data["task_id"]
    user_id:  str = data["user_id"]
    command:  str = data["command"]
    context:  dict = data.get("context", {})

    async def _mark_running():
        async with get_async_db_session() as db:
            await db.execute(
                text("UPDATE tasks SET status='running', started_at=NOW() WHERE id=:id"),
                {"id": task_id},
            )
            await db.commit()

    await step.run("mark-running", _mark_running)

    async def _execute_windows_command():
        from app.services.windows_agent import WindowsAgent
        agent = WindowsAgent()
        result = await agent.execute(command=command, context=context)
        return {
            "success":       result.success,
            "action_taken":  result.action_taken,
            "output":        result.output,
            "screenshot_url": result.screenshot_url,
        }

    result = await step.run("execute-command", _execute_windows_command)

    async def _mark_completed():
        status = "completed" if result["success"] else "failed"
        async with get_async_db_session() as db:
            await db.execute(
                text("""
                    UPDATE tasks SET
                        status = :status, result = :result,
                        completed_at = NOW(), updated_at = NOW()
                    WHERE id = :task_id
                """),
                {"status": status, "result": result, "task_id": task_id},
            )
            await db.commit()

    await step.run("mark-completed", _mark_completed)

    if result["success"]:
        await step.send_event(
            "track-usage",
            inngest.Event(
                name="nexus/usage.increment",
                data={"user_id": user_id, "metric": "task_run", "task_id": task_id},
            ),
        )

    return result
```

### 4.3 Research Task Function

Research tasks are the longest-running and most resource-intensive. They use multiple steps with explicit checkpointing.

```python
# services/inngest_functions/research_task.py

@inngest_client.create_function(
    fn_id="nexus/research-task",
    trigger=inngest.TriggerEvent(event="nexus/task.research.requested"),
    retries=1,
    timeout="15m",
    priority=inngest.Priority(run="event.data.priority"),
    concurrency=inngest.Concurrency(
        limit=3,
        key="event.data.user_id",  # Max 3 research tasks per user at once
    ),
)
async def handle_research_task(ctx: inngest.Context, step: inngest.Step) -> dict:
    """
    Execute a deep research task: web search, content extraction, synthesis.

    Event: nexus/task.research.requested
    Payload: ResearchTaskEventData (see section 7)
    """
    data = ctx.event.data
    task_id:   str = data["task_id"]
    user_id:   str = data["user_id"]
    query:     str = data["query"]
    depth:     str = data.get("depth", "basic")  # "basic" (Pro) | "full" (Power)
    languages: list = data.get("languages", ["en"])

    await step.run("mark-running", lambda: _update_task_status(task_id, "running"))

    # ── Step: Plan the research ───────────────────────────────────────────────
    async def _plan_research():
        from app.services.research_agent import ResearchAgent
        agent = ResearchAgent(depth=depth, languages=languages)
        plan = await agent.create_research_plan(query)
        return {"queries": plan.queries, "sources_to_visit": plan.sources}

    plan = await step.run("plan-research", _plan_research)

    # ── Step: Gather sources ──────────────────────────────────────────────────
    async def _gather_sources():
        from app.services.research_agent import ResearchAgent
        agent = ResearchAgent(depth=depth, languages=languages)
        sources = await agent.gather_sources(
            queries=plan["queries"],
            max_sources=10 if depth == "basic" else 25,
        )
        return {"sources": [s.dict() for s in sources]}

    sources_result = await step.run("gather-sources", _gather_sources)

    # ── Step: Synthesize findings ─────────────────────────────────────────────
    async def _synthesize():
        from app.services.research_agent import ResearchAgent
        agent = ResearchAgent(depth=depth, languages=languages)
        synthesis = await agent.synthesize(
            query=query,
            sources=sources_result["sources"],
        )
        return {
            "report":     synthesis.report,
            "sources":    synthesis.cited_sources,
            "confidence": synthesis.confidence_score,
        }

    final_result = await step.run("synthesize-findings", _synthesize)

    async def _save_result():
        async with get_async_db_session() as db:
            await db.execute(
                text("""
                    UPDATE tasks SET
                        status='completed', result=:result,
                        completed_at=NOW(), updated_at=NOW()
                    WHERE id=:task_id
                """),
                {"result": final_result, "task_id": task_id},
            )
            await db.commit()

    await step.run("save-result", _save_result)

    await step.send_event(
        "track-usage",
        inngest.Event(
            name="nexus/usage.increment",
            data={"user_id": user_id, "metric": "research_task", "task_id": task_id},
        ),
    )

    return final_result
```

### 4.4 Memory Extraction Function

Runs after each session ends to extract and store durable memory about the user's preferences, ongoing tasks, and context.

```python
# services/inngest_functions/memory_extract.py

@inngest_client.create_function(
    fn_id="nexus/memory-extract",
    trigger=inngest.TriggerEvent(event="nexus/session.memory.extract"),
    retries=2,
    timeout="2m",
    debounce=inngest.Debounce(
        key="event.data.user_id",
        period="30s",  # Wait 30s after last event before extracting (batch session end)
    ),
)
async def handle_memory_extract(ctx: inngest.Context, step: inngest.Step) -> dict:
    """
    Extract memory from a completed task session.
    Debounced per user — multiple rapid tasks batch into one extraction.

    Event: nexus/session.memory.extract
    """
    data = ctx.event.data
    user_id: str = data["user_id"]
    task_id: str = data["task_id"]
    summary: str | None = data.get("summary")

    async def _extract_and_store():
        from app.services.memory_service import MemoryService
        svc = MemoryService(user_id=user_id)
        memories = await svc.extract_from_task(
            task_id=task_id,
            summary=summary,
        )
        stored_count = await svc.store(memories)
        return {"memories_extracted": stored_count}

    result = await step.run("extract-memory", _extract_and_store)
    return result
```

---

## 5. Task State Machine

### States and Valid Transitions

```
                    ┌─────────────────────────────────────┐
                    │              PENDING                 │
                    │  (task created, event not yet sent   │
                    │   or Inngest hasn't picked it up)    │
                    └──────────────┬──────────────────────┘
                                   │ Inngest picks up event
                                   ▼
                    ┌─────────────────────────────────────┐
                    │              QUEUED                  │
                    │  (Inngest received event, function   │
                    │   waiting for worker slot)           │
                    └──────────────┬──────────────────────┘
                                   │ Worker starts execution
                                   ▼
                    ┌─────────────────────────────────────┐
                    │              RUNNING                 │
                    │  (function actively executing steps) │
                    └──────┬───────────────────┬──────────┘
                           │ success            │ error / exception
                           ▼                   ▼
              ┌────────────────────┐   ┌────────────────────┐
              │     COMPLETED      │   │       FAILED       │
              │  (result stored,   │   │  (error stored,    │
              │   usage tracked)   │   │   retries exhausted│
              └────────────────────┘   │   or no retries)   │
                                       └─────────┬──────────┘
                                                 │ if retries remain
                                                 ▼
                                       ┌────────────────────┐
                                       │    RUNNING (retry) │
                                       │  (Inngest auto-    │
                                       │   retries with     │
                                       │   backoff)         │
                                       └────────────────────┘

              CANCELLED: can transition from PENDING or QUEUED only
              (cannot cancel a running task mid-execution)
```

### Python Enum and Transition Guard

```python
# app/models/task.py

from enum import Enum
from typing import ClassVar


class TaskStatus(str, Enum):
    PENDING   = "pending"
    QUEUED    = "queued"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"


# Valid state transitions (current → allowed next states)
VALID_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING:   {TaskStatus.QUEUED,   TaskStatus.CANCELLED},
    TaskStatus.QUEUED:    {TaskStatus.RUNNING,  TaskStatus.CANCELLED, TaskStatus.FAILED},
    TaskStatus.RUNNING:   {TaskStatus.COMPLETED, TaskStatus.FAILED},
    TaskStatus.COMPLETED: set(),   # Terminal state
    TaskStatus.FAILED:    set(),   # Terminal state
    TaskStatus.CANCELLED: set(),   # Terminal state
}


def validate_transition(
    current: TaskStatus,
    next_status: TaskStatus,
) -> None:
    """Raises ValueError if the transition is not valid."""
    allowed = VALID_TRANSITIONS.get(current, set())
    if next_status not in allowed:
        raise ValueError(
            f"Invalid task status transition: {current} → {next_status}. "
            f"Allowed: {allowed}"
        )
```

### Tasks DB Table

```sql
-- supabase/migrations/20250101000003_create_tasks.sql

CREATE TABLE IF NOT EXISTS tasks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type            VARCHAR(20) NOT NULL
                    CHECK (type IN ('browser', 'windows', 'research', 'memory')),
    status          VARCHAR(20) NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'queued', 'running',
                                      'completed', 'failed', 'cancelled')),
    goal            TEXT NOT NULL,              -- user's natural language request
    result          JSONB,                      -- task output, null until completed
    error_message   TEXT,                       -- set on failure
    inngest_event_id VARCHAR(100),              -- for replay/debugging
    priority        INTEGER NOT NULL DEFAULT 0, -- 0=free, 5=pro, 10=power
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_tasks_user_status ON tasks(user_id, status);
CREATE INDEX IF NOT EXISTS idx_tasks_user_created ON tasks(user_id, created_at DESC);

-- task_steps table for granular trace UI
CREATE TABLE IF NOT EXISTS task_steps (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id     UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    step_name   VARCHAR(100) NOT NULL,
    status      VARCHAR(20) NOT NULL DEFAULT 'pending',
    started_at  TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    output      JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_task_steps_task ON task_steps(task_id, created_at);
```

---

## 6. SSE (Server-Sent Events) for Real-time Status

### Why SSE

The frontend needs live updates as a task progresses through steps. SSE is the right tool:
- Unidirectional (server → client only — that's all we need)
- Works over standard HTTP/1.1 and HTTP/2
- No WebSocket handshake overhead
- EventSource API is built into all modern browsers
- Automatic reconnection built into the browser spec

### FastAPI SSE Implementation

```python
# app/api/v1/tasks.py

import asyncio
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}/stream")
async def stream_task_status(
    task_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventSourceResponse:
    """
    SSE endpoint for real-time task status updates.

    Client connects here immediately after submitting a task.
    Stream closes automatically when task reaches a terminal state
    (completed, failed, cancelled).

    Events emitted:
      - task.queued        → { status: "queued" }
      - task.started       → { status: "running", started_at: "..." }
      - task.step          → { step_name: "...", status: "running|completed|failed" }
      - task.completed     → { result: {...}, completed_at: "..." }
      - task.failed        → { error: "...", retrying: false }
      - task.heartbeat     → {} (every 15s to keep connection alive)
    """

    # Verify the task belongs to this user
    result = await db.execute(
        text("SELECT id, user_id FROM tasks WHERE id = :task_id"),
        {"task_id": task_id},
    )
    task_row = result.fetchone()
    if not task_row or str(task_row.user_id) != str(user.id):
        raise HTTPException(404, "Task not found")

    async def event_generator():
        last_step_count = 0
        last_status = None
        heartbeat_counter = 0

        while True:
            # Fetch current task state
            result = await db.execute(
                text("""
                    SELECT status, result, error_message, started_at, completed_at
                    FROM tasks WHERE id = :task_id
                """),
                {"task_id": task_id},
            )
            task = result.fetchone()

            if not task:
                yield {"event": "error", "data": json.dumps({"error": "task_not_found"})}
                break

            current_status = task.status

            # Emit status change events
            if current_status != last_status:
                if current_status == "queued":
                    yield {
                        "event": "task.queued",
                        "data": json.dumps({"status": "queued", "task_id": task_id}),
                    }
                elif current_status == "running":
                    yield {
                        "event": "task.started",
                        "data": json.dumps({
                            "status": "running",
                            "started_at": task.started_at.isoformat() if task.started_at else None,
                        }),
                    }
                elif current_status == "completed":
                    yield {
                        "event": "task.completed",
                        "data": json.dumps({
                            "status": "completed",
                            "result": task.result,
                            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                        }),
                    }
                    break  # Terminal — close stream
                elif current_status == "failed":
                    yield {
                        "event": "task.failed",
                        "data": json.dumps({
                            "status": "failed",
                            "error": task.error_message,
                            "retrying": False,
                        }),
                    }
                    break  # Terminal — close stream
                elif current_status == "cancelled":
                    yield {"event": "task.cancelled", "data": json.dumps({"status": "cancelled"})}
                    break

                last_status = current_status

            # Emit new step events
            steps_result = await db.execute(
                text("""
                    SELECT step_name, status, started_at, completed_at, output
                    FROM task_steps
                    WHERE task_id = :task_id
                    ORDER BY created_at ASC
                    OFFSET :offset
                """),
                {"task_id": task_id, "offset": last_step_count},
            )
            new_steps = steps_result.fetchall()
            for step in new_steps:
                yield {
                    "event": "task.step",
                    "data": json.dumps({
                        "step_name":    step.step_name,
                        "status":       step.status,
                        "started_at":   step.started_at.isoformat() if step.started_at else None,
                        "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                        "output":       step.output,
                    }),
                }
                last_step_count += 1

            # Heartbeat every 15s to prevent proxy timeout
            heartbeat_counter += 1
            if heartbeat_counter >= 30:  # 30 * 500ms = 15s
                yield {"event": "task.heartbeat", "data": json.dumps({"ts": datetime.utcnow().isoformat()})}
                heartbeat_counter = 0

            await asyncio.sleep(0.5)  # Poll every 500ms

    return EventSourceResponse(event_generator())
```

### React Frontend: EventSource

```typescript
// hooks/useTaskStream.ts

import { useEffect, useState, useRef } from "react";

type TaskStep = {
  step_name: string;
  status: "pending" | "running" | "completed" | "failed";
  output?: Record<string, unknown>;
  started_at?: string;
  completed_at?: string;
};

type TaskStreamState = {
  status: "pending" | "queued" | "running" | "completed" | "failed" | "cancelled";
  steps: TaskStep[];
  result?: Record<string, unknown>;
  error?: string;
};

export function useTaskStream(taskId: string | null) {
  const [state, setState] = useState<TaskStreamState>({
    status: "pending",
    steps: [],
  });
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!taskId) return;

    // Close any existing stream
    esRef.current?.close();

    const es = new EventSource(`/api/v1/tasks/${taskId}/stream`, {
      withCredentials: true,
    });
    esRef.current = es;

    es.addEventListener("task.queued", () => {
      setState(s => ({ ...s, status: "queued" }));
    });

    es.addEventListener("task.started", () => {
      setState(s => ({ ...s, status: "running" }));
    });

    es.addEventListener("task.step", (event: MessageEvent) => {
      const step: TaskStep = JSON.parse(event.data);
      setState(s => ({
        ...s,
        steps: [
          ...s.steps.filter(x => x.step_name !== step.step_name),
          step,
        ],
      }));
    });

    es.addEventListener("task.completed", (event: MessageEvent) => {
      const data = JSON.parse(event.data);
      setState(s => ({ ...s, status: "completed", result: data.result }));
      es.close();
    });

    es.addEventListener("task.failed", (event: MessageEvent) => {
      const data = JSON.parse(event.data);
      setState(s => ({ ...s, status: "failed", error: data.error }));
      es.close();
    });

    es.addEventListener("task.cancelled", () => {
      setState(s => ({ ...s, status: "cancelled" }));
      es.close();
    });

    es.onerror = () => {
      // Browser will auto-reconnect on transient errors
      // EventSource spec: reconnects after 3s by default
      console.warn("SSE connection error, browser will retry...");
    };

    return () => {
      es.close();
    };
  }, [taskId]);

  return state;
}
```

### Usage in React Component

```tsx
// components/TaskExecutionPanel.tsx

import { useTaskStream } from "@/hooks/useTaskStream";

export function TaskExecutionPanel({ taskId }: { taskId: string }) {
  const { status, steps, result, error } = useTaskStream(taskId);

  return (
    <div className="task-panel">
      <TaskStatusBadge status={status} />
      <div className="step-trace">
        {steps.map(step => (
          <StepRow key={step.step_name} step={step} />
        ))}
      </div>
      {status === "completed" && <TaskResult result={result} />}
      {status === "failed" && <TaskError error={error} />}
    </div>
  );
}
```

---

## 7. Event Payload Schemas

All Inngest events use strongly-typed Pydantic models. These are also used to validate outbound events before sending.

```python
# app/schemas/inngest_events.py

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from typing import Optional


# ── Browser Task ──────────────────────────────────────────────────────────────

class BrowserTaskEventData(BaseModel):
    task_id:         str
    user_id:         str
    goal:            str  = Field(..., min_length=1, max_length=2000)
    url:             Optional[str] = None
    user_context:    Optional[str] = None   # persistent memory context
    priority:        int = Field(default=0, ge=0, le=10)
    timeout_seconds: int = Field(default=600, ge=10, le=900)
    plan:            str = Field(default="free")  # for logging/metrics


class BrowserTaskEvent(BaseModel):
    name: str = "nexus/task.browser.requested"
    data: BrowserTaskEventData


# ── Windows Task ──────────────────────────────────────────────────────────────

class WindowsTaskEventData(BaseModel):
    task_id:         str
    user_id:         str
    command:         str  = Field(..., min_length=1, max_length=1000)
    context:         dict = Field(default_factory=dict)   # screen state, open apps
    priority:        int  = Field(default=0, ge=0, le=10)
    timeout_seconds: int  = Field(default=30, ge=5, le=300)
    plan:            str  = Field(default="free")


class WindowsTaskEvent(BaseModel):
    name: str = "nexus/task.windows.requested"
    data: WindowsTaskEventData


# ── Research Task ─────────────────────────────────────────────────────────────

class ResearchTaskEventData(BaseModel):
    task_id:         str
    user_id:         str
    query:           str  = Field(..., min_length=1, max_length=2000)
    depth:           str  = Field(default="basic")  # "basic" | "full"
    languages:       list[str] = Field(default=["en"])
    priority:        int  = Field(default=5, ge=0, le=10)
    timeout_seconds: int  = Field(default=600, ge=30, le=900)
    plan:            str  = Field(default="pro")

    @field_validator("depth")
    @classmethod
    def validate_depth(cls, v: str) -> str:
        if v not in ("basic", "full"):
            raise ValueError("depth must be 'basic' or 'full'")
        return v


class ResearchTaskEvent(BaseModel):
    name: str = "nexus/task.research.requested"
    data: ResearchTaskEventData


# ── Memory Extract ────────────────────────────────────────────────────────────

class MemoryExtractEventData(BaseModel):
    user_id:  str
    task_id:  str
    summary:  Optional[str] = None   # Pre-computed task summary
    session_transcript: Optional[str] = None  # Full session for deep extraction


class MemoryExtractEvent(BaseModel):
    name: str = "nexus/session.memory.extract"
    data: MemoryExtractEventData


# ── Usage Increment ───────────────────────────────────────────────────────────

class UsageIncrementEventData(BaseModel):
    user_id: str
    metric:  str  # "task_run" | "browser_task" | "research_task"
    task_id: str  # For deduplication / audit log

    @field_validator("metric")
    @classmethod
    def validate_metric(cls, v: str) -> str:
        allowed = {"task_run", "browser_task", "research_task"}
        if v not in allowed:
            raise ValueError(f"metric must be one of {allowed}")
        return v


class UsageIncrementEvent(BaseModel):
    name: str = "nexus/usage.increment"
    data: UsageIncrementEventData


# ── Helper: Send Typed Event ──────────────────────────────────────────────────

async def send_typed_event(event_model: BaseModel) -> None:
    """Send an Inngest event using a typed Pydantic model."""
    from services.inngest_client import inngest_client

    await inngest_client.send(
        inngest.Event(
            name=event_model.name,
            data=event_model.data.model_dump(),
        )
    )
```

---

## 8. Error Handling & Dead Letter Queue

### Inngest Retry Behavior

Inngest uses **exponential backoff** for retries. Default backoff schedule:

| Attempt | Delay |
|---|---|
| 1st retry | 1 minute |
| 2nd retry | 10 minutes |
| 3rd retry | 30 minutes (if configured) |

For Nexus functions:
- Browser tasks: 2 retries (can recover from transient browser crashes)
- Windows tasks: 1 retry (most failures are deterministic — retrying won't help)
- Research tasks: 1 retry (LLM/API failures can be transient)
- Usage tracking: 5 retries (critical — must not miss an increment)
- Memory extraction: 2 retries (non-critical, debounced)

### Handling Retries in Function Code

```python
@inngest_client.create_function(
    fn_id="nexus/browser-task",
    trigger=inngest.TriggerEvent(event="nexus/task.browser.requested"),
    retries=2,
    timeout="10m",
)
async def handle_browser_task(ctx: inngest.Context, step: inngest.Step) -> dict:
    # ctx.attempt tells you which attempt this is (0=first, 1=first retry, ...)
    attempt = ctx.attempt

    if attempt > 0:
        # This is a retry — log it and update task
        async def _mark_retrying():
            async with get_async_db_session() as db:
                await db.execute(
                    text("""
                        UPDATE tasks SET
                            error_message = :msg,
                            updated_at    = NOW()
                        WHERE id = :task_id
                    """),
                    {
                        "msg":     f"Retrying (attempt {attempt + 1})...",
                        "task_id": ctx.event.data["task_id"],
                    },
                )
                await db.commit()

        await step.run("mark-retrying", _mark_retrying)

    # ... rest of function
```

### What Happens When All Retries Are Exhausted

When Inngest exhausts all retries, the function is moved to the **Dead Letter Queue** in the Inngest dashboard. Simultaneously:

```python
# Inngest calls the function one final time with ctx.attempt == max_retries + 1
# We detect this and mark the task as permanently failed:

async def handle_browser_task(ctx: inngest.Context, step: inngest.Step) -> dict:
    MAX_RETRIES = 2

    try:
        # ... execute task ...
        pass
    except Exception as exc:
        # On final attempt, mark as permanently failed
        if ctx.attempt >= MAX_RETRIES:
            async def _mark_failed():
                async with get_async_db_session() as db:
                    await db.execute(
                        text("""
                            UPDATE tasks SET
                                status        = 'failed',
                                error_message = :error,
                                completed_at  = NOW(),
                                updated_at    = NOW()
                            WHERE id = :task_id
                        """),
                        {
                            "error":   str(exc)[:500],
                            "task_id": ctx.event.data["task_id"],
                        },
                    )
                    await db.commit()

            await step.run("mark-failed", _mark_failed)

            # Notify user via SSE (task.failed event will be picked up by stream)
            # Optionally: send push notification / email for Power users

        raise  # Re-raise so Inngest records the failure correctly
```

### Dead Letter Queue (Inngest Dashboard)

Failed events that exhausted retries appear in the Inngest dashboard under **Dead Events**. From there you can:
- **Replay** a specific event (re-run the function with the original payload)
- **Inspect** the full error trace and step-by-step execution log
- **Bulk replay** all dead events of a given type after deploying a fix

```python
# To manually replay a dead event via API (for support tooling):
# POST https://api.inngest.com/v1/events/{event_id}/replay
# Authorization: Bearer {INNGEST_API_KEY}
```

### User-Facing Error Messages

| Failure Type | User Message |
|---|---|
| Browser launch failed | "Could not start the browser. This usually means the page was unreachable. Try again?" |
| Goal execution timeout | "The task took too long and was stopped. Try breaking it into smaller steps." |
| Research API failure | "Research service is temporarily unavailable. We'll retry automatically." |
| Windows access denied | "Nexus doesn't have permission for that action. Check the Windows agent permissions." |
| Unknown error | "Something went wrong. Our team has been notified. Task ID: {task_id}" |

---

## 9. Local Development Flow

### Prerequisites

```bash
# Python environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Node.js (for Inngest CLI)
node --version  # Requires Node 18+
npm install -g inngest-cli   # Or use npx each time
```

### Step-by-Step Local Setup

#### Step 1: Configure Environment

```bash
# .env.local (copy from .env.example)
cp .env.example .env.local

# Required for local dev:
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:54322/nexus
SUPABASE_URL=http://localhost:54321
SUPABASE_ANON_KEY=your_local_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_local_service_role_key

# Inngest local dev — these are auto-set by dev server, but set them anyway:
INNGEST_EVENT_KEY=local
INNGEST_SIGNING_KEY=local
INNGEST_DEV=true
```

#### Step 2: Start Supabase Local

```bash
# If using Supabase CLI for local DB
npx supabase start

# Run migrations
npx supabase db push
# or:
npx supabase migration up
```

#### Step 3: Start FastAPI

```bash
uvicorn main:app --reload --port 8000 --log-level debug

# You should see:
# INFO:     Uvicorn running on http://127.0.0.1:8000
# INFO:     Inngest endpoint mounted at /api/inngest
```

#### Step 4: Start Inngest Dev Server

```bash
# In a separate terminal
npx inngest-cli@latest dev -u http://localhost:8000/api/inngest

# This starts the Inngest dev server at http://localhost:8288
# It will:
#   - Connect to your FastAPI app at /api/inngest
#   - Discover all registered functions automatically
#   - Act as the message queue locally (no Inngest cloud needed)
#   - Provide the dev UI for monitoring runs
```

#### Step 5: Test an Event

```bash
# Option A: Use the Inngest dev UI at http://localhost:8288
# → Go to "Test" tab → Select function → Send test event with JSON payload

# Option B: Use the Inngest CLI
npx inngest-cli@latest event send nexus/task.browser.requested \
  --data '{
    "task_id": "test-task-001",
    "user_id": "test-user-001",
    "goal": "Search for the latest Python release notes",
    "url": "https://python.org",
    "priority": 0,
    "timeout_seconds": 60
  }'

# Option C: Hit your FastAPI endpoint directly
curl -X POST http://localhost:8000/api/v1/tasks/browser \
  -H "Authorization: Bearer your_test_jwt" \
  -H "Content-Type: application/json" \
  -d '{"goal": "Search for Python 3.14 release notes"}'
```

#### Step 6: Monitor in Inngest Dev UI

```
Open: http://localhost:8288

→ Functions tab: Shows all registered Nexus functions
→ Runs tab: Real-time list of function executions with status
→ Click any run: Shows step-by-step execution trace, input/output per step
→ Replay failed runs: One click to re-send the original event
```

### Development Workflow for New Task Types

1. Define the Pydantic event schema in `app/schemas/inngest_events.py`
2. Create the function file in `services/inngest_functions/`
3. Register it in `main.py` in the `functions=[...]` list
4. Restart FastAPI — Inngest dev server auto-syncs
5. Send a test event via dev UI
6. Watch the step trace in the dev UI

### Useful Local Dev Commands

```bash
# Check registered functions
curl http://localhost:8000/api/inngest

# Tail FastAPI logs
uvicorn main:app --reload --log-level debug 2>&1 | grep -E "(inngest|task|error)"

# Watch Supabase DB changes in real time
npx supabase db logs --tail

# Reset local DB and re-run migrations
npx supabase db reset
```

### Deploying to Production (Railway)

```bash
# Set environment variables in Railway dashboard:
INNGEST_EVENT_KEY=evt_xxx
INNGEST_SIGNING_KEY=signkey-prod-xxx

# After deploy, register your endpoint with Inngest Cloud:
# Dashboard → Apps → Add App → URL: https://api.nexus.app/api/inngest
# Inngest will call this URL to discover and invoke functions.

# Verify registration:
curl https://api.nexus.app/api/inngest
# Should return: {"message":"Inngest endpoint","functions":[...]}
```

---

*Document end. See also: `monetization_model.md` for quota enforcement that integrates with the task dispatch flow described here.*
