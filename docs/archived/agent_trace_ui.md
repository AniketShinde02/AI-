# Agent Trace UI — Live Execution Visibility System
**Document:** `08_agent_trace_ui.md`  
**Version:** 1.0  
**Scope:** Frontend component architecture, backend event emission, streaming protocol, and animation design for real-time agent execution visibility in Nexus 2.0.  
**Reference UI:** Perplexity Computer's activity panel (the expandable "Thinking / Running tasks in parallel / Reading files" trace panel you see mid-response)

---

## 1. What This Feature Is

Every time Nexus executes a task — browser automation, file operations, Windows control, memory retrieval, research — the user should see a **live trace panel** that mirrors exactly what the agent is doing, step by step, in real time.

Not a spinner. Not "Working on it…". A real, expanding timeline with icons, statuses, elapsed times, and expandable detail — exactly like Perplexity Computer's activity feed.

This is not optional polish. It is a **trust and retention mechanism**. Users who can see what the agent is doing:
- Stay engaged instead of closing the window
- Understand why tasks take time
- Trust the system enough to let it complete
- Notice failures and give better corrections
- Come back because the experience feels intelligent

---

## 2. The Three Laws of Trace UI

Before any implementation detail, internalize these:

**Law 1 — Never show raw reasoning tokens.**  
Expose actions, steps, tool names, and statuses. Never expose the LLM's internal chain-of-thought reasoning. Showing "Hmm, the user probably wants X, let me think about Y…" is unprofessional and confusing. Show: what tool is running, what it found, what the status is.

**Law 2 — Progressive disclosure.**  
The glanceable view shows step name + status icon. The expandable view shows tool parameters + results. Never force users to read walls of logs. Collapsed by default, expandable on demand.

**Law 3 — No silent waiting beyond 2 seconds.**  
If Nexus hasn't emitted a new trace event in 2 seconds, emit a heartbeat event ("Still working…"). Users interpret silence as failure.

---

## 3. UI Anatomy — What You're Building

Based on Perplexity Computer's trace panel (your screenshot reference), here is the exact component anatomy:

```
┌─────────────────────────────────────────────────────┐
│  AGENT TRACE PANEL                                  │
│  ─────────────────────────────────────────────────  │
│  ✅  Understood request           [0.2s]            │
│  ✅  Searching memory             [0.8s]  >         │
│  ✅  Opening browser              [1.1s]            │
│  ⟳   Extracting leads from LinkedIn  [running...]   │
│  ○   Writing CSV file             [waiting]         │
│  ○   Generating outreach messages [waiting]         │
│  ─────────────────────────────────────────────────  │
│  Progress: ██████░░░░  3 of 6 steps complete        │
│  Elapsed: 12s   |  Est. remaining: ~18s             │
│                                      [Cancel Task]  │
└─────────────────────────────────────────────────────┘
```

**When a step is expandable (the `>` arrow):**

```
│  ✅  Searching memory             [0.8s]  ∨         │
│      └─ Retrieved 3 relevant memories:              │
│           • "User prefers CSV exports"              │
│           • "LinkedIn automation blocked 2x before" │
│           • "Outreach tone: professional"           │
```

**When "Thinking" step is active (Perplexity-style):**

```
│  🧠  Thinking                     [streaming]  ∨   │
│      └─ Planning approach...                        │
│         Breaking task into 3 sub-steps.             │
│         Using Browser Use for LinkedIn...           │
```

---

## 4. Step Status System

Every trace step has one of these statuses. Each maps to a specific icon and animation state:

