# PERSONALITY_PIPELINE_AUDIT.md
## Why Nexus Sometimes Ignores Personality — Evidence

### Problem
Nexus occasionally responds in a generic, robotic manner despite having a defined personality in `prompts.py`.

---

### Finding 1: Three Competing System Prompts Exist

**Prompt 1 — The Good One** (`prompts.py`)
```python
# File: d:\AI\backend\voice_agent\prompts.py
# Lines 1-44
def get_nexus_system_prompt() -> str:
    return """
You are Nexus, a Voice-First AI Operating System and Agent Orchestrator built by Aniket.
...Helpful, Sharp, Witty...
...Prefer conversational Hinglish...
...HUMOR LAYER...
...CONFIDENCE SYSTEM...
"""
```
This is the richest, most complete prompt. **It is NEVER used by the active pipeline.**

---

**Prompt 2 — The Active One (Minimal)** (`ws_main.py`)
```python
# File: d:\AI\backend\voice_agent\ws_main.py
# Lines 935-947 (confirmed line from grep search)
system_prompt = (
    "You are Nexus, a premium AI assistant. "
    "Your persona is Professional, Confident, Helpful, Fast, and Natural. "
    "Do not sound robotic. Be concise. "
    "Mirror the user's dominant language naturally. "
    "If the user speaks English, respond in English. "
    "If the user speaks Hindi or Marathi, respond in that language. "
    "Only mix languages when the user naturally mixes them first. "
    "Do not force translations. "
    "Keep responses conversational and natural. "
    "CRITICAL: Do NOT output internal monologues, reasoning steps, or thought processes. "
    "CRITICAL: No markdown or emojis. Never use asterisks (*) or formatting."
)
```
This is the prompt that actually runs. It lacks the humor layer, the confidence system, the response length controller, and all the identity rules from `prompts.py`.

---

**Prompt 3 — Dead Prompt** (`main.py`)
```python
# File: d:\AI\backend\voice_agent\main.py
# Lines 140-146
system_prompt="""You are Nexus, a highly advanced AI system. 
    IMPORTANT: Your first task is to wait for the user to select a language...
"""
```
This is from the old Stream WebRTC pipeline. It is dead code (`main.py` is never executed). **No impact.**

---

### Finding 2: `prompts.py` is Never Imported in the Active Pipeline

**Evidence:** Grep search on `prompts.py` imports:
```
# ZERO results in ws_main.py
# ZERO results in providers/llm.py
# ZERO results in config.py
```
`prompts.py` exists but is completely orphaned. It was written for the old `main.py` pipeline.

---

### Finding 3: No Conversation History
**File:** `ws_main.py`
**Evidence:**
```python
stream = await llm_provider.client.chat.completions.create(
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": transcript}   # ← SINGLE USER MESSAGE ONLY
    ],
    model=llm_provider.model,
    stream=True
)
```
Every single turn sends **only one user message** with no conversation history. The LLM has zero memory of previous turns, making personality drift worse because it cannot build on established rapport.

---

### Summary of Root Causes

| Cause | File | Line | Impact |
|-------|------|------|--------|
| Rich `prompts.py` never imported | `ws_main.py` | 935 | Full personality unused |
| Minimal 6-line prompt active instead | `ws_main.py` | 935-947 | Generic responses |
| No conversation history passed | `ws_main.py` | ~955 | Zero cross-turn coherence |
| `main.py` has third dead prompt | `main.py` | 140 | Confusion, no impact |

### Fix Priority
1. Import and use `get_nexus_system_prompt()` from `prompts.py` in `ws_main.py`
2. Add rolling conversation history (last 8-10 turns) to every LLM call
3. Delete the inline prompt string from `ws_main.py`
4. Delete the dead prompt from `main.py`
