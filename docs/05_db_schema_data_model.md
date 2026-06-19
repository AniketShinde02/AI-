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


# Appendix: Firestore Hybrid Data Strategy

# nexus-firestore-data-strategy.md

## Nexus Firestore Data Strategy

This document defines the production-grade data architecture for Nexus using Firebase Auth and Cloud Firestore as the canonical backend, plus a local cache/storage layer for performance, offline behavior, and device-specific state. The design is intentionally hybrid: Firestore is the source of truth for anything that must survive device loss and sync across devices, while the local layer exists only for latency, offline UX, streaming state, and machine-bound secrets.

---

## 1. Architecture Overview

### 1.1 Why Firestore

Firestore is the correct default database for Nexus because Nexus is not a single-device note app. It is a multi-device, authenticated, real-time assistant with conversations, memory, tasks, voice state, and AI orchestration. Firestore is optimized for large collections of small documents, supports hierarchical collections and subcollections, and gives you real-time listeners plus offline persistence out of the box [web:46][web:51].

Firestore also plays well with Firebase Auth. Security Rules can use `request.auth.uid` to enforce strict user isolation, which is exactly what a personal assistant needs because users must only read and write their own state [web:40][web:87]. That matters more than raw SQL elegance. If the access model is wrong, the whole product is unsafe.

Firestore has tradeoffs. It is not relational, joins are your problem, document size is capped at 1 MiB, and hot documents can become a performance problem if you keep hammering the same record with frequent writes [web:86][web:27]. So the architecture must be deliberate: small documents, denormalized where needed, subcollections for unbounded sequences, and strict write patterns to avoid hot spots.

### 1.2 Why Hybrid Local-First

Local-first does **not** mean local-only. It means the app should feel instant and resilient even when the network is flaky, while the authoritative state lives in Firestore. Firebase already supports offline persistence for actively used data and syncs local changes when the device reconnects [web:51][web:61]. That is useful, but it is not enough by itself for a product like Nexus.

The local layer should hold only:

- transient UI state,
- pending writes,
- streaming audio and partial responses,
- session caches,
- device-specific secrets,
- and a small working set of recently used data.

Everything durable goes to Firestore. This gives you consistent cross-device behavior, easier debugging, easier deletion, and a sane recovery story. The brutal truth: if you make local storage the main database, you will create sync hell the moment users switch devices or reinstall.

### 1.3 Canonical Source of Truth

Firestore is the canonical source of truth for:

- identity-linked user profile,
- preferences and tone,
- conversation history,
- memory,
- tasks and reminders,
- AI state snapshots,
- subscription and entitlement metadata,
- and audit-friendly state transitions.

Local data is never allowed to redefine canonical state. Local data can only:

- accelerate reads,
- support offline edits,
- hold speculative state until sync,
- or store machine-only secrets.

This distinction matters because the assistant must be consistent. If the local machine says the user likes concise answers but Firestore says detailed answers, Firestore wins. Period.

### 1.4 DB-for-Truth vs Local-for-Speed

Use this rule:

- **DB for truth**: anything you need after reinstall, on another device, or after a crash.
- **Local for speed**: anything that improves responsiveness but can be recomputed, resynced, or discarded.

If data is user-facing and durable, it belongs in Firestore. If data is ephemeral, device-bound, or too expensive to fetch repeatedly, keep a local copy. This is the clean split. Anything else becomes architectural mush.

### 1.5 Sync Philosophy

The sync philosophy should be:

1. Write locally first for immediate UX when appropriate.
2. Queue the write with an operation ID.
3. Sync to Firestore with retries and idempotency.
4. Reconcile remote acknowledgments with local optimistic state.
5. Merge or overwrite based on object semantics.
6. Never silently lose a user action.

The key is not “offline support” as a feature checkbox. It is predictable state reconciliation. Users will forgive a delayed sync. They will not forgive disappearing messages or duplicate tasks.

### 1.6 Event-Driven Architecture

Nexus should treat Firestore as the system of record but not as the only execution engine. Use an event-driven layer in the application server or Cloud Functions for:

- memory extraction,
- summarization,
- embeddings generation,
- reminder scheduling,
- subscription updates,
- and message lifecycle transitions.

Write minimal canonical records synchronously, then emit events or queue jobs for derived state. That keeps the user-facing path fast and reduces contention. For example, when a voice turn finishes, write the final message to Firestore immediately, then enqueue summarization and memory extraction asynchronously.

### 1.7 Latency Considerations

Voice assistants live and die by latency. You cannot afford a slow persistence layer on the critical path. Firestore reads should be minimized for hot flows:

- current session,
- current conversation,
- current AI state,
- last few turns,
- latest stream state.

Keep the current session documents tiny and targeted. Do not read giant documents just to display a chat screen. Firestore pagination should use cursors, not offsets [web:80][web:75]. Listener scopes must be narrow so you do not turn every screen into a firehose.

### 1.8 Cost Considerations

Firestore cost is dominated by reads, writes, index entries, and document fan-out. The architecture should aggressively reduce:

- unnecessary listeners,
- oversized documents,
- repeated polling,
- and broad collection scans.

Avoid storing raw high-volume logs in Firestore if they can be summarized or moved to object storage. Avoid hot counters in one document; use sharded counters or batched counters if needed [web:91][web:85]. Keep memory documents compact, and chunk large AI state into multiple documents. Large documents are a bill and performance problem waiting to happen [web:86][web:92].

### 1.9 Scalability Considerations

Firestore can scale well if the data model respects its constraints. It can also become a mess if you shove relational thinking into it. The design here assumes:

- many users,
- many sessions per user,
- high message volume,
- many small writes,
- many reads from the current session,
- and occasional fan-out to memory and analytics.

That means you need:

- per-user partitioning,
- subcollections for unbounded streams,
- strict field naming discipline,
- and document size guardrails.

The architecture must be ready to grow from 1k users to 1M+ without rewriting the product from scratch.

---

## 2. Data Classification Matrix

Use this matrix as the policy layer for all storage decisions.

| Data Type                            | Store Locally Only |              Sync to Firestore |          Encrypt at Rest | Cache Locally | Ephemeral Memory | Long-Term Memory |                 Must Never Persist | Rationale                                                                             |
| ------------------------------------ | -----------------: | -----------------------------: | -----------------------: | ------------: | ---------------: | ---------------: | ---------------------------------: | ------------------------------------------------------------------------------------- |
| UI view state                        |                Yes |                             No |                       No |           Yes |              Yes |               No |                                 No | Purely presentation state; syncing this is pointless.                                 |
| Draft user input                     |           Optional |                       Optional |                       No |           Yes |              Yes |               No |                                 No | Useful for recovery, but do not persist if the user did not intend to save it.        |
| Current assistant streaming response |                Yes |                             No |                       No |           Yes |              Yes |               No |                                 No | Streaming state is transient and should not become permanent history until finalized. |
| Partial ASR transcript               |                Yes |                             No |                 Optional |           Yes |              Yes |               No |                  Yes, if raw audio | Keep only until turn finalization unless you need debugging with explicit consent.    |
| Final conversation turns             |                 No |                            Yes |                       No |           Yes |              Yes |              Yes |                                 No | These are core user history and should sync across devices.                           |
| User profile                         |                 No |                            Yes | Yes for sensitive fields |           Yes |               No |              Yes |                                 No | Profile is the assistant’s personalization backbone.                                 |
| Tone / personality preferences       |                 No |                            Yes |                    Maybe |           Yes |               No |              Yes |                                 No | Must survive device changes or the assistant forgets the user’s style.               |
| Short-term session memory            |                 No |                            Yes |                       No |           Yes |              Yes |               No |                                 No | Session memory supports continuity during a live conversation.                        |
| Long-term memory facts               |                 No |                            Yes |  Yes for sensitive facts |           Yes |               No |              Yes | Sensitive facts should be excluded | Durable facts are core to personalization.                                            |
| Sensitive PII                        |                 No | Yes only if strictly necessary |                      Yes |       Minimal |               No |            Maybe |              Prefer not to persist | Minimize exposure. Use explicit retention rules.                                      |
| Passwords / auth secrets             |                 No |                             No |                      Yes |            No |               No |               No |                                Yes | Never store in Firestore documents. Use provider auth or secure storage.              |
| OAuth refresh tokens                 |                 No |    Prefer backend secure store |                      Yes |            No |               No |               No |                        Ideally yes | Firestore is not a secrets vault.                                                     |
| Device token / pairing secret        |                 No |  Maybe encrypted metadata only |                      Yes |           Yes |               No |               No |                                 No | Device-bound trust material belongs in secure local storage.                          |
| Reminder definitions                 |                 No |                            Yes |                       No |           Yes |               No |              Yes |                                 No | They must sync and survive reinstall.                                                 |
| Analytics events                     |                 No |                            Yes |                       No |         Maybe |               No |  Yes, summarized |                                 No | High-level events can be useful; raw noise should not bloat the DB.                   |
| Voice audio chunks                   |                Yes |                     Usually no |                 Optional |           Yes |              Yes |               No |                         Prefer yes | Raw audio is heavy and privacy-sensitive. Keep only with explicit need.               |
| Embedding vectors                    |                 No |                            Yes |                    Maybe |           Yes |               No |              Yes |                                 No | Needed for semantic retrieval and memory search.                                      |
| Safety flags                         |                 No |                            Yes |                       No |           Yes |               No |              Yes |                                 No | Safety state must be shared and auditable.                                            |
| Cached AI state                      |                Yes |            Maybe snapshot only |                       No |           Yes |              Yes |               No |                                 No | The current agent state can be local; the durable checkpoint goes to Firestore.       |

