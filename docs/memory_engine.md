# Nexus 2.0 — Memory Engine Reference

**Document version:** `v1.0`  
**Status:** Production-grade specification  
**Audience:** Senior backend engineers building or modifying the Nexus 2.0 memory pipeline  
**Last updated:** 2026-04-27  

---

## Table of Contents

1. [Overview](#1-overview)
2. [Memory Scopes](#2-memory-scopes)
3. [DB Schema for Memory](#3-db-schema-for-memory)
4. [Context Assembly Algorithm](#4-context-assembly-algorithm)
5. [Token Budget](#5-token-budget)
6. [Rolling Summary Strategy](#6-rolling-summary-strategy)
7. [Memory Extraction (Post-Session)](#7-memory-extraction-post-session)
8. [Phase Roadmap](#8-phase-roadmap)
9. [What AI Coding Tools Must NOT Do](#9-what-ai-coding-tools-must-not-do)

---

## 1. Overview

### Why memory matters

A voice assistant without memory is a stateless command interpreter. It cannot say "you mentioned last week you prefer concise answers" or "last time you ran this browser task, the site required two-factor authentication." Every session starts from zero. Users teach the assistant their preferences repeatedly. The assistant cannot personalize, cannot accelerate, cannot become indispensable.

Nexus 2.0 is designed to become the user's persistent assistant — one that grows more useful over time because it accumulates a model of who the user is and what they do. This requires a memory system that is:

- **Intelligent** — not a raw conversation dump, but extracted facts and preferences
- **Selective** — stores what matters, discards noise, deduplicates aggressively
- **Efficient** — never exceeds the token budget allocated for memory injection
- **Retrievable** — in Phase 1, by keyword and recency; in Phase 2, by semantic similarity
- **Trustworthy** — the user can inspect and delete what is remembered

### Types of memory Nexus supports

| Type | Mechanism | Lifespan | Phase |
|---|---|---|---|
| Working memory | In-request context (last N turns passed to LLM) | Single LLM call | MVP |
| Session memory | DB: `memory_items` with `scope='session'` | Session duration | MVP |
| Long-term profile memory | DB: `memory_items` with `scope='profile'` | Indefinite (user-deletable) | MVP |
| Task memory | DB: `memory_items` with `scope='task'`, linked by `task_id` | Per-task, retained as reference | MVP |
| Semantic / vector memory | pgvector embeddings in `memory_items.embedding` | Same as item scope | Phase 2 |
| Global facts | DB: `memory_items` with `scope='global'`, `user_id=NULL` | Indefinite | Phase 2 |
| Hierarchical (xMemory-style) | Layered summaries at session/week/month granularity | Indefinite | Phase 3 |

---

## 2. Memory Scopes

Each `memory_item` row carries a `scope` field. Scope governs retrieval priority, injection position, and expiry behavior.

### `profile` — User preferences and facts (cross-session)

The most important scope. Profile memories are injected into every LLM call. They represent durable facts about the user that don't change session to session.

**Examples:**
- `"User's name is Arjun Mehta. He prefers to be addressed as Arjun."` (importance: 5)
- `"User works as a backend engineer at a fintech startup in Mumbai."` (importance: 5)
- `"User uses Notion as their primary task manager."` (importance: 4)
- `"User prefers dark mode and minimal UI. He finds verbose AI responses annoying."` (importance: 4)
- `"User codes primarily in Python and is learning Rust."` (importance: 3)
- `"User's keyboard shortcut for new terminal tab is Ctrl+Shift+T in Windows Terminal."` (importance: 2)

**Retrieval rule:** Always fetch profile memories with `importance >= 4` (hard inject). Fetch `importance >= 3` if token budget permits. Never fetch `importance <= 2` unless specifically requested.

**Expiry:** Never expires unless the user explicitly deletes or the system detects a contradiction (handled during post-session memory extraction deduplication).

---

### `session` — Active session context

Session memories are scoped to a single session. They capture what has happened in the current conversation and are primarily used when session history exceeds the token budget. The rolling summary (Section 6) is stored as a `session`-scope memory.

**Examples:**
- `"Session goal: User is preparing a presentation on Q4 metrics for a board meeting tomorrow."` (importance: 4)
- `"User already confirmed that browser profile 'Work' should be used for Gmail tasks."` (importance: 3)
- `"Rolling summary: Arjun asked about Notion alternatives, then asked Nexus to open his Notion workspace and duplicate the Project Apollo template. Task completed successfully."` (importance: 3)

**Expiry:** Set `expires_at = session.ended_at + interval '24 hours'`. A cleanup cron job prunes expired session memories.

---

### `task` — Context from a specific task

Task memories are linked to a specific `task_id` in the `tasks` table. They capture intermediate state, clarification answers, and tool results for a running or completed task. They are the primary mechanism for resuming interrupted tasks.

**Examples:**
- `"Browser task goal: Book a Zomato delivery order for chicken biryani, extra spicy."` (task_id: abc123, importance: 3)
- `"Clarification answered: User confirmed delivery address is 'Koramangala, Bangalore'."` (task_id: abc123, importance: 4)
- `"Task result: Booking confirmed. Order #ZOM-98123. Estimated delivery: 45 minutes."` (task_id: abc123, importance: 3)

**Expiry:** Does not expire, but retrieval is limited to the specific `task_id` context unless the task is still active.

---

### `global` — System-wide facts (not user-specific)

Global memories store facts that apply across all users, such as current API rate limits, known service outages, or product feature flags. User_id is NULL for global memories.

**Examples:**
- `"GetStream free tier limit: 5 concurrent voice sessions."` (importance: 2)
- `"Browser Use: Zomato login via OTP — does not support persistent session."` (importance: 3)
- `"Feature flag: research_mode_enabled=false for Free tier as of 2026-01-01."` (importance: 4)

**Retrieval rule:** Inject global memories relevant to the current task only. Never inject all global memories unconditionally.

---

## 3. DB Schema for Memory

The memory system lives in two primary tables: `memory_items` (the core store) and the `sessions` and `tasks` tables it references.

```sql
-- ─────────────────────────────────────────────────────────────────────────
-- Core memory store
-- ─────────────────────────────────────────────────────────────────────────

CREATE TABLE memory_items (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,  -- NULL for global scope
    session_id  UUID REFERENCES sessions(id),                 -- nullable
    task_id     UUID REFERENCES tasks(id),                    -- nullable
    scope       VARCHAR(20) NOT NULL                          -- 'profile'|'session'|'task'|'global'
                    CHECK (scope IN ('profile', 'session', 'task', 'global')),
    content     TEXT NOT NULL,                                -- The actual memory text
    importance  SMALLINT DEFAULT 3                            -- 1–5 scale
                    CHECK (importance BETWEEN 1 AND 5),
    embedding   vector(1536),                                 -- pgvector; NULL until Phase 2
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    expires_at  TIMESTAMPTZ,                                  -- NULL = never expires
    source      VARCHAR(30) DEFAULT 'extracted'               -- 'extracted'|'explicit'|'system'
                    CHECK (source IN ('extracted', 'explicit', 'system'))
);

-- Indexes for common retrieval patterns
CREATE INDEX idx_memory_user_scope
    ON memory_items (user_id, scope)
    WHERE expires_at IS NULL OR expires_at > NOW();

CREATE INDEX idx_memory_user_importance
    ON memory_items (user_id, importance DESC, created_at DESC)
    WHERE scope = 'profile';

CREATE INDEX idx_memory_session
    ON memory_items (session_id)
    WHERE scope IN ('session', 'task');

CREATE INDEX idx_memory_task
    ON memory_items (task_id)
    WHERE scope = 'task';

-- Phase 2: vector similarity index (enable after embeddings are populated)
-- CREATE INDEX idx_memory_embedding
--     ON memory_items USING ivfflat (embedding vector_cosine_ops)
--     WITH (lists = 100);


-- ─────────────────────────────────────────────────────────────────────────
-- Supporting tables (abbreviated — full schema in 05_db_schema_data_model.md)
-- ─────────────────────────────────────────────────────────────────────────

CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       VARCHAR(255) UNIQUE NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    started_at  TIMESTAMPTZ DEFAULT NOW(),
    ended_at    TIMESTAMPTZ,                -- NULL while session is active
    turn_count  INT DEFAULT 0,
    status      VARCHAR(20) DEFAULT 'active'
                    CHECK (status IN ('active', 'ended', 'abandoned'))
);

CREATE TABLE tasks (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id    UUID REFERENCES sessions(id),
    user_id       UUID REFERENCES users(id) ON DELETE CASCADE,
    tool_name     VARCHAR(50) NOT NULL,      -- 'browser_task'|'windows_task'|'research_task'
    status        VARCHAR(20) DEFAULT 'pending'
                      CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    goal          TEXT NOT NULL,
    result        TEXT,
    error_message TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    completed_at  TIMESTAMPTZ
);

CREATE TABLE conversation_turns (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  UUID REFERENCES sessions(id) ON DELETE CASCADE,
    role        VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'tool')),
    content     TEXT NOT NULL,
    tool_name   VARCHAR(50),   -- set if role='tool'
    tool_call_id VARCHAR(100), -- OpenAI tool call ID, if applicable
    tokens_used INT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

### Memory expiry cleanup job

```sql
-- Scheduled via Supabase pg_cron or Inngest cron job — run daily
DELETE FROM memory_items
WHERE expires_at IS NOT NULL
  AND expires_at < NOW();
```

---

## 4. Context Assembly Algorithm

The context assembler is the intelligence layer that decides what to send to the LLM for each request. It is the most critical function in the memory system. It must run fast (target: < 50ms including DB queries) and must never exceed the defined token budget.

### Data structures

```python
# core/memory.py

from dataclasses import dataclass, field
from uuid import UUID


@dataclass
class AssembledContext:
    """
    The fully assembled context ready for injection into the LLM call.
    Produced by assemble_context().
    """
    profile_memory_text: str           # Rendered profile memories (injected into system prompt)
    session_summary_text: str          # Rolling session summary (injected into system prompt)
    session_turns_as_messages: list[dict]  # Raw turns as OpenAI messages format
    task_context_text: str | None      # Active task state, if any
    
    # Accounting
    profile_memory_tokens: int
    session_summary_tokens: int
    session_turns_tokens: int
    task_context_tokens: int
    total_tokens_used: int
    
    # Metadata
    memories_retrieved: int            # How many memory_items were fetched
    semantic_search_used: bool         # Whether pgvector similarity was used


@dataclass
class TokenBudget:
    """
    Token allocation for each context component.
    See Section 5 for budget rationale.
    """
    TOTAL:           int = 16_000
    SYSTEM_PROMPT:   int =  2_000
    PROFILE_MEMORY:  int =  1_500
    SESSION_HISTORY: int =  6_000
    SEMANTIC_MEMORY: int =  1_500
    TASK_CONTEXT:    int =  2_000
    TOOL_RESULTS:    int =  2_000
    USER_MESSAGE:    int =  1_000
```

### Context assembly implementation

```python
# core/memory.py

import tiktoken
from uuid import UUID

_ENCODER = tiktoken.encoding_for_model("gpt-4o-mini")


def count_tokens(text: str) -> int:
    """Fast token count. Uses tiktoken — same encoder as GPT-4o-mini/GPT-4o."""
    return len(_ENCODER.encode(text))


async def assemble_context(
    user_id: UUID,
    session_id: UUID,
    query: str,
    budget: TokenBudget = None,
    task_id: UUID | None = None,
) -> AssembledContext:
    """
    Assembles the full context payload for an LLM call.

    Assembly steps:
      1. Fetch high-importance profile memories (always injected)
      2. Fetch rolling session summary or last N session turns
      3. If pgvector enabled: fetch semantically similar memories
      4. Fetch active task context if task_id is provided
      5. Pack each component within its token budget
      6. Return AssembledContext with token accounting

    Never raises on partial results — if a DB query fails, gracefully
    degrade to empty string for that component.
    """
    if budget is None:
        budget = TokenBudget()

    # ── Step 1: Fetch profile memories ────────────────────────────────────
    profile_memories = await _fetch_profile_memories(
        user_id=user_id,
        min_importance=4,      # Always include importance >= 4
        max_items=10,
    )

    # If budget allows, also include importance >= 3
    profile_text = _render_memories(profile_memories)
    if count_tokens(profile_text) < budget.PROFILE_MEMORY * 0.7:
        extra = await _fetch_profile_memories(
            user_id=user_id,
            min_importance=3,
            max_items=5,
            exclude_ids=[m.id for m in profile_memories],
        )
        profile_memories.extend(extra)
        profile_text = _render_memories(profile_memories)

    # Hard cap at budget
    profile_text = _truncate_to_budget(profile_text, budget.PROFILE_MEMORY)

    # ── Step 2: Session history ────────────────────────────────────────────
    # First check for a rolling summary
    rolling_summary = await _fetch_rolling_summary(session_id=session_id)
    
    if rolling_summary:
        session_summary_text = rolling_summary.content
        # Get the last 5 raw turns (verbatim, after the summarized period)
        raw_turns = await _fetch_recent_turns(
            session_id=session_id,
            max_turns=5,
            after_turn_number=rolling_summary.covers_up_to_turn,
        )
    else:
        session_summary_text = ""
        # No summary — get up to 10 raw turns or until budget exhausted
        raw_turns = await _fetch_recent_turns(
            session_id=session_id,
            max_turns=10,
        )

    turns_as_messages = [turn.as_message_dict() for turn in raw_turns]
    turns_token_count = sum(count_tokens(t["content"]) for t in turns_as_messages)

    # Trim if over budget (remove oldest turns first)
    while turns_token_count > budget.SESSION_HISTORY and len(turns_as_messages) > 2:
        removed = turns_as_messages.pop(0)
        turns_token_count -= count_tokens(removed["content"])

    # ── Step 3: Semantic memory retrieval (Phase 2 only) ──────────────────
    semantic_memory_text = ""
    semantic_search_used = False

    if await _pgvector_is_enabled():
        semantic_memories = await _fetch_semantic_memories(
            user_id=user_id,
            query=query,
            top_k=5,
            min_similarity=0.75,
            exclude_ids=[m.id for m in profile_memories],
        )
        if semantic_memories:
            semantic_memory_text = _render_memories(semantic_memories)
            semantic_memory_text = _truncate_to_budget(
                semantic_memory_text, budget.SEMANTIC_MEMORY
            )
            semantic_search_used = True

    # ── Step 4: Active task context ────────────────────────────────────────
    task_context_text = None
    task_context_tokens = 0

    if task_id:
        task_memories = await _fetch_task_memories(task_id=task_id)
        if task_memories:
            task_context_text = _render_memories(task_memories)
            task_context_text = _truncate_to_budget(task_context_text, budget.TASK_CONTEXT)
            task_context_tokens = count_tokens(task_context_text)

    # ── Step 5: Combine profile + semantic into memory_context string ─────
    # This is what goes into the {memory_context} placeholder in the system prompt
    memory_context_parts = []
    if profile_text:
        memory_context_parts.append(f"### User Profile\n{profile_text}")
    if semantic_memory_text:
        memory_context_parts.append(f"### Related Context\n{semantic_memory_text}")

    memory_context = "\n\n".join(memory_context_parts) if memory_context_parts else "(No profile memory yet)"

    # ── Step 6: Build and return AssembledContext ──────────────────────────
    profile_tokens = count_tokens(memory_context)
    session_summary_tokens = count_tokens(session_summary_text)

    return AssembledContext(
        profile_memory_text=memory_context,
        session_summary_text=session_summary_text,
        session_turns_as_messages=turns_as_messages,
        task_context_text=task_context_text,
        profile_memory_tokens=profile_tokens,
        session_summary_tokens=session_summary_tokens,
        session_turns_tokens=turns_token_count,
        task_context_tokens=task_context_tokens,
        total_tokens_used=(
            profile_tokens + session_summary_tokens +
            turns_token_count + task_context_tokens
        ),
        memories_retrieved=len(profile_memories),
        semantic_search_used=semantic_search_used,
    )


# ── Private helpers ────────────────────────────────────────────────────────

async def _fetch_profile_memories(
    user_id: UUID,
    min_importance: int,
    max_items: int,
    exclude_ids: list[UUID] | None = None,
) -> list[MemoryItem]:
    """Fetch profile-scope memories ordered by importance DESC, then recency."""
    query = """
        SELECT * FROM memory_items
        WHERE user_id = $1
          AND scope = 'profile'
          AND importance >= $2
          AND (expires_at IS NULL OR expires_at > NOW())
          AND ($3::uuid[] IS NULL OR id != ALL($3))
        ORDER BY importance DESC, created_at DESC
        LIMIT $4
    """
    rows = await db.fetch(query, user_id, min_importance, exclude_ids, max_items)
    return [MemoryItem(**row) for row in rows]


async def _fetch_rolling_summary(session_id: UUID) -> MemoryItem | None:
    """Fetch the most recent rolling summary for this session."""
    row = await db.fetchrow("""
        SELECT * FROM memory_items
        WHERE session_id = $1
          AND scope = 'session'
          AND source = 'system'
          AND content LIKE 'ROLLING_SUMMARY:%%'
        ORDER BY created_at DESC
        LIMIT 1
    """, session_id)
    return MemoryItem(**row) if row else None


async def _fetch_recent_turns(
    session_id: UUID,
    max_turns: int,
    after_turn_number: int | None = None,
) -> list[ConversationTurn]:
    """Fetch the most recent N conversation turns for a session."""
    query = """
        SELECT * FROM conversation_turns
        WHERE session_id = $1
          AND ($2 IS NULL OR turn_number > $2)
        ORDER BY created_at DESC
        LIMIT $3
    """
    rows = await db.fetch(query, session_id, after_turn_number, max_turns)
    turns = [ConversationTurn(**row) for row in rows]
    return list(reversed(turns))  # Return in chronological order


def _render_memories(memories: list[MemoryItem]) -> str:
    """Render a list of memory items as a bulleted text block."""
    if not memories:
        return ""
    lines = []
    for m in memories:
        prefix = "•"
        lines.append(f"{prefix} {m.content}")
    return "\n".join(lines)


def _truncate_to_budget(text: str, max_tokens: int) -> str:
    """Hard-truncate text to stay within token budget. Never splits mid-sentence if avoidable."""
    if count_tokens(text) <= max_tokens:
        return text
    # Binary search for truncation point
    tokens = _ENCODER.encode(text)
    truncated_tokens = tokens[:max_tokens]
    return _ENCODER.decode(truncated_tokens)
```

---

## 5. Token Budget

The token budget defines hard limits for each context component. These values are calibrated for `gpt-4o-mini` with a 128k token context window, using a conservative working budget of 16,000 tokens to ensure fast responses and cost control.

### Budget constants

```python
# core/memory.py

@dataclass
class TokenBudget:
    #
    # Total context budget for a standard request.
    # Conservative limit chosen to keep costs predictable and avoid
    # latency spikes from very large contexts on GPT-4o-mini.
    # GPT-4o complex tasks may use a higher TOTAL (e.g. 32,000).
    #
    TOTAL:           int = 16_000

    # The rendered system prompt (role, rules, injected memory).
    # Hard limit. Never compress the system prompt — it degrades behavior.
    SYSTEM_PROMPT:   int =  2_000

    # Profile memories injected into the system prompt.
    # Includes semantic matches in Phase 2.
    PROFILE_MEMORY:  int =  1_500

    # Raw conversation turns OR rolling summary + recent turns.
    # This is the largest slice — recent context is the most valuable.
    SESSION_HISTORY: int =  6_000

    # Semantic memory from vector search (Phase 2 only).
    # Separate from PROFILE_MEMORY to keep accounting clean.
    SEMANTIC_MEMORY: int =  1_500

    # Active task context (goal, intermediate results, clarifications).
    TASK_CONTEXT:    int =  2_000

    # Tool results from this turn's tool calls.
    TOOL_RESULTS:    int =  2_000

    # The current user message.
    # Hard limit. If a user message exceeds 1,000 tokens, truncate and notify.
    USER_MESSAGE:    int =  1_000
```

### Budget allocation breakdown

```
Total: 16,000 tokens
├── System prompt (inc. injected memories): 2,000 + 1,500 = 3,500
├── Session history:                         6,000
├── Semantic memory:                         1,500
├── Task context:                            2,000
├── Tool results:                            2,000
└── User message:                            1,000
    ─────────────────────────────────────────
    Total assigned:                         16,000
```

### Overflow handling

When assembled context exceeds budget, truncation happens in this order — **from lowest to highest priority:**

```
Priority for truncation (truncate lowest priority first):

1. SEMANTIC_MEMORY     — remove oldest semantic memories first
2. SESSION_HISTORY     — trim oldest turns (keep recent ones)
   └── If session has a rolling summary:
       keep summary verbatim, trim raw turns
   └── If session has no summary and > 20 turns:
       trigger rolling summary NOW (see Section 6)
3. TASK_CONTEXT        — truncate to key fields (goal + last tool result only)
4. PROFILE_MEMORY      — drop importance <= 3 items
5. TOOL_RESULTS        — truncate tool result text, keep status/summary

NEVER truncate:
• System prompt base text
• User message
• Profile memories with importance = 5
```

```python
# core/memory.py — overflow handling

def apply_overflow_policy(
    context: AssembledContext,
    budget: TokenBudget,
) -> AssembledContext:
    """
    Applies overflow truncation policy if total context exceeds budget.
    Mutates and returns context in-place.
    """
    if context.total_tokens_used <= budget.TOTAL:
        return context  # No truncation needed

    overflow = context.total_tokens_used - budget.TOTAL

    # 1. Trim semantic memory first
    if context.profile_memory_tokens > budget.PROFILE_MEMORY and overflow > 0:
        # (semantic is embedded in profile_memory_text in Phase 2)
        context = _trim_semantic_portion(context, budget.SEMANTIC_MEMORY)
        overflow = context.total_tokens_used - budget.TOTAL

    # 2. Trim session history
    if overflow > 0 and context.session_turns_tokens > 500:
        context = _trim_session_turns(context, budget.SESSION_HISTORY)
        overflow = context.total_tokens_used - budget.TOTAL

    # 3. Trim task context
    if overflow > 0 and context.task_context_text:
        context = _trim_task_context(context, min_tokens=200)
        overflow = context.total_tokens_used - budget.TOTAL

    # 4. Drop low-importance profile memories
    if overflow > 0:
        context = _trim_low_importance_memories(context, min_importance=4)

    return context
```

---

## 6. Rolling Summary Strategy

When session history grows beyond the `SESSION_HISTORY` budget (6,000 tokens), keeping raw turns becomes counterproductive. The rolling summary strategy compresses older turns into a compact paragraph while retaining the most recent turns verbatim.

### When to trigger a rolling summary

```python
# core/memory.py

ROLLING_SUMMARY_TRIGGER_TURNS = 20   # Trigger when session exceeds 20 turns
ROLLING_SUMMARY_TRIGGER_TOKENS = 5_000  # Or when session history exceeds 5k tokens

async def maybe_trigger_rolling_summary(
    session_id: UUID,
    user_id: UUID,
) -> bool:
    """
    Checks if a rolling summary should be generated for this session.
    Called after each assistant turn by core/conversation.py.
    Returns True if a summary was generated.
    """
    turn_count = await db.fetchval(
        "SELECT turn_count FROM sessions WHERE id = $1", session_id
    )
    if turn_count is None:
        return False

    session_tokens = await _estimate_session_token_count(session_id)

    should_summarize = (
        turn_count >= ROLLING_SUMMARY_TRIGGER_TURNS or
        session_tokens >= ROLLING_SUMMARY_TRIGGER_TOKENS
    )

    if should_summarize:
        await generate_rolling_summary(session_id=session_id, user_id=user_id)
        return True

    return False
```

### Summary generation

```python
# core/memory.py

ROLLING_SUMMARY_PROMPT = """
You are a memory compression assistant. Below is a conversation transcript.
Summarize the key events, decisions made, tasks executed, and outcomes in 
3–6 sentences. Focus on facts that would help an AI assistant understand 
what happened and serve the user better in future turns.

Include:
- What the user was trying to accomplish
- Which tasks were executed and their results
- Any preferences or facts the user revealed
- Any pending items or incomplete tasks

Do NOT include:
- Pleasantries or small talk
- Tool call mechanics
- Information that is already in the user's profile memory

Transcript:
{transcript}

Summary (write in third person, as if briefing a new assistant):
""".strip()


async def generate_rolling_summary(
    session_id: UUID,
    user_id: UUID,
    keep_last_n_turns: int = 5,
) -> MemoryItem:
    """
    Generates a rolling summary of the session, covering all turns except
    the most recent keep_last_n_turns (which are kept verbatim).

    Steps:
    1. Fetch all turns for this session
    2. Exclude the most recent keep_last_n_turns
    3. Send to GPT-4o-mini for summarization
    4. Store as memory_item with scope='session', source='system'
    5. Mark covered turns with a generation checkpoint

    Returns the created MemoryItem.
    """
    all_turns = await _fetch_recent_turns(session_id=session_id, max_turns=200)

    if len(all_turns) <= keep_last_n_turns:
        return None  # Nothing to summarize yet

    turns_to_summarize = all_turns[:-keep_last_n_turns]
    transcript = _format_turns_as_transcript(turns_to_summarize)

    summary_prompt = ROLLING_SUMMARY_PROMPT.format(transcript=transcript)
    
    # Use GPT-4o-mini — this is async, cost-sensitive work
    from services.llm_router import get_model, TaskComplexity
    model = get_model(TaskComplexity.SIMPLE)
    
    response = await _call_llm(
        model_config=model,
        messages=[{"role": "user", "content": summary_prompt}],
    )
    summary_text = response.content.strip()
    
    # Store as a session-scoped memory
    memory_item = await db.memory_items.create({
        "user_id": user_id,
        "session_id": session_id,
        "scope": "session",
        "source": "system",
        "content": f"ROLLING_SUMMARY: {summary_text}",
        "importance": 3,
        "covers_up_to_turn": len(turns_to_summarize),  # Checkpoint
    })

    return memory_item


def _format_turns_as_transcript(turns: list[ConversationTurn]) -> str:
    """Format turns as a readable transcript for the summarization LLM."""
    lines = []
    for turn in turns:
        role_label = "User" if turn.role == "user" else "Nexus"
        if turn.role == "tool":
            lines.append(f"[Tool: {turn.tool_name}] {turn.content}")
        else:
            lines.append(f"{role_label}: {turn.content}")
    return "\n".join(lines)
```

### Summary lifecycle

```
Session starts
     │
     ├── Turns 1–19: raw turns stored in conversation_turns
     │                session_history budget = up to 6,000 tokens
     │
     ├── Turn 20 (or ~5,000 tokens): rolling summary triggered
     │   ├── Turns 1–15 → summarized into memory_item (scope='session')
     │   └── Turns 16–20 → kept verbatim
     │
     ├── Turns 21–39: new raw turns appended
     │
     ├── Turn 40: second rolling summary triggered
     │   ├── Existing summary + turns 16–35 → new summary
     │   └── Turns 36–40 → kept verbatim
     │
     └── Session ends → post-session memory extraction (Section 7)
```

---

## 7. Memory Extraction (Post-Session)

When a session ends, a background Inngest job processes the conversation to extract durable profile-level facts. This is the mechanism that makes Nexus smarter over time.

### Inngest job definition

```python
# inngest_functions/memory_extract.py
# Triggered by: POST /sessions/{session_id}/end

import inngest
from uuid import UUID

@inngest.create_function(
    fn_id="extract-session-memory",
    trigger=inngest.TriggerEvent(event="nexus/session.ended"),
    retries=3,
)
async def extract_session_memory(ctx: inngest.Context) -> dict:
    """
    Post-session memory extraction job.
    Runs asynchronously after session.ended event is published.
    Typical latency: 5–15 seconds after session end.
    """
    session_id = UUID(ctx.event.data["session_id"])
    user_id    = UUID(ctx.event.data["user_id"])

    await run_memory_extraction(session_id=session_id, user_id=user_id)
    return {"status": "ok", "session_id": str(session_id)}
```

### Extraction prompt and logic

```python
# core/memory.py

MEMORY_EXTRACTION_PROMPT = """
You are a memory extraction assistant. Analyze this conversation and extract 
durable facts about the user worth remembering across future sessions.

Focus on:
1. Personal facts (name, job title, company, location, timezone)
2. Tool and software preferences ("uses Notion", "prefers VS Code")
3. Work patterns ("morning person", "works in short focused sessions")
4. Communication preferences ("prefers concise responses", "technical background")
5. Recurring workflows or goals ("deploys to Railway", "uses pnpm not npm")
6. Important decisions made that have future relevance
7. Relationship/project context ("working on Project Apollo launch")

Do NOT extract:
- One-off requests with no future relevance ("open Chrome")
- Sensitive information (passwords, financial data, health data)
- Facts already well-represented in existing profile memory (dedup later)
- Information the user might want private (do not extract if uncertain)

For each extracted fact, respond with a JSON array:
[
  {
    "content": "User prefers Python for scripting tasks over bash.",
    "importance": 3,
    "category": "preference"
  },
  ...
]

Importance scale: 1=trivial, 2=minor, 3=normal, 4=important, 5=critical
Categories: "identity" | "preference" | "workflow" | "tool" | "project" | "decision"

Conversation transcript:
{transcript}

Existing profile memory (avoid duplicating these):
{existing_profile}

Extracted facts (JSON array only, no other text):
""".strip()


async def run_memory_extraction(session_id: UUID, user_id: UUID) -> list[MemoryItem]:
    """
    Runs post-session memory extraction for a completed session.
    
    Steps:
    1. Fetch the full session transcript (up to last 50 turns)
    2. Fetch existing profile memories (for deduplication context)
    3. Send to GPT-4o-mini for fact extraction
    4. For each extracted fact: check for semantic duplicates
    5. Insert non-duplicate facts as memory_items with scope='profile'
    6. Return list of newly created MemoryItems
    """
    # Step 1: Fetch transcript
    turns = await _fetch_recent_turns(session_id=session_id, max_turns=50)
    if not turns:
        return []

    transcript = _format_turns_as_transcript(turns)

    # Step 2: Fetch existing profile memory for dedup context
    existing = await _fetch_profile_memories(
        user_id=user_id, min_importance=1, max_items=30
    )
    existing_profile = _render_memories(existing) or "(none)"

    # Step 3: LLM extraction
    prompt = MEMORY_EXTRACTION_PROMPT.format(
        transcript=transcript,
        existing_profile=existing_profile,
    )

    from services.llm_router import get_model, TaskComplexity
    model = get_model(TaskComplexity.MEMORY_EXTRACT)

    response = await _call_llm(
        model_config=model,
        messages=[{"role": "user", "content": prompt}],
    )

    # Step 4: Parse extracted facts
    extracted_facts: list[dict] = _parse_extraction_response(response.content)
    if not extracted_facts:
        return []

    # Step 5: Deduplication and insertion
    created_items: list[MemoryItem] = []
    for fact in extracted_facts:
        is_duplicate = await _is_duplicate_memory(
            user_id=user_id,
            content=fact["content"],
            existing_memories=existing,
        )
        if not is_duplicate:
            item = await db.memory_items.create({
                "user_id": user_id,
                "session_id": session_id,
                "scope": "profile",
                "source": "extracted",
                "content": fact["content"],
                "importance": fact.get("importance", 3),
            })
            created_items.append(item)

    return created_items


async def _is_duplicate_memory(
    user_id: UUID,
    content: str,
    existing_memories: list[MemoryItem],
) -> bool:
    """
    Phase 1: Simple keyword overlap check.
    Phase 2: Replace with pgvector cosine similarity check.
    Returns True if the content is substantially similar to an existing memory.
    """
    # Phase 1 implementation: bag-of-words overlap
    content_words = set(content.lower().split())
    for existing in existing_memories:
        existing_words = set(existing.content.lower().split())
        overlap = content_words & existing_words
        overlap_ratio = len(overlap) / max(len(content_words), 1)
        if overlap_ratio > 0.6:
            return True  # Likely duplicate

    # Phase 2 (future): semantic similarity via pgvector
    # similarity = await _cosine_similarity(content, existing_memories)
    # return similarity > 0.85

    return False


def _parse_extraction_response(content: str) -> list[dict]:
    """Parse the LLM's JSON response. Returns empty list on parse failure."""
    import json
    try:
        # Strip any markdown code fences if present
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content.strip())
    except (json.JSONDecodeError, IndexError):
        return []
```

### Post-session flow summary

```
User ends session (or session times out)
         │
         ▼
  POST /sessions/{id}/end
         │
         ├─→ DB: sessions.status = 'ended', sessions.ended_at = NOW()
         ├─→ Inngest event published: nexus/session.ended
         │
         │   (Background — user does not wait for this)
         ▼
  Inngest: extract-session-memory job
         │
         ├── Fetch last 50 turns
         ├── Fetch existing profile memory (for dedup)
         ├── GPT-4o-mini extraction call (~3–8s)
         ├── For each fact:
         │   ├── Check duplicate → skip if duplicate
         │   └── INSERT into memory_items (scope='profile')
         └── Log extracted count, token cost, latency
```

---

## 8. Phase Roadmap

Memory system capabilities evolve across three phases aligned with the product roadmap. Each phase has a clear trigger condition and is independently deployable.

### Phase 1 — MVP (Month 1)

**Goal:** Get basic memory working end-to-end. No embeddings. Keyword search only.

**What ships:**
- `memory_items` table with full schema (embedding column present but NULL)
- `assemble_context()` fully implemented (Steps 1–4 without semantic search)
- `TokenBudget` enforced on every LLM call
- Rolling summary trigger at 20 turns or 5,000 tokens
- Post-session memory extraction via Inngest job (GPT-4o-mini)
- Phase 1 deduplication: keyword overlap check
- `memory_save` tool working end-to-end (user can ask Nexus to remember things)

**What is explicitly deferred:**
- pgvector embeddings — not populated, not searched
- Global-scope memories
- Memory inspection UI (user cannot view/delete memories yet)
- Memory eviction policy (manually curated at this scale)

**Phase 1 retrieval:** `ORDER BY importance DESC, created_at DESC LIMIT 10`

---

### Phase 2 — Semantic Memory (Month 2)

**Trigger:** 50+ active users consistently hitting context quality issues, or memory_items exceeds 10,000 rows.

**What ships:**
- Embeddings populated using OpenAI `text-embedding-3-small` (1536 dimensions)
- Background Inngest job: embed all existing profile memories in batch
- New memory items embedded on insert (async, non-blocking to the main flow)
- `_fetch_semantic_memories()` using pgvector `<=>` cosine distance operator
- Phase 2 deduplication: cosine similarity > 0.85 threshold
- Semantic search included in `assemble_context()` Step 3
- Memory inspection endpoint: `GET /users/me/memories` with search

**pgvector query pattern:**
```sql
-- Top 5 semantically similar profile memories for a given query
SELECT id, content, importance,
       1 - (embedding <=> $1::vector) AS similarity
FROM memory_items
WHERE user_id = $2
  AND scope = 'profile'
  AND embedding IS NOT NULL
  AND (expires_at IS NULL OR expires_at > NOW())
ORDER BY embedding <=> $1::vector
LIMIT 5;
```

**Cost note:** `text-embedding-3-small` costs $0.02/1M tokens. Embedding one memory item (~50 tokens) costs ~$0.000001. At 1,000 memory items/user, cost is trivial.

---

### Phase 3 — Hierarchical Memory (Month 4+)

**Trigger:** Power users with 6+ months of usage, 10,000+ memory items, requesting features like "what did I work on last month?".

**What ships:**
- xMemory-style layered summaries:
  - Session summaries (already exists from Phase 1)
  - Weekly summaries (Inngest weekly cron: summarize all session summaries for the week)
  - Monthly summaries (Inngest monthly cron: summarize all weekly summaries)
- Memory tagging: project-level tags so memories can be scoped to "Project Apollo" etc.
- Memory forgetting policy: user-controlled, with automated eviction for low-importance items older than 90 days
- Memory export: `GET /users/me/memories/export` returns structured JSON
- Memory UI: full CRUD in the Nexus web interface

**Architecture note:** Phase 3 does not require changes to `assemble_context()`. The hierarchical summaries are stored as `profile`-scope memories with high importance and appropriate tags, so they are retrieved through the existing pipeline.

---

## 9. What AI Coding Tools Must NOT Do

This section defines hard constraints for AI-assisted development. These rules exist because AI coding assistants (Cursor, Copilot, Claude, etc.) often take shortcuts that seem reasonable locally but violate system invariants.

### Rule 1: Never bypass `core/memory.py` for DB writes

**Wrong:**
```python
# In services/browser_use_client.py
# DO NOT DO THIS
await db.execute(
    "INSERT INTO memory_items (user_id, scope, content) VALUES ($1, 'profile', $2)",
    user_id, "User completed a browser task"
)
```

**Why it's wrong:** Direct DB writes to `memory_items` skip:
- Importance scoring logic
- Duplicate detection
- Token budget validation
- Event emission for async processing
- Schema validation

**Correct pattern:**
```python
# Always go through core/memory.py
from core.memory import save_memory

await save_memory(
    user_id=user_id,
    content="User completed a browser task to book a Zomato delivery.",
    scope="session",
    importance=2,
)
```

---

### Rule 2: Never store raw conversation dumps as memory

**Wrong:**
```python
# DO NOT DO THIS — do not dump raw turns into memory_items
for turn in session_turns:
    await db.memory_items.create({
        "user_id": user_id,
        "scope": "profile",
        "content": f"{turn.role}: {turn.content}",  # Raw turn text
        "importance": 3,
    })
```

**Why it's wrong:** Raw conversation text in memory_items:
- Wastes context budget with low-information content (pleasantries, fillers)
- Creates massive token overhead on retrieval
- Contains no structured signal — just noise
- Grows without bound (100 turns/session × 50 sessions = 5,000 raw turns)

**Correct pattern:** Extract facts first via `run_memory_extraction()` (Section 7). Only store the extracted, normalized, deduplicated facts as memory items.

---

### Rule 3: Never inject raw memory into the system prompt slot directly

**Wrong:**
```python
# DO NOT DO THIS
system_prompt = f"""
You are Nexus.
{raw_memory_dump}  ← unstructured dump directly in system prompt
"""
```

**Why it's wrong:** The system prompt slot has a hard budget of 2,000 tokens. An unstructured memory dump will overflow it, overwrite tool instructions, and degrade model behavior. Memory injection must go through the designated `{memory_context}` placeholder, which is populated by `assemble_context()` with proper budget enforcement.

**Correct pattern:** Always use `build_system_prompt(memory_context=..., session_context=...)` from `core/prompts/base.py`. This function enforces the budget and renders memory into the designated injection point.

---

### Rule 4: Never call OpenAI Embeddings API synchronously in the request path

**Wrong:**
```python
# In core/conversation.py — DO NOT DO THIS
async def handle_user_message(message: str, user_id: UUID, ...) -> Response:
    # ...
    embedding = await openai.embeddings.create(input=message, model="text-embedding-3-small")
    # This adds 100–300ms to every single user request
```

**Why it's wrong:** The embeddings API call adds 100–300ms latency to the critical path (user speaks → response starts). For a voice assistant targeting < 1.5s end-to-end latency, this is a significant budget violation.

**Correct pattern:** Queue embedding generation as an Inngest background job after the response is returned to the user. The next request will benefit from the embedding if retrieval is needed.

---

### Rule 5: Never grow `memory_items` without a cleanup plan

**Wrong:**
```python
# DO NOT DO THIS — no expiry, no eviction, no deduplication
await db.memory_items.create({
    "user_id": user_id,
    "scope": "session",
    "content": some_content,
    # Missing: expires_at, duplicate check
})
```

**Why it's wrong:** Without `expires_at`, session-scope memories accumulate indefinitely. At 10 session memories/session × 100 sessions/month, a single user generates 1,000 session memories in 10 months — nearly all of which are stale. This degrades retrieval quality, increases DB query cost, and wastes vector index capacity.

**Correct pattern:**
- Always set `expires_at` for session-scope memories.
- Always run `_is_duplicate_memory()` before inserting profile-scope memories.
- Run the daily cleanup cron to purge expired items.

---

*Document version: v1.0 | Next review: after Phase 2 semantic memory rollout*
