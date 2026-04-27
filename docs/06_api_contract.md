# 06 – API Contract

This document defines the **external API contract** for the assistant’s backend. It covers:

- Auth & user endpoints
- Session & conversation endpoints
- Task & tool endpoints
- Local Windows agent API shape

The contract follows REST and OpenAPI-style best practices: resource-oriented URLs, clear verbs, normalized payloads, and explicit error shapes.[web:298][web:299][web:296][web:308]

---

## 1. General principles

- Transport: HTTPS for cloud APIs; HTTP/WebSocket on `localhost` for the Windows agent.
- Format: JSON for request/response bodies (except streaming channels).
- Versioning: prefix URLs with `/api/v1/`.
- Auth: Bearer tokens (JWT or opaque) in `Authorization` header for user-bound endpoints.
- Errors: use consistent error objects: `{ "error": { "code": "...", "message": "...", "details": {...} } }`.

---

## 2. Auth & user endpoints

### 2.1 `POST /api/v1/auth/register`

Registers a new user.

**Request body**
```json
{
  "email": "user@example.com",
  "password": "string",
  "display_name": "Aniket"
}
```

**Response 201**
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "display_name": "Aniket",
    "created_at": "2026-04-24T10:00:00Z"
  },
  "token": "jwt-or-opaque-token"
}
```

### 2.2 `POST /api/v1/auth/login`

Authenticates a user.

**Request** same shape as register (minus display name).  
**Response 200** same as register.

### 2.3 `GET /api/v1/me`

Returns current authenticated user.

---

## 3. Session & conversation endpoints

### 3.0 `GET /api/v1/stream/token`

Fetches credentials for the frontend to connect to GetStream Chat and Video.

**Response 200**
```json
{
  "api_key": "string",
  "token": "jwt-token",
  "user_id": "string"
}
```

### 3.1 `POST /api/v1/sessions`

Create a new conversation session.

**Request**
```json
{
  "entry_mode": "voice",   // or "text"
  "active_mode": "assistant"
}
```

**Response 201**
```json
{
  "session": {
    "id": "uuid",
    "user_id": "uuid",
    "entry_mode": "voice",
    "active_mode": "assistant",
    "started_at": "2026-04-24T10:00:00Z"
  }
}
```

### 3.2 `POST /api/v1/sessions/{session_id}/messages`

Send a text message into a session (voice text or typed).

**Request**
```json
{
  "role": "user",
  "content": "Open my Gmail and summarize the last 5 unread emails.",
  "input_mode": "text"
}
```

**Response 200**
```json
{
  "turn": {
    "id": 123,
    "session_id": "uuid",
    "role": "assistant",
    "content": "Here is a summary of your last 5 unread emails...",
    "created_at": "2026-04-24T10:00:02Z"
  },
  "tasks": [
    {
      "id": "task-uuid",
      "type": "browser",
      "status": "running"
    }
  ]
}
```

### 3.3 `GET /api/v1/sessions/{session_id}`

Fetch session metadata and recent conversation.

### 3.4 `GET /api/v1/sessions/{session_id}/messages`

List conversation turns for a session.

---

## 4. Task & tool endpoints

### 4.1 `GET /api/v1/tasks/{task_id}`

Get task details and status.

**Response 200**
```json
{
  "task": {
    "id": "task-uuid",
    "user_id": "uuid",
    "session_id": "uuid",
    "status": "succeeded",
    "title": "Summarize last 5 unread emails",
    "trace_id": "langfuse-trace-uuid",
    "result_summary": "5 emails summarized",
    "created_at": "...",
    "updated_at": "..."
  },
  "tool_runs": [
    {
      "id": 47,
      "tool_type": "browser",
      "tool_name": "browser_use",
      "status": "succeeded",
      "requested_at": "...",
      "completed_at": "..."
    }
  ]
}
```

### 4.2 `GET /api/v1/tasks`

List recent tasks for the authenticated user.

Query params:
- `type` (optional)
- `status` (optional)
- `limit`, `offset`

---

## 5. Output document endpoints

### 5.1 `GET /api/v1/tasks/{task_id}/documents`

List documents created for a task.

**Response 200**
```json
{
  "documents": [
    {
      "id": "doc-uuid",
      "title": "Research summary: Best cooling pad options",
      "created_at": "..."
    }
  ]
}
```

### 5.2 `GET /api/v1/documents/{document_id}`

Fetch a specific document.

**Response 200**
```json
{
  "document": {
    "id": "doc-uuid",
    "task_id": "task-uuid",
    "title": "Research summary: Best cooling pad options",
    "content_markdown": "# Summary...",
    "created_at": "..."
  }
}
```

---

## 6. Local Windows agent API contract

The local Windows agent runs on the user’s machine and listens on `http://127.0.0.1:{PORT}`. Communication can be HTTP or WebSocket; here we define an HTTP JSON contract for clarity.