### Classification Rules

- If it is needed after reinstall, it is not local-only.
- If it changes every second and is only useful during the live interaction, it is ephemeral.
- If it affects identity, memory, billing, or permissions, it must sync.
- If it can be reconstructed from canonical records, cache it locally instead of treating it as truth.
- If it is a secret, assume Firestore is the wrong place unless encrypted and strictly necessary.

---

## 3. Firestore Collection Design

The cleanest design is a top-level collection model with selected subcollections for unbounded sequences. That avoids giant arrays, hot documents, and unreadable documents. Firestore is optimized for collections of small documents, not “one mega document per user” nonsense [web:46][web:86].

### 3.1 Path Conventions

Recommended paths:

- `users/{uid}`
- `users/{uid}/devices/{deviceId}`
- `conversations/{conversationId}`
- `conversations/{conversationId}/messages/{messageId}`
- `conversations/{conversationId}/events/{eventId}`
- `users/{uid}/memory/{memoryId}`
- `users/{uid}/tasks/{taskId}`
- `users/{uid}/reminders/{reminderId}`
- `users/{uid}/device_sessions/{sessionId}`
- `users/{uid}/analytics/{eventId}`
- `users/{uid}/subscriptions/{subscriptionId}`
- `users/{uid}/ai_state/{stateId}`
- `users/{uid}/voice_preferences/{profileId}`
- `users/{uid}/emotional_context/{contextId}`
- `users/{uid}/safety_flags/{flagId}`
- `users/{uid}/cache_metadata/{cacheKey}`

You can also mirror some collections globally and index by `userId`, but for a single-user access pattern, nesting under `users/{uid}` is usually cleaner. It reduces accidental cross-user queries and makes Security Rules simpler.

---

### 3.2 `users`

#### Purpose

The user document is the account-level root. It stores identity-adjacent profile metadata, preferences, settings, and entitlements.

#### Example Document

```json
{
  "uid": "google_uid_123",
  "email": "aniket@example.com",
  "displayName": "Aniket",
  "photoURL": "https://...",
  "plan": "pro",
  "status": "active",
  "createdAt": "2026-05-10T10:00:00Z",
  "updatedAt": "2026-05-10T10:00:00Z",
  "lastLoginAt": "2026-05-10T10:04:00Z",
  "timezone": "Asia/Kolkata",
  "locale": "en-IN",
  "defaultTone": "concise",
  "defaultStyle": "direct",
  "memoryPolicy": {
    "allowLongTermMemory": true,
    "allowEmotionalMemory": true,
    "allowVoiceRetention": false
  },
  "featureFlags": {
    "semanticMemory": true,
    "offlineMode": true
  },
  "limits": {
    "messageLimit": 50000,
    "memoryLimit": 1000
  }
}
```

#### Required Fields

- `uid` string
- `email` string
- `createdAt` timestamp
- `updatedAt` timestamp
- `status` string
- `plan` string

#### Optional Fields

- `displayName`
- `photoURL`
- `timezone`
- `locale`
- `defaultTone`
- `defaultStyle`
- `memoryPolicy`
- `featureFlags`
- `limits`
- `lastLoginAt`

#### Field Types

- strings for identity and enums
- timestamps for lifecycle tracking
- maps for nested preferences
- booleans for feature switches

#### Indexing Strategy

- Single-field index on `uid`
- Single-field index on `plan`
- Single-field index on `status`
- Single-field index on `lastLoginAt`
- If querying by locale/plan, add composite indexes only when needed

#### Read/Write Frequency

- Read on app startup
- Read on auth state change
- Write on profile edits and plan changes
- Low frequency, but very high importance

#### Security Implications

- Users can only read/write their own user document.
- Sensitive flags should be server-authoritative if they affect billing or safety.
- Do not allow arbitrary client writes to plan or entitlement fields.

---

### 3.3 `conversations`

#### Purpose

A conversation represents a long-lived thread or context boundary, which may span multiple sessions.

#### Example Document

```json
{
  "conversationId": "conv_001",
  "uid": "google_uid_123",
  "title": "Daily planning",
  "mode": "voice",
  "status": "active",
  "createdAt": "2026-05-10T10:00:00Z",
  "updatedAt": "2026-05-10T10:10:00Z",
  "lastMessageAt": "2026-05-10T10:10:00Z",
  "lastSummaryAt": "2026-05-10T10:05:00Z",
  "pinned": false,
  "archived": false,
  "contextVersion": 12
}
```

#### Required Fields

- `conversationId`
- `uid`
- `status`
- `createdAt`
- `updatedAt`
- `lastMessageAt`

#### Optional Fields

- `title`
- `mode`
- `lastSummaryAt`
- `pinned`
- `archived`
- `contextVersion`

#### Indexing Strategy

- `uid + lastMessageAt desc`
- `uid + archived + updatedAt desc`
- `uid + pinned + lastMessageAt desc`

#### Read/Write Frequency

- Read on conversation list view
- Read heavily on current conversation screen
- Write on new message, rename, archive, summary updates

#### Security Implications

- Only the owner can read/write.
- Avoid storing large message arrays here. Use a subcollection.

---

### 3.4 `messages`

#### Purpose

Messages are the atomic conversation units. Use a subcollection under each conversation.

#### Example Document

```json
{
  "messageId": "msg_001",
  "conversationId": "conv_001",
  "uid": "google_uid_123",
  "role": "user",
  "content": "Remind me tomorrow at 9 to call the client.",
  "contentType": "text",
  "inputMode": "voice",
  "status": "final",
  "createdAt": "2026-05-10T10:01:00Z",
  "updatedAt": "2026-05-10T10:01:05Z",
  "clientMessageId": "local_op_9f1",
  "replyToMessageId": null,
  "tokens": 18,
  "language": "en-IN",
  "partial": false,
  "attachments": [],
  "tags": ["reminder", "task"]
}
```

#### Required Fields

- `messageId`
- `conversationId`
- `uid`
- `role`
- `content`
- `status`
- `createdAt`

#### Optional Fields

- `contentType`
- `inputMode`
- `updatedAt`
- `clientMessageId`
- `replyToMessageId`
- `tokens`
- `language`
- `partial`
- `attachments`
- `tags`

#### Indexing Strategy

- `uid + createdAt desc`
- `conversationId + createdAt asc`
- `conversationId + status + createdAt desc`
- `clientMessageId` unique per user to dedupe optimistic writes

#### Read/Write Frequency

- Very high read frequency in active conversations
- Very high write frequency in live chat and voice sessions

#### Security Implications

- This is user-owned data only.
- Final messages should be immutable except for moderation or correction through privileged service paths.
- Partial messages may be mutable until finalized, but final messages should be append-only.

---