| Status | Icon | Animation | Color |
|---|---|---|---|
| `waiting` | `○` (hollow circle) | None | Gray (#6B7280) |
| `running` | `⟳` (spinning ring) | Continuous rotation 1s linear | Blue (#3B82F6) |
| `thinking` | `🧠` or pulsing orb | Opacity pulse 1.5s ease-in-out | Purple (#8B5CF6) |
| `succeeded` | `✅` (checkmark) | Brief scale-up on completion | Green (#10B981) |
| `failed` | `✗` (cross) | Subtle shake on appear | Red (#EF4444) |
| `retrying` | `↺` (refresh arrow) | Counter-rotation 0.8s | Orange (#F59E0B) |
| `skipped` | `—` (dash) | None | Gray (#9CA3AF) |
| `awaiting_input` | `⏸` (pause) | Pulse border | Amber (#F59E0B) |

---

## 5. Trace Event Schema

This is what the backend emits. Every field matters.

### 5.1 Task created event
```json
{
  "event": "task_created",
  "task_id": "uuid",
  "title": "Extract leads from LinkedIn",
  "type": "browser",
  "total_steps_estimate": 6,
  "created_at": "2026-04-27T12:00:00Z"
}
```

### 5.2 Step started event
```json
{
  "event": "step_started",
  "task_id": "uuid",
  "step_id": "step-3",
  "step_index": 2,
  "step_name": "Extracting leads from LinkedIn",
  "tool": "browser_use",
  "icon_hint": "browser",
  "started_at": "2026-04-27T12:00:12Z"
}
```

### 5.3 Step log event (streaming text within a step)
```json
{
  "event": "step_log",
  "task_id": "uuid",
  "step_id": "step-3",
  "log_type": "info",
  "message": "Navigating to linkedin.com/search...",
  "timestamp": "2026-04-27T12:00:13Z"
}
```

### 5.4 Step completed event
```json
{
  "event": "step_completed",
  "task_id": "uuid",
  "step_id": "step-3",
  "status": "succeeded",
  "duration_ms": 8400,
  "summary": "Found 47 matching profiles",
  "expandable_data": {
    "type": "list",
    "items": ["Alice Chen - Founder", "Bob Kumar - CTO", "..."]
  },
  "completed_at": "2026-04-27T12:00:20Z"
}
```

### 5.5 Step failed event
```json
{
  "event": "step_failed",
  "task_id": "uuid",
  "step_id": "step-3",
  "status": "failed",
  "error_code": "BROWSER_BLOCKED",
  "error_message": "LinkedIn requires login. Browser session may have expired.",
  "is_retrying": true,
  "retry_count": 1,
  "max_retries": 2
}
```

### 5.6 Human approval required event
```json
{
  "event": "approval_required",
  "task_id": "uuid",
  "step_id": "step-5",
  "risk_level": "high",
  "action_description": "About to send 47 connection requests on LinkedIn",
  "consequences": "This is irreversible. Connection requests will be sent.",
  "approve_label": "Send requests",
  "deny_label": "Cancel"
}
```

### 5.7 Task completed event
```json
{
  "event": "task_completed",
  "task_id": "uuid",
  "status": "succeeded",
  "steps_total": 6,
  "steps_succeeded": 5,
  "steps_failed": 1,
  "duration_ms": 42000,
  "output_document_id": "doc-uuid",
  "final_message": "Extracted 47 leads and saved to leads.csv"
}
```

### 5.8 Heartbeat event (prevent silent waiting)
```json
{
  "event": "heartbeat",
  "task_id": "uuid",
  "step_id": "step-3",
  "message": "Still working... browser is loading results",
  "elapsed_ms": 8000
}
```

---

## 6. Backend Streaming Protocol

### 6.1 Transport: SSE for trace events, WebSocket for voice

For the trace panel specifically, use **Server-Sent Events (SSE)**, not WebSockets. Here's why:

| Criteria | SSE | WebSocket |
|---|---|---|
| Direction | Server → Client only | Bidirectional |
| Complexity | Simple HTTP | Protocol upgrade |
| Auto-reconnect | Built into browser | Manual |
| Firewall compatibility | Works through proxies | Sometimes blocked |
| Use case fit | Agent trace events | Voice/real-time chat |

Trace events are **one-directional** (backend pushes updates to frontend). SSE is the correct tool. The Cancel action is a separate REST call.

Use WebSocket only for voice sessions (already in your architecture).

### 6.2 FastAPI SSE endpoint

```python
# backend/api/http.py
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
import asyncio

@router.get("/api/v1/tasks/{task_id}/stream")
async def stream_task_events(task_id: str, current_user: User = Depends(get_current_user)):
    """
    SSE endpoint: streams trace events for a running task.
    Client connects here and receives events as the task progresses.
    """
    async def event_generator():
        async for event in task_event_queue.subscribe(task_id, user_id=current_user.id):
            yield {
                "event": event["event"],
                "data": json.dumps(event),
                "id": event.get("step_id", str(uuid4()))
            }
    
    return EventSourceResponse(event_generator())
```

### 6.3 Event emission from inside task execution

Every core module that executes work must be able to emit trace events. Use a shared event bus:

```python
# backend/core/trace.py
class TaskTracer:
    """
    Injected into any module that needs to emit trace events.
    Handles emission to the SSE queue + saving to DB.
    """
    def __init__(self, task_id: str, user_id: str):
        self.task_id = task_id
        self.user_id = user_id
    
    async def step_started(self, step_id: str, step_name: str, tool: str, icon_hint: str = "default") -> None:
        event = {
            "event": "step_started",
            "task_id": self.task_id,
            "step_id": step_id,
            "step_name": step_name,
            "tool": tool,
            "icon_hint": icon_hint,
            "started_at": utcnow_iso()
        }
        await self._emit(event)
    
    async def step_log(self, step_id: str, message: str, log_type: str = "info") -> None:
        event = {
            "event": "step_log",
            "task_id": self.task_id,
            "step_id": step_id,
            "log_type": log_type,
            "message": message,
            "timestamp": utcnow_iso()
        }
        await self._emit(event)
    
    async def step_completed(self, step_id: str, summary: str, duration_ms: int, expandable_data: dict = None) -> None:
        event = {
            "event": "step_completed",
            "task_id": self.task_id,
            "step_id": step_id,
            "status": "succeeded",
            "duration_ms": duration_ms,
            "summary": summary,
            "expandable_data": expandable_data
        }
        await self._emit(event)
    
    async def step_failed(self, step_id: str, error_code: str, error_message: str, is_retrying: bool = False) -> None:
        event = {
            "event": "step_failed",
            "task_id": self.task_id,
            "step_id": step_id,
            "status": "failed",
            "error_code": error_code,
            "error_message": error_message,
            "is_retrying": is_retrying
        }
        await self._emit(event)
    
    async def heartbeat(self, step_id: str, message: str, elapsed_ms: int) -> None:
        event = {
            "event": "heartbeat",
            "task_id": self.task_id,
            "step_id": step_id,
            "message": message,
            "elapsed_ms": elapsed_ms
        }
        await self._emit(event)
    
    async def _emit(self, event: dict) -> None:
        # Push to in-memory queue subscribed by SSE endpoint
        await task_event_queue.push(self.task_id, event)
        # Persist to DB for history/replay
        await db_save_trace_event(event)
```

**Usage inside any module:**
```python
# backend/services/browser_use_client.py
async def run_browser_task(task_id: str, goal: str, tracer: TaskTracer) -> dict:
    step_id = "browser-step-1"
    
    await tracer.step_started(step_id, "Opening browser", tool="browser_use", icon_hint="browser")
    
    try:
        # Start heartbeat ticker in background
        heartbeat_task = asyncio.create_task(
            _heartbeat_loop(tracer, step_id, interval_ms=2000)
        )
        
        result = await browser_use_agent.run(goal=goal)
        heartbeat_task.cancel()
        
        await tracer.step_completed(
            step_id,
            summary=f"Completed: {result.summary}",
            duration_ms=result.elapsed_ms,
            expandable_data=result.structured_data
        )
        return result
        
    except BrowserBlockedError as e:
        heartbeat_task.cancel()
        await tracer.step_failed(step_id, "BROWSER_BLOCKED", str(e), is_retrying=True)
        raise
```

### 6.4 In-memory event queue

For MVP, use a simple asyncio queue per task. For scale, swap with Redis pub/sub:

```python
# backend/core/event_queue.py
from asyncio import Queue
from collections import defaultdict
from typing import AsyncGenerator

class TaskEventQueue:
    def __init__(self):
        self._queues: dict[str, list[Queue]] = defaultdict(list)
    
    async def push(self, task_id: str, event: dict) -> None:
        for q in self._queues[task_id]:
            await q.put(event)
    
    async def subscribe(self, task_id: str, user_id: str) -> AsyncGenerator:
        q = Queue(maxsize=500)
        self._queues[task_id].append(q)
        try:
            while True:
                event = await q.get()
                yield event
                if event["event"] in ("task_completed", "task_failed", "task_cancelled"):
                    break
        finally:
            self._queues[task_id].remove(q)

task_event_queue = TaskEventQueue()
```

---

## 7. Frontend Component Architecture

### 7.1 Component stack

```
AgentTracePanel (container)
├── TaskHeader
│   ├── TaskTitle
│   ├── ProgressBar
│   └── ElapsedTime
├── StepTimeline
│   └── StepItem[] (one per step)
│       ├── StepIcon (status-driven)
│       ├── StepName
│       ├── StepDuration
│       ├── ExpandToggle (if expandable_data exists)
│       └── StepDetail (collapsed by default)
│           ├── LogStream (for step_log events)
│           └── StructuredData (for expandable_data)
├── ApprovalGate (conditional, renders on approval_required)
│   ├── RiskBadge (green/amber/red)
│   ├── ActionDescription
│   └── ApproveButton + DenyButton
└── TaskFooter
    ├── EstimatedRemaining
    └── CancelButton
```

### 7.2 Custom hook: useTaskStream

```typescript
// frontend/src/hooks/useTaskStream.ts
import { useEffect, useReducer, useRef } from 'react'

type StepStatus = 'waiting' | 'running' | 'thinking' | 'succeeded' | 'failed' | 'retrying' | 'awaiting_input' | 'skipped'

interface TraceStep {
  id: string
  name: string
  status: StepStatus
  tool?: string
  icon_hint?: string
  started_at?: string
  duration_ms?: number
  summary?: string
  logs: string[]
  expandable_data?: unknown
  error_message?: string
  is_retrying?: boolean
}

interface TaskTrace {
  task_id: string
  title: string
  status: 'running' | 'succeeded' | 'failed' | 'cancelled'
  steps: TraceStep[]
  total_steps_estimate: number
  elapsed_ms: number
  approval_pending?: ApprovalRequest
}

type TraceAction =
  | { type: 'TASK_CREATED'; payload: any }
  | { type: 'STEP_STARTED'; payload: any }
  | { type: 'STEP_LOG'; payload: any }
  | { type: 'STEP_COMPLETED'; payload: any }
  | { type: 'STEP_FAILED'; payload: any }
  | { type: 'HEARTBEAT'; payload: any }
  | { type: 'APPROVAL_REQUIRED'; payload: any }
  | { type: 'TASK_COMPLETED'; payload: any }

function traceReducer(state: TaskTrace | null, action: TraceAction): TaskTrace | null {
  switch (action.type) {
    case 'TASK_CREATED':
      return {
        task_id: action.payload.task_id,
        title: action.payload.title,
        status: 'running',
        steps: [],
        total_steps_estimate: action.payload.total_steps_estimate ?? 0,
        elapsed_ms: 0
      }
    
    case 'STEP_STARTED':
      if (!state) return state
      const newStep: TraceStep = {
        id: action.payload.step_id,
        name: action.payload.step_name,
        status: 'running',
        tool: action.payload.tool,
        icon_hint: action.payload.icon_hint,
        started_at: action.payload.started_at,
        logs: []
      }
      return { ...state, steps: [...state.steps, newStep] }
    
    case 'STEP_LOG':
      if (!state) return state
      return {
        ...state,
        steps: state.steps.map(s =>
          s.id === action.payload.step_id
            ? { ...s, logs: [...s.logs, action.payload.message] }
            : s
        )
      }
    
    case 'STEP_COMPLETED':
      if (!state) return state
      return {
        ...state,
        steps: state.steps.map(s =>
          s.id === action.payload.step_id
            ? {
                ...s,
                status: 'succeeded',
                duration_ms: action.payload.duration_ms,
                summary: action.payload.summary,
                expandable_data: action.payload.expandable_data
              }
            : s
        )
      }
    
    case 'STEP_FAILED':
      if (!state) return state
      return {
        ...state,
        steps: state.steps.map(s =>
          s.id === action.payload.step_id
            ? {
                ...s,
                status: action.payload.is_retrying ? 'retrying' : 'failed',
                error_message: action.payload.error_message,
                is_retrying: action.payload.is_retrying
              }
            : s
        )
      }
    
    case 'APPROVAL_REQUIRED':
      if (!state) return state
      return {
        ...state,
        steps: state.steps.map(s =>
          s.id === action.payload.step_id ? { ...s, status: 'awaiting_input' } : s
        ),
        approval_pending: action.payload
      }
    
    case 'TASK_COMPLETED':
      if (!state) return state
      return {
        ...state,
        status: action.payload.status,
        approval_pending: undefined
      }
    
    default:
      return state
  }
}

export function useTaskStream(taskId: string | null) {
  const [trace, dispatch] = useReducer(traceReducer, null)
  const esRef = useRef<EventSource | null>(null)
  
  useEffect(() => {
    if (!taskId) return
    
    const token = getAuthToken()
    // Note: EventSource doesn't support custom headers natively.
    // Pass token as query param or use @microsoft/fetch-event-source for header auth.
    const es = new EventSource(`/api/v1/tasks/${taskId}/stream?token=${token}`)
    esRef.current = es
    
    es.addEventListener('task_created', (e) => dispatch({ type: 'TASK_CREATED', payload: JSON.parse(e.data) }))
    es.addEventListener('step_started', (e) => dispatch({ type: 'STEP_STARTED', payload: JSON.parse(e.data) }))
    es.addEventListener('step_log', (e) => dispatch({ type: 'STEP_LOG', payload: JSON.parse(e.data) }))
    es.addEventListener('step_completed', (e) => dispatch({ type: 'STEP_COMPLETED', payload: JSON.parse(e.data) }))
    es.addEventListener('step_failed', (e) => dispatch({ type: 'STEP_FAILED', payload: JSON.parse(e.data) }))
    es.addEventListener('heartbeat', (e) => dispatch({ type: 'HEARTBEAT', payload: JSON.parse(e.data) }))
    es.addEventListener('approval_required', (e) => dispatch({ type: 'APPROVAL_REQUIRED', payload: JSON.parse(e.data) }))
    es.addEventListener('task_completed', (e) => {
      dispatch({ type: 'TASK_COMPLETED', payload: JSON.parse(e.data) })
      es.close()
    })
    
    es.onerror = () => {
      // EventSource auto-reconnects — log but don't panic
      console.warn('SSE connection interrupted, browser will reconnect...')
    }
    
    return () => {
      es.close()
      esRef.current = null
    }
  }, [taskId])
  
  const cancelTask = async () => {
    if (!taskId) return
    await fetch(`/api/v1/tasks/${taskId}/cancel`, { method: 'POST' })
  }
  
  const approveStep = async (stepId: string) => {
    await fetch(`/api/v1/tasks/${taskId}/steps/${stepId}/approve`, { method: 'POST' })
  }
  
  const denyStep = async (stepId: string) => {
    await fetch(`/api/v1/tasks/${taskId}/steps/${stepId}/deny`, { method: 'POST' })
  }
  
  return { trace, cancelTask, approveStep, denyStep }
}
```

### 7.3 StepIcon component (the animated indicator)

This is the most important visual component — it changes animation based on status:

```tsx
// frontend/src/components/trace/StepIcon.tsx
import { cn } from '@/lib/utils'

interface StepIconProps {
  status: StepStatus
  iconHint?: string
}

const iconMap: Record<string, string> = {
  browser: '🌐',
  memory: '🧠',
  windows: '🖥️',
  research: '🔍',
  file: '📁',
  default: '⚡'
}

export function StepIcon({ status, iconHint = 'default' }: StepIconProps) {
  if (status === 'succeeded') {
    return (
      <span className="step-icon step-icon--success animate-check-appear">
        <svg className="w-4 h-4 text-green-500" viewBox="0 0 16 16" fill="none">
          <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5"/>
          <path d="M5 8l2 2 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
        </svg>
      </span>
    )
  }
  
  if (status === 'running' || status === 'thinking') {
    return (
      <span className="step-icon step-icon--running">
        <svg
          className={cn(
            'w-4 h-4',
            status === 'running' ? 'text-blue-500 animate-spin' : 'text-purple-500 animate-pulse-ring'
          )}
          viewBox="0 0 16 16" fill="none"
        >
          <circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeWidth="1.5"
            strokeDasharray="12 28" strokeLinecap="round"/>
        </svg>
      </span>
    )
  }
  
  if (status === 'failed') {
    return (
      <span className="step-icon step-icon--failed animate-shake">
        <svg className="w-4 h-4 text-red-500" viewBox="0 0 16 16" fill="none">
          <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5"/>
          <path d="M5.5 5.5l5 5M10.5 5.5l-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
        </svg>
      </span>
    )
  }
  
  if (status === 'retrying') {
    return (
      <span className="step-icon step-icon--retrying">
        <svg className="w-4 h-4 text-orange-500 animate-spin-reverse" viewBox="0 0 16 16" fill="none">
          <path d="M13 8a5 5 0 1 1-1-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          <path d="M10 2l2 3-3 1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </span>
    )
  }
  
  if (status === 'awaiting_input') {
    return (
      <span className="step-icon step-icon--awaiting animate-pulse-border">
        <svg className="w-4 h-4 text-amber-500" viewBox="0 0 16 16" fill="none">
          <rect x="1.5" y="1.5" width="13" height="13" rx="2" stroke="currentColor" strokeWidth="1.5"/>
          <path d="M6 6h.01M8 6h.01M10 6h.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
        </svg>
      </span>
    )
  }
  
  // waiting / default
  return (
    <span className="step-icon step-icon--waiting">
      <svg className="w-4 h-4 text-gray-400" viewBox="0 0 16 16" fill="none">
        <circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeWidth="1.5"/>
      </svg>
    </span>
  )
}
```

### 7.4 Tailwind animation config for trace states

Add to your `tailwind.config.ts`:

```typescript
// tailwind.config.ts
export default {
  theme: {
    extend: {
      animation: {
        'spin': 'spin 1s linear infinite',
        'spin-reverse': 'spin-reverse 0.8s linear infinite',
        'pulse-ring': 'pulse-ring 1.5s ease-in-out infinite',
        'check-appear': 'check-appear 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards',
        'shake': 'shake 0.4s ease-in-out',
        'step-enter': 'step-enter 0.25s ease-out forwards',
        'pulse-border': 'pulse-border 1.5s ease-in-out infinite',
      },
      keyframes: {
        'spin-reverse': {
          from: { transform: 'rotate(360deg)' },
          to: { transform: 'rotate(0deg)' }
        },
        'pulse-ring': {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.5', transform: 'scale(0.95)' }
        },
        'check-appear': {
          '0%': { transform: 'scale(0.5)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' }
        },
        'shake': {
          '0%, 100%': { transform: 'translateX(0)' },
          '20%': { transform: 'translateX(-4px)' },
          '60%': { transform: 'translateX(4px)' },
        },
        'step-enter': {
          '0%': { opacity: '0', transform: 'translateY(-4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' }
        },
        'pulse-border': {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(245, 158, 11, 0.4)' },
          '50%': { boxShadow: '0 0 0 4px rgba(245, 158, 11, 0)' }
        }
      }
    }
  }
}
```

### 7.5 Main AgentTracePanel component

```tsx
// frontend/src/components/trace/AgentTracePanel.tsx
import { useTaskStream } from '@/hooks/useTaskStream'
import { StepIcon } from './StepIcon'
import { ApprovalGate } from './ApprovalGate'
import { cn } from '@/lib/utils'
import { useState } from 'react'

interface AgentTracePanelProps {
  taskId: string
  onComplete?: (result: any) => void
}

export function AgentTracePanel({ taskId, onComplete }: AgentTracePanelProps) {
  const { trace, cancelTask, approveStep, denyStep } = useTaskStream(taskId)
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set())
  
  if (!trace) return <AgentTraceSkeleton />
  
  const completedCount = trace.steps.filter(s => s.status === 'succeeded').length
  const progress = trace.total_steps_estimate > 0
    ? (completedCount / trace.total_steps_estimate) * 100
    : 0
  
  return (
    <div className="agent-trace-panel rounded-xl border border-zinc-800 bg-zinc-900/80 backdrop-blur p-4 w-full max-w-lg">
      
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div>
          <p className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Nexus is working</p>
          <h3 className="text-sm font-semibold text-zinc-100 mt-0.5">{trace.title}</h3>
        </div>
        {trace.status === 'running' && (
          <button
            onClick={cancelTask}
            className="text-xs text-zinc-500 hover:text-red-400 transition-colors px-2 py-1 rounded border border-zinc-700 hover:border-red-800"
          >
            Cancel
          </button>
        )}
      </div>
      
      {/* Progress bar */}
      {trace.total_steps_estimate > 0 && (
        <div className="mb-4">
          <div className="h-1 bg-zinc-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="flex justify-between mt-1">
            <span className="text-xs text-zinc-500">
              {completedCount} of {trace.total_steps_estimate} steps
            </span>
            <ElapsedTimer startedAt={trace.steps[0]?.started_at} isRunning={trace.status === 'running'} />
          </div>
        </div>
      )}
      
      {/* Steps timeline */}
      <div className="space-y-1">
        {trace.steps.map((step, index) => {
          const isExpanded = expandedSteps.has(step.id)
          const hasExpandable = step.expandable_data || step.logs.length > 0
          
          return (
            <div
              key={step.id}
              className="animate-step-enter"
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <div
                className={cn(
                  "flex items-center gap-2.5 px-2 py-1.5 rounded-lg group",
                  hasExpandable && "cursor-pointer hover:bg-zinc-800/50 transition-colors",
                  step.status === 'running' && "bg-blue-950/20",
                  step.status === 'failed' && "bg-red-950/20",
                  step.status === 'awaiting_input' && "bg-amber-950/20"
                )}
                onClick={() => {
                  if (!hasExpandable) return
                  setExpandedSteps(prev => {
                    const next = new Set(prev)
                    next.has(step.id) ? next.delete(step.id) : next.add(step.id)
                    return next
                  })
                }}
              >
                <StepIcon status={step.status} iconHint={step.icon_hint} />
                
                <span className={cn(
                  "text-sm flex-1",
                  step.status === 'waiting' && "text-zinc-500",
                  step.status === 'running' && "text-zinc-200",
                  step.status === 'thinking' && "text-purple-300",
                  step.status === 'succeeded' && "text-zinc-300",
                  step.status === 'failed' && "text-red-400",
                  step.status === 'retrying' && "text-orange-400",
                  step.status === 'awaiting_input' && "text-amber-300"
                )}>
                  {step.name}
                  {step.is_retrying && (
                    <span className="ml-2 text-xs text-orange-500 bg-orange-950/40 px-1.5 py-0.5 rounded">
                      retrying
                    </span>
                  )}
                </span>
                
                {step.duration_ms && (
                  <span className="text-xs text-zinc-600 font-mono">
                    {formatDuration(step.duration_ms)}
                  </span>
                )}
                
                {hasExpandable && (
                  <svg
                    className={cn(
                      "w-3 h-3 text-zinc-600 transition-transform",
                      isExpanded && "rotate-90"
                    )}
                    fill="none" viewBox="0 0 16 16"
                  >
                    <path d="M6 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                  </svg>
                )}
              </div>
              
              {/* Expandable detail */}
              {isExpanded && hasExpandable && (
                <div className="ml-8 pl-2 border-l border-zinc-800 mt-1 mb-1 space-y-1">
                  {step.logs.map((log, i) => (
                    <p key={i} className="text-xs text-zinc-500 font-mono leading-relaxed">{log}</p>
                  ))}
                  {step.summary && (
                    <p className="text-xs text-zinc-400 mt-1">{step.summary}</p>
                  )}
                  {step.error_message && (
                    <p className="text-xs text-red-400 mt-1">⚠ {step.error_message}</p>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
      
      {/* Approval gate */}
      {trace.approval_pending && (
        <ApprovalGate
          request={trace.approval_pending}
          onApprove={() => approveStep(trace.approval_pending!.step_id)}
          onDeny={() => denyStep(trace.approval_pending!.step_id)}
        />
      )}
      
      {/* Task complete state */}
      {trace.status === 'succeeded' && (
        <div className="mt-3 pt-3 border-t border-zinc-800">
          <p className="text-xs text-green-400 flex items-center gap-1.5">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 16 16">
              <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5"/>
              <path d="M5 8l2 2 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
            Task completed successfully
          </p>
        </div>
      )}
    </div>
  )
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}
```

---

## 8. ApprovalGate Component

When the agent is about to do something irreversible, it must pause and ask:

```tsx
// frontend/src/components/trace/ApprovalGate.tsx
interface ApprovalRequest {
  step_id: string
  risk_level: 'low' | 'medium' | 'high'
  action_description: string
  consequences: string
  approve_label: string
  deny_label: string
}

const riskConfig = {
  low: { color: 'text-green-400', bg: 'bg-green-950/30', border: 'border-green-900', label: 'Low risk' },
  medium: { color: 'text-amber-400', bg: 'bg-amber-950/30', border: 'border-amber-900', label: 'Caution' },
  high: { color: 'text-red-400', bg: 'bg-red-950/30', border: 'border-red-900', label: 'Sensitive action' }
}

export function ApprovalGate({ request, onApprove, onDeny }: {
  request: ApprovalRequest
  onApprove: () => void
  onDeny: () => void
}) {
  const risk = riskConfig[request.risk_level]
  
  return (
    <div className={`mt-3 p-3 rounded-lg border ${risk.border} ${risk.bg} animate-step-enter`}>
      <div className="flex items-center gap-2 mb-2">
        <span className={`text-xs font-semibold uppercase tracking-wide ${risk.color}`}>
          {risk.label}
        </span>
      </div>
      <p className="text-sm text-zinc-300 mb-1">{request.action_description}</p>
      <p className="text-xs text-zinc-500 mb-3">{request.consequences}</p>
      <div className="flex gap-2">
        <button
          onClick={onApprove}
          className={`flex-1 text-sm py-1.5 px-3 rounded-lg font-medium transition-colors ${
            request.risk_level === 'high'
              ? 'bg-red-900 hover:bg-red-800 text-red-100'
              : 'bg-blue-900 hover:bg-blue-800 text-blue-100'
          }`}
        >
          {request.approve_label}
        </button>
        <button
          onClick={onDeny}
          className="flex-1 text-sm py-1.5 px-3 rounded-lg font-medium bg-zinc-800 hover:bg-zinc-700 text-zinc-300 transition-colors"
        >
          {request.deny_label}
        </button>
      </div>
    </div>
  )
}
```

---

## 9. DB Additions for Trace History

Add one new table so users can replay past task traces:

```sql
-- Add to your 05_db_schema_data_model.md schema

CREATE TABLE trace_events (
  id          BIGSERIAL PRIMARY KEY,
  task_id     UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  event_type  VARCHAR(50) NOT NULL,
  step_id     VARCHAR(100),
  payload     JSONB NOT NULL,
  created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_trace_events_task_id ON trace_events(task_id);
CREATE INDEX idx_trace_events_task_created ON trace_events(task_id, created_at);
```

This enables:
- Replaying a past task's execution visually
- Debugging failed tasks
- Future analytics (which steps fail most often, average step durations)

---

## 10. Ready-Made Libraries to Use (Don't Build from Scratch)

### 10.1 Use Immediately

| Library | What to use from it | Link |
|---|---|---|
| **agenttrace-ui** | Timeline, approval gates, reasoning traces — literally built for this | [Vercel Community](https://community.vercel.com/t/agenttrace-ui-human-in-the-loop-approval-gates-and-reasoning-traces-built-on-ai-sdk-v6/37962) |
| **shadcn/ui** | Accordion (for expandable steps), Badge (status), Progress, Separator | [shadcn.com](https://ui.shadcn.com) |
| **Framer Motion** | `AnimatePresence` for step enter/exit, layout animations | [framer.com/motion](https://www.framer.com/motion/) |
| **@microsoft/fetch-event-source** | SSE with proper auth headers (solves EventSource auth problem) | [npm](https://www.npmjs.com/package/@microsoft/fetch-event-source) |
| **Mantine Timeline** | Pre-built timeline component if you want a faster start | [mantine.dev](https://mantine.dev/core/timeline/) |

### 10.2 Reference repos to study

| Repo | What it shows |
|---|---|
| `agent-ui` by Mastra | Full agent chat + trace panel patterns |
| `vercel/ai-chatbot` | SSE streaming into React, state management |
| `openai-agents-streaming-api` | FastAPI + SSE + OpenAI Agents SDK event types |

### 10.3 The @microsoft/fetch-event-source pattern

The native `EventSource` API doesn't support custom headers (cannot send `Authorization: Bearer ...`). Fix:

```typescript
import { fetchEventSource } from '@microsoft/fetch-event-source'

// Instead of: new EventSource(url)
// Use:
await fetchEventSource(`/api/v1/tasks/${taskId}/stream`, {
  headers: {
    'Authorization': `Bearer ${getAuthToken()}`,
    'Content-Type': 'text/event-stream'
  },
  onmessage(ev) {
    const data = JSON.parse(ev.data)
    dispatch({ type: ev.event.toUpperCase(), payload: data })
  },
  onerror(err) {
    console.error('SSE error', err)
    throw err // will trigger retry
  }
})
```

---

## 11. The Perplexity Effect — How to Nail the Visual Feel

What makes Perplexity Computer's trace panel feel premium is not complex. It's 5 things:

**1. Subtle entry animations.** Each new step slides in from the top with ~0.25s ease-out. Steps don't just appear — they arrive. Use `animate-step-enter` from your Tailwind config.

**2. The spinning ring indicator.** The `running` state uses a partial dashed circle spinning continuously. Not a full spinner — a partial arc (60% fill, 40% gap). This looks more elegant than a solid spinner.

**3. Instant checkmark on completion.** When a step completes, the spinning ring snaps to a checkmark with a brief scale-up animation (200ms). This gives visceral satisfaction.

**4. Glass morphism card.** The trace panel uses `bg-zinc-900/80 backdrop-blur` — slightly transparent with blur. This makes it feel like it floats above the content rather than being bolted on.

**5. Monospace log text.** Inside expandable steps, use `font-mono text-xs` for log messages. This signals technical depth and precision. Users trust it more.

---

## 12. Integration Into Nexus Conversation Flow

The trace panel should appear **inline within the conversation**, not in a separate panel or sidebar. This is the Devin-style approach — trace updates appear as the agent works, woven into the chat stream.

```
User: "Extract leads from LinkedIn and send connection requests to CTOs"

Nexus: "Got it, starting now..."

[AgentTracePanel renders here, expanding as steps complete]
✅ Understood your request
✅ Checking memory for past LinkedIn attempts  
⟳  Searching for CTO profiles matching criteria...
○  Preparing connection messages
○  Sending requests

Nexus: "Done! Found 47 CTO profiles and queued 47 connection requests. Saved to leads.csv."
```

After task completion, the trace panel collapses to a single "View execution trace" link. Users can expand it to see the full trace or leave it collapsed.

---

## 13. What NOT to Build

- **No raw reasoning token display.** Don't show the LLM's thinking tokens ("Hmm, I should consider…"). Show only tool actions and results.
- **No live DOM screenshots from browser automation.** Don't try to stream a live browser preview. It's complex, slow, and rarely useful for the user's actual needs.
- **No infinite log scrolling.** Cap expandable step logs at 20 lines with a "View full log" option. 
- **No WebSocket for trace events.** You already use WebSocket for voice. Keep SSE for trace. Don't conflate them.
- **No global trace panel sidebar.** Keep the trace inline with the conversation, not a permanent sidebar element. Sidebars get ignored.

---

## 14. Implementation Sequence (Add to 30-Day Plan)

| When | What to build |
|---|---|
| Week 2 Day 10 | Backend: `TaskTracer` class + `TaskEventQueue` + heartbeat logic |
| Week 2 Day 11 | Backend: SSE endpoint `/tasks/:id/stream` with FastAPI |
| Week 2 Day 12 | Frontend: `useTaskStream` hook + basic step list rendering |
| Week 2 Day 13 | Frontend: `StepIcon` with all animation states |
| Week 2 Day 14 | Frontend: `AgentTracePanel` full component + Tailwind animations |
| Week 3 Day 17 | Backend: Wire `TaskTracer` into `browser_use_client.py` |
| Week 3 Day 19 | Backend: Wire `TaskTracer` into `windows_agent_client.py` |
| Week 3 Day 20 | Frontend: `ApprovalGate` component for sensitive actions |
| Week 4 Day 23 | DB: `trace_events` table + history replay endpoint |

---

## 15. Summary

| Layer | What you're building |
|---|---|
| Backend events | `TaskTracer` class, 8 event types, heartbeat, SSE endpoint |
| Transport | SSE (not WebSocket) via `sse-starlette` in FastAPI |
| Frontend state | `useTaskStream` reducer hook consuming SSE events |
| UI components | `AgentTracePanel`, `StepIcon`, `ApprovalGate`, `ElapsedTimer` |
| Animations | Tailwind keyframes: spin, pulse-ring, check-appear, shake, step-enter |
| Libraries to use | `agenttrace-ui`, `shadcn/ui`, `framer-motion`, `@microsoft/fetch-event-source` |
| Privacy rule | Never expose raw reasoning tokens — only actions and results |
| UX rule | No silent waiting beyond 2 seconds — emit heartbeats |
