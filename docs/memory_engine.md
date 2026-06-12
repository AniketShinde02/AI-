# Memory Engine: Fact Extraction & Context Retrieval

## 1. Memory Architecture
Nexus 2.0 uses a tiered memory system to balance speed, relevance, and persistence.

### Tier 1: Session Context (Ephemeral)
- **Scope**: Current conversation thread.
- **Storage**: In-memory / Redis cache for the active session.
- **Content**: Last 10–20 turns of dialogue, active task state, and tool outputs.

### Tier 2: User Profile (Persistent)
- **Scope**: Permanent facts about the user.
- **Storage**: Supabase Postgres (`memory_items` table).
- **Content**: Name, role, preferences, frequently used apps, website credentials (mapped securely).

### Tier 3: Knowledge Base (Semantic - Future)
- **Scope**: Large amounts of unstructured info.
- **Storage**: pgvector on Supabase.
- **Content**: Research reports, long-term task logs, user-uploaded documents.

## 2. Fact Extraction Process
Every 3–5 turns, a background task (using `GPT-4o-mini`) processes the recent history to extract new permanent facts.

1.  **Trigger**: Conversation turn completes.
2.  **Analysis**: LLM identifies "Permanent Facts".
3.  **Deduplication**: Compare new facts against existing `memory_items`.
4.  **Persistence**: `INSERT` new unique facts into the database.

## 3. Retrieval Strategy
Before every LLM orchestration turn, the system performs a multi-stage retrieval:

1.  **Exact Match**: Pull all facts where `importance_score > 8`.
2.  **Semantic Search (Future)**: Use `pgvector` to find facts related to the current query.
3.  **Context Injection**: Inject retrieved facts into the Orchestrator's system prompt under the `Memory:` header.

## 4. Safety & Privacy
- **User Control**: Users can ask "What do you remember about me?" or "Forget that I like X".
- **Sensitivity**: Never extract PII (Personally Identifiable Information) or passwords into the standard memory table. Use dedicated secure storage for credentials.