### 3.5 `memory`

#### Purpose

Memory stores extracted facts, preferences, user-specific workflows, and summaries.

#### Example Document

```json
{
  "memoryId": "mem_001",
  "uid": "google_uid_123",
  "scope": "profile",
  "category": "preference",
  "importance": 5,
  "content": "User prefers concise, direct answers.",
  "source": "extracted",
  "sourceConversationId": "conv_001",
  "sourceMessageIds": ["msg_010", "msg_011"],
  "createdAt": "2026-05-10T10:05:00Z",
  "updatedAt": "2026-05-10T10:05:00Z",
  "expiresAt": null,
  "embeddingStatus": "ready",
  "embeddingModel": "text-embedding-3-small",
  "metadata": {
    "topic": "communication_style",
    "confidence": 0.94,
    "language": "en"
  }
}
```

#### Required Fields

- `memoryId`
- `uid`
- `scope`
- `category`
- `importance`
- `content`
- `source`
- `createdAt`
- `updatedAt`

#### Optional Fields

- `sourceConversationId`
- `sourceMessageIds`
- `expiresAt`
- `embeddingStatus`
- `embeddingModel`
- `metadata`

#### Indexing Strategy

- `uid + scope + importance desc + createdAt desc`
- `uid + category + createdAt desc`
- `uid + expiresAt`
- `uid + embeddingStatus`
- If semantic search is implemented, keep vector metadata separate from vector payload

#### Read/Write Frequency

- Read often for prompt context injection
- Write after session summarization or explicit user memory commands
- Moderate frequency, but high value

#### Security Implications

- Users can read their own memory.
- Users can delete their own memory.
- Never store raw conversation dumps here.
- Sensitive facts should be excluded or encrypted depending on policy.

---

### 3.6 `embeddings_metadata`

#### Purpose

Store embedding metadata and references to vectors without bloating core memory docs.

#### Example Document

```json
{
  "embeddingId": "emb_001",
  "uid": "google_uid_123",
  "sourceType": "memory",
  "sourceId": "mem_001",
  "model": "text-embedding-3-small",
  "dimension": 1536,
  "status": "ready",
  "chunkCount": 1,
  "createdAt": "2026-05-10T10:05:10Z",
  "updatedAt": "2026-05-10T10:05:10Z",
  "vectorRef": "firestore_vector_external_or_local_ref",
  "metadata": {
    "chunkIndex": 0,
    "tokenCount": 23
  }
}
```

#### Required Fields

- `embeddingId`
- `uid`
- `sourceType`
- `sourceId`
- `model`
- `dimension`
- `status`
- `createdAt`

#### Optional Fields

- `chunkCount`
- `vectorRef`
- `metadata`

#### Indexing Strategy

- `uid + sourceType + sourceId`
- `uid + status + createdAt desc`

#### Security Implications

- Embeddings can leak semantic info; treat them as derived sensitive data.
- Keep references tightly scoped to owner identity.

---

### 3.7 `tasks`

#### Purpose

Tasks represent actionable work: reminders, browser tasks, desktop tasks, research jobs, mixed tasks.

#### Example Document

```json
{
  "taskId": "task_001",
  "uid": "google_uid_123",
  "conversationId": "conv_001",
  "type": "reminder",
  "status": "running",
  "title": "Call the client tomorrow at 9",
  "goal": "Create a reminder for tomorrow 9 AM",
  "resultSummary": null,
  "errorMessage": null,
  "priority": "normal",
  "createdAt": "2026-05-10T10:01:10Z",
  "updatedAt": "2026-05-10T10:01:20Z",
  "dueAt": "2026-05-11T09:00:00Z",
  "tags": ["reminder"],
  "metadata": {
    "sourceMessageId": "msg_001",
    "timezone": "Asia/Kolkata"
  }
}
```

#### Required Fields

- `taskId`
- `uid`
- `type`
- `status`
- `goal`
- `createdAt`
- `updatedAt`

#### Optional Fields

- `conversationId`
- `title`
- `resultSummary`
- `errorMessage`
- `priority`
- `dueAt`
- `tags`
- `metadata`

#### Indexing Strategy

- `uid + status + createdAt desc`
- `uid + type + createdAt desc`
- `uid + dueAt asc`
- `conversationId + createdAt desc`

#### Read/Write Frequency

- Moderate reads on task list
- Frequent writes during live execution

#### Security Implications

- Tasks often drive side effects. Use server-side updates for status changes to avoid manipulation.
- Do not trust client-written `resultSummary` for privileged workflows.

---

### 3.8 `reminders`

#### Purpose

Reminders are a specialized task class with schedule semantics.

#### Example Document

```json
{
  "reminderId": "rem_001",
  "uid": "google_uid_123",
  "taskId": "task_001",
  "title": "Call client",
  "scheduleType": "absolute",
  "scheduledFor": "2026-05-11T09:00:00Z",
  "timezone": "Asia/Kolkata",
  "status": "scheduled",
  "createdAt": "2026-05-10T10:01:20Z",
  "updatedAt": "2026-05-10T10:01:20Z",
  "snoozeCount": 0,
  "deliveryMode": "push"
}
```

#### Required Fields

- `reminderId`
- `uid`
- `title`
- `scheduleType`
- `scheduledFor`
- `status`
- `createdAt`

#### Optional Fields

- `taskId`
- `timezone`
- `snoozeCount`
- `deliveryMode`

#### Indexing Strategy

- `uid + status + scheduledFor asc`
- `uid + scheduledFor asc`

#### Security Implications

- Reminders should be server-scheduled if possible.
- Avoid client-only reminders if reliability matters.

---

### 3.9 `device_sessions`

#### Purpose

Track trusted devices, session health, and local agent or browser-device relationships.

#### Example Document

```json
{
  "deviceSessionId": "devsess_001",
  "uid": "google_uid_123",
  "deviceId": "device_abc123",
  "platform": "web",
  "browser": "chrome",
  "isTrusted": true,
  "lastSeenAt": "2026-05-10T10:10:00Z",
  "createdAt": "2026-05-10T10:00:00Z",
  "revokedAt": null,
  "ipHash": "hashed_ip_value",
  "metadata": {
    "userAgent": "Mozilla/5.0...",
    "locale": "en-IN"
  }
}
```

#### Required Fields

- `deviceSessionId`
- `uid`
- `deviceId`
- `platform`
- `lastSeenAt`
- `createdAt`

#### Optional Fields

- `browser`
- `isTrusted`
- `revokedAt`
- `ipHash`
- `metadata`

#### Indexing Strategy

- `uid + lastSeenAt desc`
- `uid + deviceId`
- `uid + isTrusted`

#### Security Implications

- Good for suspicious-session detection.
- Device trust must be revocable.

---

### 3.10 `analytics`

#### Purpose

Store minimal product analytics or operational events that must be queryable inside the app.

#### Example Document

```json
{
  "eventId": "evt_001",
  "uid": "google_uid_123",
  "eventType": "message_sent",
  "category": "usage",
  "createdAt": "2026-05-10T10:01:00Z",
  "sessionId": "sess_001",
  "conversationId": "conv_001",
  "metadata": {
    "mode": "voice",
    "latencyMs": 420
  }
}
```

#### Required Fields

- `eventId`
- `uid`
- `eventType`
- `category`
- `createdAt`

#### Optional Fields

- `sessionId`
- `conversationId`
- `metadata`

#### Indexing Strategy

- `uid + createdAt desc`
- `uid + category + createdAt desc`

#### Security Implications

- Keep this small. For serious analytics, export to a proper analytics pipeline.
- Do not dump verbose logs here.

---

### 3.11 `subscriptions`

#### Purpose

Store billing entitlement snapshots and provider references.

#### Example Document

```json
{
  "subscriptionId": "sub_001",
  "uid": "google_uid_123",
  "provider": "google_play",
  "status": "active",
  "plan": "pro",
  "currentPeriodStart": "2026-05-01T00:00:00Z",
  "currentPeriodEnd": "2026-06-01T00:00:00Z",
  "createdAt": "2026-05-01T00:00:00Z",
  "updatedAt": "2026-05-10T10:00:00Z",
  "providerCustomerId": "cust_123",
  "providerSubscriptionId": "sub_provider_456",
  "metadata": {
    "trial": false
  }
}
```

