# 05 – DB Schema / Data Model

This document defines the relational data model for the voice-first assistant. It is **design-first**: tables and relationships are specified before implementation, so backend code, AI tools, and analytics all have a single source of truth. Modern schema design guidance recommends modeling entities and relationships explicitly, normalizing where needed, and keeping the schema aligned with concrete use cases.[web:307][web:304]

---

## 1. Design goals

- Support **login-enabled users** and per-user context.
- Track **sessions**, **conversation turns**, **tasks**, and **tool runs**.
- Store **memory items** (profile, session, task-related).
- Store **output documents** (markdown reports, summaries).
- Be ready for future **vector retrieval** without forcing vector DB choices into MVP.[web:175][web:178][web:272]

Assume a relational DB such as Postgres.

---

## 2. Entity list

Core entities:

- `users`
- `sessions`
- `conversation_turns`
- `tasks`
- `task_events` (optional event log)
- `tool_runs`
- `memory_items`
- `output_documents`

Future / optional entities:

- `embeddings` (for vector search)
- `integration_tokens` (for external APIs/tools)

---

## 3. Tables and fields

### 3.1 `users`

Represents a unique human user.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | UUID | PK | Primary ID |
| email | VARCHAR(255) | UNIQUE, NOT NULL | Login identifier |
| password_hash | VARCHAR | NOT NULL | Or null if using OAuth only |
| display_name | VARCHAR(100) | NULL | User-facing name |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | Default now |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | Updated on changes |
| settings_json | JSONB | NULL | Per-user settings (language preferences, etc.) |

Indexes:
- unique index on `email`.

---

### 3.2 `sessions`

Represents a logical interaction session (voice/text) for a user.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | UUID | PK | Session ID |
| user_id | UUID | FK → users.id | NOT NULL |
| started_at | TIMESTAMP WITH TIME ZONE | NOT NULL | Session start |
| ended_at | TIMESTAMP WITH TIME ZONE | NULL | Session end |
| entry_mode | VARCHAR(20) | NOT NULL | e.g. `voice`, `text`, `mixed` |
| active_mode | VARCHAR(20) | NOT NULL | e.g. `assistant`, `browser`, `pc`, `research` |
| metadata | JSONB | NULL | Misc session data (device, client version) |

Indexes:
- index on `user_id`.
- index on `started_at`.

---

### 3.3 `conversation_turns`

Individual messages within a session.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | BIGSERIAL | PK | Turn ID |
| session_id | UUID | FK → sessions.id | NOT NULL |
| user_id | UUID | FK → users.id | NOT NULL |
| role | VARCHAR(20) | NOT NULL | `user` or `assistant` |
| input_mode | VARCHAR(20) | NOT NULL | `voice` or `text` |
| content | TEXT | NOT NULL | Raw text (already transcribed for voice) |
| language | VARCHAR(10) | NULL | `en`, `hi`, `mr`, etc. |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | Turn time |
| related_task_id | UUID | FK → tasks.id | NULL | Optional link when turn relates to a task |
| metadata | JSONB | NULL | e.g. STT provider, latency, tokens |

Indexes:
- index on `session_id`.
- index on `(session_id, created_at)` for chronological queries.

---

### 3.4 `tasks`

High-level tasks created by the assistant when using tools.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | UUID | PK | Task ID |
| user_id | UUID | FK → users.id | NOT NULL |
| session_id | UUID | FK → sessions.id | NULL | Session where task originated |
| type | VARCHAR(20) | NOT NULL | `browser`, `windows`, `research`, `mixed` |
| status | VARCHAR(20) | NOT NULL | `pending`, `running`, `succeeded`, `failed`, `cancelled` |
| title | VARCHAR(255) | NULL | Short label for task |
| description | TEXT | NULL | Long-form description / goal |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | Creation time |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | Update time |
| retry_count | INTEGER | NOT NULL DEFAULT 0 | Current retry attempt |
| max_retries | INTEGER | NOT NULL DEFAULT 3 | Allowed retries |
| trace_id | VARCHAR(100) | NULL | Correlation ID for Langfuse/tracing |
| idempotency_key | VARCHAR(100) | UNIQUE, NULL | Prevent duplicate runs |
| result_summary | TEXT | NULL | Short description of outcome |
| error_message | TEXT | NULL | Error details if failed |
| metadata | JSONB | NULL | Additional data (priority, tags, etc.) |

Indexes:
- index on `user_id`.
- index on `(user_id, created_at)`.

---

### 3.5 `task_events`

Optional fine-grained event log per task (state changes, confirmations, etc.).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | BIGSERIAL | PK | Event ID |
| task_id | UUID | FK → tasks.id | NOT NULL |
| event_type | VARCHAR(50) | NOT NULL | e.g. `created`, `started`, `tool_called`, `confirmation_required` |
| payload | JSONB | NULL | Event-specific data |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | Event time |

Indexes:
- index on `task_id`.

---

### 3.6 `tool_runs`

Represents each invocation of a tool (browser, windows agent, research, etc.).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | BIGSERIAL | PK | Tool run ID |
| task_id | UUID | FK → tasks.id | NOT NULL |
| tool_type | VARCHAR(30) | NOT NULL | `browser`, `windows_agent`, `research`, etc. |
| tool_name | VARCHAR(100) | NULL | Specific tool (e.g. `browser_use`, `pywinauto`, `search`) |
| status | VARCHAR(20) | NOT NULL | `pending`, `running`, `succeeded`, `failed` |
| requested_at | TIMESTAMP WITH TIME ZONE | NOT NULL | Time of call |
| completed_at | TIMESTAMP WITH TIME ZONE | NULL | Completion time |
| request_payload | JSONB | NULL | Raw parameters sent to tool |
| response_payload | JSONB | NULL | Raw response from tool |
| error_message | TEXT | NULL | If failed |