### 6.1 Auth model

- Local agent trusts only connections from localhost.
- For production, agent should require a local shared secret or token passed via header: `X-Agent-Token: <token>`.

### 6.2 Request envelope

All commands follow a common structure:

```json
{
  "action": "create_folder",      // action name
  "request_id": "uuid",           // optional tracking
  "params": { ... }                // action-specific parameters
}
```

### 6.3 Response envelope

```json
{
  "request_id": "uuid",
  "status": "succeeded",          // or "failed"
  "result": { ... },
  "error": {
    "code": "...",
    "message": "..."
  }
}
```

### 6.4 Example actions

#### 6.4.1 `POST /agent/actions` – create folder

**Request**
```json
{
  "action": "create_folder",
  "request_id": "123",
  "params": {
    "path": "C:/Users/Aniket/Desktop/Client Reports"
  }
}
```

**Response**
```json
{
  "request_id": "123",
  "status": "succeeded",
  "result": {
    "path": "C:/Users/Aniket/Desktop/Client Reports"
  },
  "error": null
}
```

#### 6.4.2 `POST /agent/actions` – open app

```json
{
  "action": "open_app",
  "request_id": "124",
  "params": {
    "app_name": "Visual Studio Code"
  }
}
```

#### 6.4.3 `POST /agent/actions` – type text in active window

```json
{
  "action": "type_text",
  "request_id": "125",
  "params": {
    "text": "npm run dev",
    "send_enter": true
  }
}
```

The Windows agent implementation will map these commands to `pywinauto` operations (Application start/connect, UIA control actions, `keyboard.send_keys`, etc.), following the capabilities documented in pywinauto GitHub and docs.[web:52][web:279][web:283]

---

## 7. Streaming & voice

Voice streaming is primarily handled by Stream Video and OpenAI Realtime integration, orchestrated by Next.js API Routes.

Relevant references:
- Stream Video AI voice assistant docs.
- OpenAI Realtime SDK docs.

For the purposes of this API contract, the primary backend surface for voice is the `POST /api/stream/voice-session` endpoint, which creates the call and returns the credentials. Audio transport follows Stream's WebRTC protocol.

---

## 8. Error model

Standard error response:

```json
{
  "error": {
    "code": "TASK_NOT_FOUND",
    "message": "Task with id task-uuid does not exist",
    "details": {}
  }
}
```

API design guides recommend consistent error shapes with stable codes and human-readable messages; follow this pattern for all endpoints.[web:298][web:299][web:296][web:308]

---

## 9. Future extensions

- Add specific endpoints for research jobs (submit job, get status, get report).
- Add endpoints for managing memory items (list, pin, delete) once memory UI exists.
- Add OpenAPI spec file (`openapi.yaml`) generated from these contracts for tooling and client generation.[web:308][web:309]

This API contract should evolve alongside the PRD and architecture document, but changes must be explicit and versioned.