#### Required Fields

- `subscriptionId`
- `uid`
- `provider`
- `status`
- `plan`
- `createdAt`
- `updatedAt`

#### Optional Fields

- `currentPeriodStart`
- `currentPeriodEnd`
- `providerCustomerId`
- `providerSubscriptionId`
- `metadata`

#### Indexing Strategy

- `uid + status`
- `uid + plan`
- `provider + providerSubscriptionId`

#### Security Implications

- Strongly prefer server-authoritative writes.
- The client should read entitlements, not assert them.

---

### 3.12 `ai_state`

#### Purpose

Store serialized durable state that the orchestrator uses for resumed or multi-step flows.

#### Example Document

```json
{
  "stateId": "state_001",
  "uid": "google_uid_123",
  "conversationId": "conv_001",
  "taskId": "task_001",
  "stateType": "orchestration",
  "status": "active",
  "stateVersion": 3,
  "payload": {
    "step": "awaiting_confirmation",
    "candidateActions": ["create_reminder"]
  },
  "createdAt": "2026-05-10T10:01:15Z",
  "updatedAt": "2026-05-10T10:01:20Z",
  "expiresAt": "2026-05-10T12:01:20Z"
}
```

#### Required Fields

- `stateId`
- `uid`
- `stateType`
- `status`
- `stateVersion`
- `payload`
- `createdAt`
- `updatedAt`

#### Optional Fields

- `conversationId`
- `taskId`
- `expiresAt`

#### Indexing Strategy

- `uid + stateType + updatedAt desc`
- `uid + status + expiresAt`

#### Security Implications

- Keep payloads compact.
- Never store secrets or raw reasoning traces.

---

### 3.13 `voice_preferences`

#### Purpose

Store voice-specific user preferences like speed, assistant persona, speaking style, and language priority.

#### Example Document

```json
{
  "profileId": "voice_001",
  "uid": "google_uid_123",
  "preferredVoice": "female_1",
  "speakingRate": 1.0,
  "volume": 0.9,
  "languagePriority": ["en-IN", "hi-IN", "mr-IN"],
  "interruptibility": "high",
  "ttsProvider": "openai",
  "createdAt": "2026-05-10T10:00:00Z",
  "updatedAt": "2026-05-10T10:00:00Z"
}
```

#### Required Fields

- `profileId`
- `uid`
- `createdAt`
- `updatedAt`

#### Optional Fields

- `preferredVoice`
- `speakingRate`
- `volume`
- `languagePriority`
- `interruptibility`
- `ttsProvider`

#### Indexing Strategy

- `uid` unique
- `uid + updatedAt desc`

#### Security Implications

- Safe to sync.
- Do not overuse fields for runtime streaming state.

---

### 3.14 `emotional_context`

#### Purpose

Store short-lived or long-lived affective context if the product uses it.

#### Example Document

```json
{
  "contextId": "emo_001",
  "uid": "google_uid_123",
  "conversationId": "conv_001",
  "mood": "frustrated",
  "confidence": 0.72,
  "source": "inferred",
  "createdAt": "2026-05-10T10:02:00Z",
  "updatedAt": "2026-05-10T10:02:00Z",
  "expiresAt": "2026-05-10T12:02:00Z",
  "metadata": {
    "evidenceMessageIds": ["msg_001", "msg_002"]
  }
}
```

#### Required Fields

- `contextId`
- `uid`
- `mood`
- `confidence`
- `source`
- `createdAt`
- `updatedAt`

#### Optional Fields

- `conversationId`
- `expiresAt`
- `metadata`

#### Indexing Strategy

- `uid + conversationId`
- `uid + createdAt desc`
- `uid + expiresAt`

#### Security Implications

- Highly sensitive from a product ethics angle.
- Use it sparingly and avoid long-term retention unless user explicitly opts in.

---

### 3.15 `safety_flags`

#### Purpose

Track safety, policy, confirmation, abuse, and trust markers.

#### Example Document

```json
{
  "flagId": "safe_001",
  "uid": "google_uid_123",
  "flagType": "requires_confirmation",
  "severity": "medium",
  "status": "active",
  "reason": "Potentially destructive action requested",
  "createdAt": "2026-05-10T10:03:00Z",
  "updatedAt": "2026-05-10T10:03:00Z",
  "expiresAt": "2026-05-10T11:03:00Z",
  "metadata": {
    "taskId": "task_001"
  }
}
```

#### Required Fields

- `flagId`
- `uid`
- `flagType`
- `severity`
- `status`
- `reason`
- `createdAt`
- `updatedAt`

#### Optional Fields

- `expiresAt`
- `metadata`

#### Indexing Strategy

- `uid + status + createdAt desc`
- `uid + flagType + status`
- `uid + expiresAt`

#### Security Implications

- Usually server-side only.
- Users may read safety flags, but writes should be privileged.

---

### 3.16 `cache_metadata`

#### Purpose

Track cache keys, TTLs, versions, and invalidation state.

#### Example Document

```json
{
  "cacheKey": "conversation_conv_001_summary",
  "uid": "google_uid_123",
  "scope": "session",
  "version": 7,
  "etag": "abc123",
  "lastUpdatedAt": "2026-05-10T10:05:00Z",
  "expiresAt": "2026-05-10T10:35:00Z",
  "location": "local+firestore",
  "metadata": {
    "source": "summarizer"
  }
}
```

#### Required Fields

- `cacheKey`
- `uid`
- `scope`
- `version`
- `lastUpdatedAt`

#### Optional Fields

- `etag`
- `expiresAt`
- `location`
- `metadata`

#### Indexing Strategy

- `uid + cacheKey`
- `uid + scope + expiresAt`

#### Security Implications

- Low sensitivity, but useful for sync correctness.
- Never assume cache metadata is truth.

---

## 4. Local Database Layer

The local layer should not be a second source of truth. It is a performance and resilience layer.

### 4.1 IndexedDB vs SQLite vs localStorage

#### IndexedDB

Best for:

- web client cache,
- offline document caches,
- message drafts,
- pending sync queues,
- lightweight local state in the browser.

Pros:

- native to the web,
- large storage capacity,
- async API,
- works with Firestore offline-friendly architecture.

Cons:

- awkward API,
- schema discipline is your responsibility,
- not ideal for complex relational queries.

#### SQLite

Best for:

- desktop app shell,
- local Windows agent state,
- richer query needs,
- device-level queues,
- durable local indexing.

Pros:

- fast,
- structured,
- reliable,
- good for local task queues and audit logs.

Cons:

- extra plumbing on web,
- more maintenance,
- sync complexity if abused.

#### localStorage

Best for:

- tiny non-sensitive flags,
- last open tab,
- UI preferences that are not critical.

Pros:

- simple.

Cons:

- synchronous,
- tiny,
- fragile,
- not suitable for serious data.

### 4.2 Recommended Architecture

Use:

- **IndexedDB** for the web app cache and offline queue.
- **SQLite** for the local Windows agent and any desktop shell.
- **localStorage** only for ultra-small UI flags if necessary.

If you build a desktop shell later, SQLite should become the primary local persistence layer. For the browser, IndexedDB is the right default. Do not use localStorage for anything important. That is kindergarten-level engineering for adults.

### 4.3 Cache Eviction Policy

Use a tiered cache:

1. Hot data: current conversation, current AI state, current draft.
2. Warm data: recent conversations, recent tasks, recent memory snippets.
3. Cold data: archived sessions and older documents.

Eviction policy:

- TTL-based expiry for volatile data.
- LRU for session caches.
- Size limits by domain:
  - conversation cache,
  - memory cache,
  - audio cache,
  - embedding cache,
  - queue cache.

Rules:

- Never evict unsynced writes without first preserving them in a durable queue.
- Never evict current-turn streaming buffers mid-response.
- Never cache user secrets in plain text.

### 4.4 Session Memory

Session memory is local until finalized, then mirrored to Firestore. Use a rolling in-memory buffer for:

- latest user turn,
- assistant partial response,
- tool result,
- temporary clarification state.

After finalization:

