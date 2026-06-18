"""
output_contract.py — Nexus Output Enforcement Layer

CRITICAL: All text must pass through scrub_output() before being sent to:
  - WebSocket (safe_send_json)
  - TTS queue (enqueue_tts)

This is the single source of truth for reasoning leak prevention.
"""
import re
import logging
from typing import Optional

logger = logging.getLogger("nexus.output_contract")

# ---------------------------------------------------------------------------
# Reasoning Sentence Prefixes (English + Hinglish)
# Any sentence starting with these is internal reasoning and must be dropped.
# ---------------------------------------------------------------------------
_REASONING_PREFIXES = (
    # English — LLM self-talk
    "okay so", "okay, so", "ok so", "ok, so",
    "alright so", "alright, so",
    "so the user", "the user wants", "the user said", "the user asked",
    "the user is asking", "the user seems",
    "i need to", "i'll now", "i will now", "i should",
    "i'm going to", "i am going to", "my approach",
    "let me think", "let me plan", "let me consider",
    "my plan is", "my response will",
    "i interpret", "i understand that", "as an ai",
    "i'll phrase", "i'll keep", "i'll respond",
    "going to respond", "i'm responding",
    "i can't actually", "i cannot actually",
    "i don't actually", "i do not actually",
    "i've analyzed", "i have analyzed",
    "i'm thinking", "i am thinking",
    "i'm considering", "i am considering",
    "i'm processing", "i am processing",
    "i need to explain", "i gotta explain",
    "i'll explain", "i will explain",
    "based on the", "based on what",
    "looking at the", "given the context",
    "analyzing the",
    # Hinglish — self-talk patterns
    "main soch raha", "main souch raha",
    "theek hai toh", "acha toh",
    "user ne kaha", "user chahta",
)

# ---------------------------------------------------------------------------
# Regex patterns that detect reasoning blocks
# ---------------------------------------------------------------------------
_RE_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_RE_THINK_OPEN = re.compile(r"<think>.*$", re.DOTALL | re.IGNORECASE)
_RE_BOLD_ACTION = re.compile(r"\*\*.*?\*\*")  # **bold** annotations
_RE_ITALIC_REASONING = re.compile(r"\*[^*\n]+\*")  # *italic* reasoning notes
_RE_THINKING_TAG = re.compile(r"\[thinking\].*?\[/thinking\]", re.DOTALL | re.IGNORECASE)
_RE_SCRATCHPAD = re.compile(r"\[scratchpad\].*?\[/scratchpad\]", re.DOTALL | re.IGNORECASE)
_RE_INTERNAL = re.compile(r"\[internal\].*?\[/internal\]", re.DOTALL | re.IGNORECASE)


def is_reasoning_sentence(text: str) -> bool:
    """Returns True if this sentence is internal reasoning that must not reach the user."""
    lowered = text.lower().strip()
    return any(lowered.startswith(pfx) for pfx in _REASONING_PREFIXES)


def scrub_output(text: str) -> Optional[str]:
    """
    Strips all reasoning tokens from a text chunk before it can reach the UI/TTS.

    Returns cleaned text, or None if the entire chunk was reasoning.
    Returns empty string if the chunk becomes empty after scrubbing.
    """
    if not text:
        return text

    # 1. Strip tagged reasoning blocks (highest priority)
    text = _RE_THINK_BLOCK.sub("", text)
    text = _RE_THINK_OPEN.sub("", text)
    text = _RE_THINKING_TAG.sub("", text)
    text = _RE_SCRATCHPAD.sub("", text)
    text = _RE_INTERNAL.sub("", text)

    # 2. Strip bold/italic annotations that are LLM self-annotations
    text = _RE_BOLD_ACTION.sub("", text)
    text = _RE_ITALIC_REASONING.sub("", text)

    # 3. Clean up whitespace
    text = text.strip()

    # 4. If the whole chunk was tagged reasoning, return None to signal drop
    if not text:
        return None

    # 5. Per-sentence reasoning prefix check
    # Split on sentence boundaries, drop reasoning sentences, reassemble
    sentences = re.split(r"(?<=[.?!\n।])\s+", text)
    clean_sentences = []
    for s in sentences:
        if s.strip() and is_reasoning_sentence(s):
            logger.warning(f"[OUTPUT_CONTRACT] Dropped reasoning sentence: {s[:80]!r}")
        else:
            clean_sentences.append(s)

    result = " ".join(clean_sentences).strip()
    return result if result else None


def scrub_and_log(text: str, source: str = "unknown") -> Optional[str]:
    """Scrub with source tagging for audit logging."""
    original_len = len(text)
    result = scrub_output(text)
    if result is None:
        logger.warning(f"[OUTPUT_CONTRACT] [{source}] FULL DROP — chunk was pure reasoning ({original_len} chars)")
    elif len(result) < original_len:
        logger.debug(f"[OUTPUT_CONTRACT] [{source}] Scrubbed {original_len - len(result)} chars of reasoning")
    return result