Indexes:
- index on `task_id`.
- index on `(task_id, tool_type)`.

---

### 3.7 `memory_items`

Stores persistent or semi-persistent memory across sessions.

Inspired by recent agent memory schema patterns, but simplified: each item is a typed memory record with metadata to support later vector search.[web:301][web:175][web:178]

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | UUID | PK | Memory ID |
| user_id | UUID | FK → users.id | NOT NULL |
| scope | VARCHAR(20) | NOT NULL | `profile`, `session`, `task`, `global` |
| session_id | UUID | FK → sessions.id | NULL | Only for session-scoped memories |
| task_id | UUID | FK → tasks.id | NULL | For task-scoped memories |
| label | VARCHAR(255) | NULL | Short description |
| content | TEXT | NOT NULL | Full memory text |
| importance | SMALLINT | NOT NULL | e.g. 1–5 rating |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | Creation time |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | Last update |
| metadata | JSONB | NULL | Tags like `topic`, `language`, `source`, etc. |

Indexes:
- index on `user_id`.
- index on `(user_id, scope)`.

---

### 3.8 `output_documents`

Markdown docs and other structured outputs created by the assistant (research reports, summaries, logs).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | UUID | PK | Document ID |
| user_id | UUID | FK → users.id | NOT NULL |
| task_id | UUID | FK → tasks.id | NULL | Task that produced this doc |
| title | VARCHAR(255) | NOT NULL | Document title |
| content_markdown | TEXT | NOT NULL | Full markdown |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | Creation time |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | Update time |
| metadata | JSONB | NULL | Additional info (doc type, tags) |

Indexes:
- index on `user_id`.
- index on `task_id`.

---

### 3.9 `embeddings` (future)

Optional table to store embeddings for memory items or documents.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | BIGSERIAL | PK | Embedding ID |
| user_id | UUID | FK → users.id | NOT NULL |
| source_table | VARCHAR(50) | NOT NULL | e.g. `memory_items`, `output_documents` |
| source_id | UUID | NOT NULL | ID in source table |
| vector | VECTOR or BYTEA | NOT NULL | Embedding (e.g., pgvector type)[web:175][web:178][web:272] |
| dim | INTEGER | NOT NULL | Embedding dimension |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | Creation time |
| metadata | JSONB | NULL | Extra info (model used, section, etc.) |

Indexes:
- index on `(user_id, source_table)`.
- vector index (e.g. `ivfflat`) on `vector` for ANN search.[web:175][web:178]

---

### 3.10 `integration_tokens` (future)

Tokens or credentials to external services (e.g. Gmail, Discord, etc.).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | UUID | PK | Token ID |
| user_id | UUID | FK → users.id | NOT NULL |
| provider | VARCHAR(50) | NOT NULL | e.g. `google`, `discord` |
| access_token | TEXT | NOT NULL | Encrypted at rest |
| refresh_token | TEXT | NULL | Encrypted |
| expires_at | TIMESTAMP WITH TIME ZONE | NULL | Expiry time |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | Creation |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL | Last update |
| metadata | JSONB | NULL | Scopes, account IDs, etc. |

---

### 3.11 `usage_logs`

Tracks resource consumption (tokens, API calls) for budgeting and rate limiting.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | BIGSERIAL | PK | Log ID |
| user_id | UUID | FK → users.id | NOT NULL |
| task_id | UUID | FK → tasks.id | NULL |
| provider | VARCHAR(50) | NOT NULL | e.g. `openai`, `gemini`, `browser_use` |
| model_name | VARCHAR(100) | NULL | Specific model used |
| tokens_in | INTEGER | NULL | Prompt tokens |
| tokens_out | INTEGER | NULL | Completion tokens |
| cost_estimated | DECIMAL(10,5) | NULL | Estimated USD cost |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | Log time |

---

---

## 4. Relationships (ER overview)

- `users` 1↦N `sessions`
- `users` 1↦N `tasks`
- `users` 1↦N `memory_items`
- `users` 1↦N `output_documents`
- `sessions` 1↦N `conversation_turns`
- `sessions` 1↦N `tasks` (optional)
- `tasks` 1↦N `task_events`
- `tasks` 1↦N `tool_runs`
- `tasks` 1↦N `output_documents`
- `sessions` 1↦N `memory_items` (session scope)
- `tasks` 1↦N `memory_items` (task scope)
- `memory_items` / `output_documents` 1↦N `embeddings` (future)

This model aligns with recent agent memory patterns where you have a central `memory_items` table with scopes and metadata, plus a separate `embeddings` table for semantic search.[web:301][web:175][web:178]

---

## 5. Practical considerations

- Start with a single relational DB (e.g. Postgres), following data model guidance that emphasizes correct relationships over premature sharding.[web:307]
- Add `embeddings` and vector indexes only when you implement non-trivial RAG; until then, you can derive context from recent conversation turns and structured memory only.[web:175][web:178][web:272]
- Use enum types or constrained strings for `type`, `status`, `scope` to prevent inconsistent values.
- Keep `metadata` as JSONB for flexibility, but rely on relational columns for core logic.

This schema is intentionally conservative and should be adequate for early product stages while supporting later growth.