- write final message,
- append session summary if needed,
- queue memory extraction,
- drop raw transient buffers locally.

### 4.5 Vector Cache

If semantic retrieval is used:

- store local vector cache for recent embeddings,
- store only references for older vectors,
- invalidate vector cache on content updates,
- refresh lazily after sync.

Do not compute embeddings synchronously in the critical path unless you enjoy latency regressions and angry users.

### 4.6 Audio Cache

Audio cache should be ephemeral:

- buffer live audio only long enough for streaming ASR/TTS,
- keep short retry windows,
- purge automatically after finalization,
- never persist raw audio by default.

If you must retain audio for debugging, require explicit opt-in, short TTL, and separate storage.

### 4.7 Streaming Cache

Streaming cache holds:

- partial assistant text,
- partial ASR transcript,
- interim tool progress,
- interrupted state.

It must support append, overwrite, and finalize semantics. Do not treat partial stream chunks as final messages.

### 4.8 Pending Sync Queue

The queue stores local operations until remote acknowledgment:

- message creates,
- task creates,
- reminder updates,
- memory upserts,
- settings changes.

Each item should include:

- `opId`
- `entityType`
- `entityId`
- `operationType`
- `payload`
- `createdAt`
- `attemptCount`
- `nextRetryAt`
- `status`

Queue rules:

- idempotency is mandatory,
- order matters for state transitions,
- retries must back off exponentially,
- dead-letter after a threshold,
- user-visible failure when recovery is impossible.

### 4.9 Optimistic Updates

Optimistic updates are fine if:

- the write is idempotent,
- the client stores operation IDs,
- the server can dedupe by `clientMessageId` or `opId`,
- rollback is possible.

Optimistic updates are not fine for:

- billing,
- entitlement,
- destructive actions,
- irreversible tasks,
- or anything that can corrupt shared state.

---

## 5. Sync Engine Design

### 5.1 Online/Offline Sync

The sync engine should maintain:

- local write queue,
- remote ack state,
- per-entity version numbers,
- and last sync timestamps.

Flow:

1. User performs an action.
2. Client writes local optimistic state.
3. Queue adds an operation.
4. Sync worker sends batched writes.
5. Firestore accepts and returns success.
6. Local queue marks operation complete.
7. Remote updates reconcile into local store.

### 5.2 Conflict Resolution

Use different conflict rules by entity type:

- **Messages**: append-only; dedupe by `clientMessageId`.
- **Tasks**: server-authoritative status transitions.
- **Settings**: last-write-wins with version checks.
- **Memory**: merge plus dedupe, not blind overwrite.
- **AI state**: versioned compare-and-swap.

LWW is acceptable for low-risk preferences. It is dangerous for task execution and memory because it can erase valid state. Use merge where the object model is compositional.

### 5.3 Device Reconciliation

When multiple devices are active:

- prefer deterministic version fields,
- keep `updatedAt` plus `stateVersion`,
- store `lastWriterDeviceId`,
- resolve by entity type,
- and surface conflicts if data loss is possible.

The system should know when it is merging assistant context versus user-owned facts. User facts should never be silently discarded.

### 5.4 Retry Queues

Retry queue design:

- exponential backoff,
- jitter,
- network-awareness,
- idempotent writes,
- dead-letter storage for hard failures.

Failed writes should not vanish. Store them in a local dead-letter queue and surface them in diagnostics if they remain unresolved.

### 5.5 Failed Writes

If a write fails:

- keep local state,
- mark it as pending sync,
- retry automatically,
- surface a non-blocking UI indicator,
- and escalate only if it has business consequences.

For irreversible side effects:

- do not assume local success is enough,
- wait for server confirmation before showing success.

### 5.6 Background Sync

Background sync should:

- wake on network reconnect,
- run periodic reconciliation,
- compress write bursts into batches,
- refresh critical listeners,
- and revalidate auth before retrying.

### 5.7 Atomic Updates

Use Firestore batched writes and transactions correctly:

- use batched writes when operations do not depend on current remote state,
- use transactions when the result depends on existing values [web:69][web:72].

Do not fake atomicity with client-side logic. That is how you get race conditions and corrupted reminders.

### 5.8 Batched Writes

Batch operations for:

- message finalization,
- conversation + message + task creation,
- memory insert + embedding metadata,
- reminder update + task status transition.

Keep batches small and within platform limits. Firestore batched writes are atomic, but they are not magic.

### 5.9 Streaming Message Sync

Streaming chat requires a two-phase model:

1. Create a partial message record.
2. Update it as chunks arrive.
3. Finalize at completion.

Use a stable `clientMessageId` or `streamId` to join chunks. Never create a new Firestore message doc for every token. That would be grotesque.

#### Flow Diagram

```text
[User speaks/types]
      |
      v
[Local UI creates optimistic op]
      |
      v
[Queue pending write]
      |
      +--> [Local render updates immediately]
      |
      v
[Sync worker sends to Firestore]
      |
      +-- success --> [Mark op complete] --> [Update listeners]
      |
      +-- failure --> [Retry queue] --> [Dead-letter if exhausted]
```

---

## 6. Firebase Auth Strategy

### 6.1 Google Auth Flow

Use Firebase Auth with Google sign-in as the primary identity provider. The auth flow should:

1. start anonymously or via Google,
2. resolve an authenticated UID,
3. create or hydrate `users/{uid}`,
4. attach device trust metadata,
5. load user state and caches.

This is standard and sane. Don’t invent a bespoke login system unless you want security debt.

### 6.2 Session Refresh Handling

Firebase Auth tokens expire and refresh automatically through the SDK. Your app should:

- listen to auth state changes,
- refresh local session state on token rotation,
- and never treat a stale token as proof of identity.

If the token is invalid:

- stop writes,
- keep local cache,
- queue operations,
- and reauthenticate.

### 6.3 Device Trust

Device trust should be explicit:

- device registration,
- trusted flag,
- last seen,
- revocation,
- and optional step-up auth for risky actions.

For sensitive actions:

- require recent reauth,
- require a trusted device,
- or require an extra confirmation.

### 6.4 Token Expiration

A token expiring should not destroy the user experience:

- continue local UI access where safe,
- block server writes,
- preserve queue,
- and reconnect silently if possible.

### 6.5 Anonymous Onboarding

Anonymous onboarding is a strong choice for reducing drop-off. Firebase supports anonymous authentication [web:55][web:58]. Let users try Nexus without friction, then link the anonymous account to Google when they sign in.

That gives:

- a persistent UID,
- saved local progress,
- and a clean upgrade path.

### 6.6 Guest-to-User Migration

When the guest upgrades:

- link credentials to the anonymous user,
- preserve UID if possible,
- migrate local state to the real user account,
- and rehydrate all server state under the same identity [web:58][web:62].

If you create a new UID on upgrade and then try to merge everything later, you will create duplicate histories and junk migration code.

### 6.7 Security Attack Prevention

Threats to block:

- token replay,
- client-side entitlement tampering,
- cross-user document reads,
- listener abuse,
- write spam,
- and anonymous account hoarding.

Countermeasures:

- Security Rules,
- App Check if appropriate,
- rate-limited backend endpoints,
- server-side verification for billing and trust,
- and device-level trust revocation.

---

## 7. Firestore Security Rules

Security Rules must be written as if the client is hostile, because it is.

### 7.1 Production-Grade Rules Example

```js
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    function signedIn() {
      return request.auth != null;
    }

    function isOwner(uid) {
      return signedIn() && request.auth.uid == uid;
    }

    function nonEmptyString(v, maxLen) {
      return v is string && v.size() > 0 && v.size() <= maxLen;
    }

    function validPlan(plan) {
      return plan in ['free', 'pro', 'power'];
    }

    function validMessageRole(role) {
      return role in ['user', 'assistant', 'tool', 'system'];
    }

    function validMemoryScope(scope) {
      return scope in ['profile', 'session', 'task', 'global'];
    }

    function validTaskStatus(status) {
      return status in ['pending', 'running', 'succeeded', 'failed', 'cancelled'];
    }

    function validReminderStatus(status) {
      return status in ['scheduled', 'sent', 'snoozed', 'cancelled', 'failed'];
    }

    function validImportance(value) {
      return value is int && value >= 1 && value <= 5;
    }

    function validTimestamp(ts) {
      return ts is timestamp;
    }

    match /users/{uid} {
      allow read: if isOwner(uid);
      allow create: if isOwner(uid)
        && request.resource.data.uid == uid
        && nonEmptyString(request.resource.data.email, 320)
        && validPlan(request.resource.data.plan);
      allow update: if isOwner(uid)
        && request.resource.data.uid == uid
        && validPlan(request.resource.data.plan)
        && request.resource.data.createdAt == resource.data.createdAt;
      allow delete: if false;
    }

    match /users/{uid}/voice_preferences/{profileId} {
      allow read, create, update: if isOwner(uid);
      allow delete: if isOwner(uid);
    }

    match /users/{uid}/device_sessions/{sessionId} {
      allow read, create, update: if isOwner(uid);
      allow delete: if isOwner(uid);
    }

    match /users/{uid}/conversations/{conversationId} {
      allow read, create, update: if isOwner(uid);
      allow delete: if isOwner(uid);
    }

    match /users/{uid}/conversations/{conversationId}/messages/{messageId} {
      allow read: if isOwner(uid);
      allow create: if isOwner(uid)
        && request.resource.data.uid == uid
        && validMessageRole(request.resource.data.role)
        && nonEmptyString(request.resource.data.content, 20000);
      allow update: if isOwner(uid)
        && request.resource.data.uid == uid
        && request.resource.data.createdAt == resource.data.createdAt;
      allow delete: if false;
    }

    match /users/{uid}/memory/{memoryId} {
      allow read: if isOwner(uid);
      allow create: if isOwner(uid)
        && request.resource.data.uid == uid
        && validMemoryScope(request.resource.data.scope)
        && validImportance(request.resource.data.importance)
        && nonEmptyString(request.resource.data.content, 4000);
      allow update: if isOwner(uid)
        && request.resource.data.uid == uid
        && validMemoryScope(request.resource.data.scope)
        && validImportance(request.resource.data.importance)
        && nonEmptyString(request.resource.data.content, 4000);
      allow delete: if isOwner(uid);
    }

    match /users/{uid}/tasks/{taskId} {
      allow read: if isOwner(uid);
      allow create: if isOwner(uid)
        && request.resource.data.uid == uid
        && nonEmptyString(request.resource.data.goal, 4000);
      allow update: if isOwner(uid)
        && request.resource.data.uid == uid
        && validTaskStatus(request.resource.data.status);
      allow delete: if false;
    }

    match /users/{uid}/reminders/{reminderId} {
      allow read, create, update, delete: if isOwner(uid);
    }

    match /users/{uid}/subscriptions/{subscriptionId} {
      allow read: if isOwner(uid);
      allow create, update: if false;
      allow delete: if false;
    }

    match /users/{uid}/ai_state/{stateId} {
      allow read, create, update: if isOwner(uid);
      allow delete: if isOwner(uid);
    }

    match /users/{uid}/emotional_context/{contextId} {
      allow read, create, update, delete: if isOwner(uid);
    }

    match /users/{uid}/safety_flags/{flagId} {
      allow read: if isOwner(uid);
      allow create, update, delete: if false;
    }

    match /users/{uid}/cache_metadata/{cacheKey} {
      allow read, create, update, delete: if isOwner(uid);
    }

    match /users/{uid}/analytics/{eventId} {
      allow read: if isOwner(uid);
      allow create: if isOwner(uid);
      allow update, delete: if false;
    }
  }
}
```

### 7.2 Security Notes

- Security Rules are not filters. A query must still be structured so it only targets allowed data [web:42][web:40].
- Use `exists()` sparingly for admin checks.
- Server-only writes should be done through privileged code paths, not from the client.
- Do not let the client set `plan`, `status`, or `subscription` truth directly.

### 7.3 Rate Limiting Ideas

Firestore Rules do not give you real rate limiting. Use:

- App Check,
- backend throttling,
- Cloud Functions or server middleware,
- and per-device operation counters.

For rate-sensitive features like message sending or task creation, maintain a write counter in a trusted backend path.

---

## 8. Performance Optimization

### 8.1 Query Optimization

Design queries around exact access patterns:

- load current conversation messages ordered by time,
- load latest tasks for user dashboard,
- load profile memory by importance and recency,
- load reminders by `scheduledFor`,
- load device sessions by `lastSeenAt`.

Do not query “everything” and then filter client-side. That is amateur hour.

### 8.2 Composite Indexes

Add composite indexes only when a query is actually needed. Firestore has a finite composite index budget, and bad modeling burns it fast [web:68][web:60]. Keep index usage intentional:

- `uid + createdAt`
- `uid + status + updatedAt`
- `uid + scope + importance`
- `uid + scheduledFor`
- `conversationId + createdAt`

### 8.3 Pagination Strategy

Use cursor-based pagination with `orderBy` and `startAfter`, not offsets [web:80][web:75]. Cursor pagination is cheaper and stable.

Example:

- page 1: `orderBy('createdAt', 'desc').limit(30)`
- page 2: `startAfter(lastVisible).limit(30)`

### 8.4 Infinite Scroll Strategy

For infinite scroll:

- prefetch the next page before the user reaches the bottom,
- maintain a bounded page cache,
- keep only visible pages in memory,
- store cursor snapshots locally.

### 8.5 Real-Time Listener Strategy

Use listeners only on:

- current conversation,
- current task,
- current voice session,
- current AI state.

Do not attach real-time listeners to entire collections unless you enjoy bandwidth waste and listener explosions. Keep listeners small and scoped.

### 8.6 Cost Optimization

Reduce cost by:

- minimizing document reads,
- avoiding giant documents,
- batching writes,
- using summary documents,
- and keeping hot state local.

If the app renders the same user profile 20 times per page load, your architecture is dumb. Cache it.

### 8.7 Memory Chunking

Large memory should be chunked into:

- summary,
- raw source references,
- retrieval index,
- and optional semantic chunks.

A single giant memory document is an anti-pattern. Firestore caps document size at 1 MiB [web:86][web:92].

### 8.8 Hot Document Prevention

Avoid documents that every request updates:

- global counters,
- current unread badge counts,
- live presence state,
- and last-seen spam.

If a field updates too often, shard it or move it to a separate event stream.

---

## 9. AI Memory System Design

### 9.1 Short-Term Memory

Short-term memory contains:

- current user turn,
- immediate assistant reply,
- current tool results,
- active clarification state.

It lives in local memory and the current conversation document, then gets compacted.

### 9.2 Long-Term Memory

Long-term memory stores:

- stable preferences,
- recurring workflows,
- important identity facts,
- project context,
- and durable assistant learnings.

This lives in Firestore and is queryable by user ID and importance.

### 9.3 Semantic Memory

Semantic memory is the vector-backed layer used for recall by meaning. Store:

- memory content,
- embeddings metadata,
- source links,
- and retrieval confidence.

Do not store semantic memory as a raw dump. The whole point is to store compressed knowledge.

### 9.4 Episodic Memory

Episodic memory is “what happened”:

- session summaries,
- task histories,
- notable decisions,
- and outcomes.

This is crucial for continuity. It prevents the assistant from acting like a goldfish.

### 9.5 Emotional Memory

Emotional memory should be treated carefully:

- short-lived affective state,
- low confidence,
- explicit opt-in if long-term retention is used,
- and strong privacy defaults.

This is optional, not a core dependency.

### 9.6 Retrieval Pipeline

Recommended pipeline:

1. Load user profile and settings.
2. Load current conversation summary.
3. Load recent messages.
4. Load relevant memory items by scope and importance.
5. Load semantic matches if available.
6. Load task and reminder context if relevant.
7. Build prompt with bounded token budgets.

### 9.7 Context Injection

The model should receive:

- profile facts,
- conversation state,
- current task state,
- selected memory snippets,
- and safety constraints.

Do not stuff raw memory into the prompt without ranking or budgeting. That burns tokens and harms quality.

### 9.8 Memory Decay

Use decay rules:

- profile memory: persistent unless deleted,
- session memory: expires,
- task memory: expires or archives,
- emotional memory: short TTL,
- noisy low-value memory: prune aggressively.

### 9.9 Memory Summarization

Summarize long sessions into:

- key events,
- decisions,
- pending actions,
- user preferences revealed,
- and outcome state.

Store the summary as a derived memory item and keep references to source messages.

### 9.10 Embedding References

Store embedding references separately when possible:

- source doc ID,
- chunk index,
- embedding model,
- version,
- and status.

This lets you re-embed without rewriting the whole user record.

---

## 10. Sensitive Data Architecture

### 10.1 Encryption Boundaries

Encrypt:

- secrets,
- tokens,
- sensitive user attachments,
- and any data that would be catastrophic if exposed.

Do not assume Firestore security rules are encryption. They are access control. Different problem.

### 10.2 Secrets Handling

Secrets should live in:

- platform secure storage,
- environment secrets,
- server-side secret managers,
- or encrypted blobs with strict backend control.

Never store raw secrets in user-readable Firestore documents.

### 10.3 Voice Data Handling

Voice data is sensitive and bulky.
Policy:

- stream audio for live processing,
- store only if explicitly required,
- prefer derived transcript over raw audio,
- and TTL-delete debug audio.

### 10.4 PII Separation

Keep PII in a minimal user document and only if needed:

- email,
- display name,
- timezone,
- locale,
- and maybe billing identity references.

Do not scatter PII across memory docs, analytics docs, and task payloads like confetti.

### 10.5 Device-Only Secrets

Device-only secrets include:

- local agent pairing token,
- local browser session state,
- device trust keys,
- local cache encryption keys.

These belong on device, not in Firestore plaintext.

### 10.6 GDPR-Style Deletion Flow

Deletion must:

1. mark user as deleting,
2. revoke sessions,
3. delete user-owned Firestore docs,
4. delete stored media or files,
5. delete local caches on next sync,
6. and purge derived memory and embeddings.

Deletion must be complete, not symbolic.

### 10.7 Data Retention Policy

Suggested retention:

- final conversation history: long-term unless user deletes,
- session summary: long-term or policy-based,
- raw audio: short TTL,
- pending sync queue: until resolved,
- logs: short TTL,
- analytics: aggregated and minimal.

---

## 11. Voice Assistant Specific Optimizations

### 11.1 Streaming Partial Responses

Partial assistant responses should live in:

- local stream buffer,
- UI state,
- and a partial Firestore message doc only if needed.

Finalize only when response is complete. Do not turn every token into a write.

### 11.2 Interruptions

Interruption handling should:

- create a new turn boundary,
- stop current synthesis,
- mark current assistant message as interrupted,
- preserve partial state if useful,
- and continue from the latest stable checkpoint.

### 11.3 Message Stitching

When ASR or TTS streams in chunks:

- stitch by `streamId`,
- preserve order,
- finalize on end-of-stream,
- dedupe duplicate chunks.

### 11.4 Speech State Persistence

Persist only:

- voice session ID,
- current assistant state,
- user interruption flags,
- and minimal playback position if needed.

### 11.5 Realtime Sync

Use realtime listeners for:

- current session,
- current task,
- voice status,
- and synchronization state.

Do not stream the entire account in realtime.

### 11.6 Latency Reduction

Reduce latency by:

- caching user profile locally,
- preloading current conversation state,
- using lightweight summary docs,
- and avoiding broad Firestore reads at turn start.

### 11.7 Wake-Word Session Handling

If wake-word support exists later:

- treat wake-word activation as a local event,
- create or resume a session locally,
- sync only the final session state and user turn records.

---

## 12. Recommended Folder Structure

```text
nexus/
  backend/
    app/
      api/
        v1/
          auth/
          conversations/
          messages/
          memory/
          tasks/
          reminders/
          subscriptions/
          sync/
          ai_state/
          voice/
          devices/
          analytics/
      core/
        config/
        logging/
        errors/
        security/
        types/
      db/
        firestore/
          client.ts
          collections.ts
          rules/
          mappers/
          serializers/
          queries/
          transactions/
          batch.ts
          pagination.ts
          listeners.ts
        local/
          indexeddb/
          sqlite/
          repositories/
          migrations/
          queue/
          cache/
      domain/
        users/
        conversations/
        messages/
        memory/
        tasks/
        reminders/
        voice/
        ai_state/
        subscriptions/
        safety/
      services/
        auth_service.ts
        memory_service.ts
        conversation_service.ts
        task_service.ts
        reminder_service.ts
        sync_service.ts
        embedding_service.ts
        voice_state_service.ts
        cache_service.ts
      sync/
        engine.ts
        conflict_resolution.ts
        operation_queue.ts
        reconciliation.ts
        idempotency.ts
        backoff.ts
      integrations/
        firebase/
        google_auth/
        storage/
        notifications/
      workers/
        summarize_memory.ts
        generate_embeddings.ts
        expire_sessions.ts
        reminder_dispatch.ts
        cleanup.ts
    tests/
      unit/
      integration/
      security/
      sync/
  frontend/
    src/
      app/
      components/
      hooks/
      state/
      stores/
      api/
      cache/
      offline/
      listeners/
      types/
  shared/
    types/
    schemas/
    constants/
```

---

## 13. API Layer Design

### 13.1 Repository Pattern

Use repositories to isolate Firestore specifics:

- `UserRepository`
- `ConversationRepository`
- `MessageRepository`
- `MemoryRepository`
- `TaskRepository`
- `ReminderRepository`
- `DeviceSessionRepository`
- `SubscriptionRepository`
- `AiStateRepository`

Repositories should:

- do mapping,
- handle query construction,
- manage pagination cursors,
- and hide Firestore quirks from the domain layer.

### 13.2 Service Layer

Services should hold business logic:

- `MemoryService` decides what gets remembered.
- `ConversationService` handles message lifecycle.
- `SyncService` manages local/remote reconciliation.
- `TaskService` manages status transitions.
- `AuthService` handles onboarding and account linking.

### 13.3 Firestore Adapters

Firestore adapters should be thin:

- serialize domain objects,
- validate shapes,
- write batches,
- and attach server timestamps.

Never let random app code reach Firestore directly.

### 13.4 Sync Engine Modules

Modules:

- operation queue
- retry handler
- reconciliation engine
- conflict resolver
- local snapshot store
- ack tracker
- dead-letter queue

### 13.5 Validation Layer

Use schema validation before write:

- Zod or equivalent
- strict enums
- size checks
- reserved field checks
- no unknown fields in privileged docs

### 13.6 Event Bus

Use an internal event bus for:

- `message.finalized`
- `task.created`
- `task.completed`
- `memory.extracted`
- `reminder.due`
- `subscription.updated`
- `device.revoked`

This keeps side effects out of controller code.

---

## 14. Example TypeScript Interfaces

```ts
export type Plan = 'free' | 'pro' | 'power';
export type MessageRole = 'user' | 'assistant' | 'tool' | 'system';
export type MemoryScope = 'profile' | 'session' | 'task' | 'global';
export type TaskStatus = 'pending' | 'running' | 'succeeded' | 'failed' | 'cancelled';
export type ReminderStatus = 'scheduled' | 'sent' | 'snoozed' | 'cancelled' | 'failed';

export interface UserDoc {
  uid: string;
  email: string;
  displayName?: string;
  photoURL?: string;
  plan: Plan;
  status: 'active' | 'disabled' | 'deleted';
  timezone?: string;
  locale?: string;
  defaultTone?: 'concise' | 'detailed' | 'friendly' | 'formal';
  defaultStyle?: string;
  memoryPolicy?: {
    allowLongTermMemory: boolean;
    allowEmotionalMemory: boolean;
    allowVoiceRetention: boolean;
  };
  featureFlags?: Record<string, boolean>;
  limits?: {
    messageLimit?: number;
    memoryLimit?: number;
  };
  createdAt: FirebaseFirestore.Timestamp;
  updatedAt: FirebaseFirestore.Timestamp;
  lastLoginAt?: FirebaseFirestore.Timestamp;
}

export interface ConversationDoc {
  conversationId: string;
  uid: string;
  title?: string;
  mode: 'voice' | 'text' | 'mixed';
  status: 'active' | 'archived' | 'closed';
  pinned?: boolean;
  archived?: boolean;
  contextVersion: number;
  lastMessageAt: FirebaseFirestore.Timestamp;
  lastSummaryAt?: FirebaseFirestore.Timestamp;
  createdAt: FirebaseFirestore.Timestamp;
  updatedAt: FirebaseFirestore.Timestamp;
}

export interface MessageDoc {
  messageId: string;
  conversationId: string;
  uid: string;
  role: MessageRole;
  content: string;
  contentType?: 'text' | 'markdown' | 'tool_result';
  inputMode?: 'voice' | 'text';
  status: 'draft' | 'partial' | 'final' | 'interrupted';
  language?: string;
  partial?: boolean;
  clientMessageId?: string;
  replyToMessageId?: string | null;
  tokens?: number;
  tags?: string[];
  attachments?: Array<{
    type: string;
    url?: string;
    name?: string;
    mimeType?: string;
  }>;
  createdAt: FirebaseFirestore.Timestamp;
  updatedAt?: FirebaseFirestore.Timestamp;
}

export interface MemoryDoc {
  memoryId: string;
  uid: string;
  scope: MemoryScope;
  category: 'identity' | 'preference' | 'workflow' | 'tool' | 'project' | 'decision' | 'safety';
  importance: 1 | 2 | 3 | 4 | 5;
  content: string;
  source: 'extracted' | 'explicit' | 'system';
  sourceConversationId?: string;
  sourceMessageIds?: string[];
  expiresAt?: FirebaseFirestore.Timestamp | null;
  embeddingStatus?: 'pending' | 'ready' | 'failed';
  embeddingModel?: string;
  metadata?: Record<string, unknown>;
  createdAt: FirebaseFirestore.Timestamp;
  updatedAt: FirebaseFirestore.Timestamp;
}

export interface TaskDoc {
  taskId: string;
  uid: string;
  conversationId?: string;
  type: 'browser' | 'windows' | 'research' | 'reminder' | 'mixed';
  status: TaskStatus;
  title?: string;
  goal: string;
  resultSummary?: string;
  errorMessage?: string;
  priority?: 'low' | 'normal' | 'high';
  dueAt?: FirebaseFirestore.Timestamp;
  tags?: string[];
  metadata?: Record<string, unknown>;
  createdAt: FirebaseFirestore.Timestamp;
  updatedAt: FirebaseFirestore.Timestamp;
}
```

---

## 15. Example Firestore Queries

### 15.1 Load Profile

```ts
const userRef = doc(db, 'users', uid);
const userSnap = await getDoc(userRef);
```

### 15.2 Load Recent Conversation Messages

```ts
const q = query(
  collection(db, 'users', uid, 'conversations', conversationId, 'messages'),
  orderBy('createdAt', 'desc'),
  limit(30)
);
```

### 15.3 Paginate Messages

```ts
const q = query(
  messagesRef,
  orderBy('createdAt', 'desc'),
  startAfter(lastVisible),
  limit(30)
);
```

### 15.4 Load Active Memory

```ts
const q = query(
  collection(db, 'users', uid, 'memory'),
  where('scope', '==', 'profile'),
  where('importance', '>=', 4),
  orderBy('importance', 'desc'),
  orderBy('createdAt', 'desc'),
  limit(20)
);
```

### 15.5 Load Upcoming Reminders

```ts
const q = query(
  collection(db, 'users', uid, 'reminders'),
  where('status', '==', 'scheduled'),
  where('scheduledFor', '>=', now),
  orderBy('scheduledFor', 'asc'),
  limit(20)
);
```

### 15.6 Load Tasks by Status

```ts
const q = query(
  collection(db, 'users', uid, 'tasks'),
  where('status', '==', 'running'),
  orderBy('updatedAt', 'desc'),
  limit(50)
);
```

### 15.7 Load Latest Device Sessions

```ts
const q = query(
  collection(db, 'users', uid, 'device_sessions'),
  orderBy('lastSeenAt', 'desc'),
  limit(10)
);
```

---

## 16. Scaling Roadmap

### 16.1 1k Users

At 1k users:

- single Firestore project is fine,
- local caching matters more than fancy sharding,
- do not over-engineer embeddings,
- keep data model simple and strict.

### 16.2 10k Users

At 10k users:

- add clear composite indexes,
- introduce summary documents,
- prune old partial streams,
- move raw logs out of Firestore,
- monitor hot documents.

### 16.3 100k Users

At 100k users:

- split operational analytics from product data,
- isolate high-write collections,
- use more aggressive TTLs,
- use sharded counters for global metrics,
- formalize background workers.

### 16.4 1M+ Users

At 1M+ users:

- separate workloads by domain,
- consider multiple Firestore databases or project separation if operationally needed,
- isolate AI-heavy writes from user-facing reads,
- use async pipelines for summarization and embeddings,
- move anything bulky to object storage or a dedicated analytics warehouse.

### 16.5 Sharding Strategy

You usually do not shard Firestore manually the way you would a SQL database. Instead:

- partition by user,
- avoid hot docs,
- use subcollections,
- and distribute counters and state updates.

### 16.6 AI Workload Isolation

AI jobs should not block user writes:

- queue summarization,
- queue embedding generation,
- queue reminder extraction,
- queue expensive context compaction.

The user-facing path should stay lightweight.

---

## 17. Common Failure Modes

### 17.1 Race Conditions

Symptoms:

- duplicate messages,
- stale task status,
- overwritten settings.

Fix:

- idempotency keys,
- transactions where needed,
- version checks,
- strict write ordering.

### 17.2 Duplicate Messages

Cause:

- retry without dedupe,
- network replays,
- multiple tabs.

Fix:

- `clientMessageId`,
- server-side upsert semantics,
- message uniqueness by operation ID.

### 17.3 Sync Corruption

Cause:

- conflicting local and remote edits,
- partial batches,
- bad merge logic.

Fix:

- operation logs,
- compare-and-swap updates,
- explicit merge policies.

### 17.4 Cache Poisoning

Cause:

- local cache treated as truth,
- stale entries not invalidated,
- cross-user cache leaks.

Fix:

- user-scoped cache namespaces,
- cache versioning,
- auth-bound cache keys.

### 17.5 Listener Explosions

Cause:

- too many real-time subscriptions,
- listening to whole collections,
- not detaching on route change.

Fix:

- narrow listeners,
- lifecycle cleanup,
- page-level listener limits.

### 17.6 Token Desync

Cause:

- auth refresh not handled,
- stale identity in local store.

Fix:

- listen to auth state changes,
- rehydrate user state on refresh,
- block writes until auth is valid.

---

## 18. Final Recommended Architecture

### 18.1 Direct Recommendation

Use Firebase Auth + Firestore as the canonical backend, and use local storage only as a performance and offline layer. That is the right architecture for Nexus. Firestore owns durable user data, conversation history, memory, tasks, reminders, subscriptions, and AI state. Local storage owns streaming buffers, pending sync operations, UI state, and device secrets [web:31][web:51][web:46].

### 18.2 What to Avoid

Avoid these patterns:

- one giant user document,
- arrays that grow forever,
- raw conversation dumps as memory,
- client-controlled billing fields,
- storing secrets in Firestore documents,
- synchronous embedding generation in the live request path,
- and offset-based pagination.

These are the classic mistakes that turn a clean product into a maintenance swamp.

### 18.3 Final Tradeoffs

- Firestore gives you realtime sync, offline support, and simple auth integration.
- Local storage gives you speed and resilience.
- Backend services give you the control needed for memory extraction, billing, and safety.
- The price is extra discipline in data modeling, indexing, and idempotent sync.

That trade is worth it. It is the least bad architecture for a voice-first assistant that must feel fast, remember the user, and scale without turning into spaghetti.

### 18.4 Operational Rule Set

1. Firestore is truth.
2. Local is acceleration.
3. Secrets stay out of general-purpose documents.
4. Memory must be curated, not dumped.
5. Writes must be idempotent.
6. High-frequency state must be small.
7. User-owned data must be isolated by UID.
8. Dangerous operations require server validation.
9. Partial streams are not final records.
10. Every expensive task belongs off the critical path.

If you follow those rules, Nexus will stay sane as it grows.
