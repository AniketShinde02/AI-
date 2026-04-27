# Nexus 2.0 — Voice AI Latency Budget

> **Document type:** Production engineering reference  
> **Project:** Nexus 2.0 — Voice-first AI assistant for Windows power users  
> **Status:** Living document — update as benchmarks change  
> **Last updated:** 2025  

---

## Table of Contents

1. [Overview & North Star](#1-overview--north-star)
2. [Pipeline Architecture](#2-pipeline-architecture)
3. [Latency Budget Allocation](#3-latency-budget-allocation)
4. [Streaming Architecture (Non-Negotiable)](#4-streaming-architecture-non-negotiable)
5. [Filler Audio Strategy for Tool Calls](#5-filler-audio-strategy-for-tool-calls)
6. [VAD (Voice Activity Detection) Tuning](#6-vad-voice-activity-detection-tuning)
7. [Model Selection vs. Latency Trade-offs](#7-model-selection-vs-latency-trade-offs)
8. [Tool Call Latency Management](#8-tool-call-latency-management)
9. [Network Optimization](#9-network-optimization)
10. [Monitoring & Alerting](#10-monitoring--alerting)
11. [Latency Testing Checklist](#11-latency-testing-checklist)
12. [Optimization Roadmap](#12-optimization-roadmap)

---

## 1. Overview & North Star

### Why Latency Is the #1 UX Metric for Voice AI

Voice is fundamentally different from text interfaces. When a user types a query, they expect a brief moment for the system to "think." When a user speaks, they expect a human-like conversational response. The human auditory and conversational systems are exquisitely tuned to detect unnatural pauses.

The research on conversational delay is unambiguous:

| Perceived Delay | User Experience |
|---|---|
| < 300ms | Feels instantaneous and natural — matches human turn-taking |
| 300ms–800ms | Slightly perceptible delay, but acceptable for most users |
| 800ms–1500ms | Clearly noticeable; users may wonder if the assistant heard them |
| 1500ms–3000ms | Users start to feel frustrated; may repeat themselves |
| > 3000ms | Users actively repeat themselves, assume the system failed, or abandon |

This maps to a real product hierarchy:

- **< 800ms TTFA**: Conversational feel. Users stay in flow.
- **800ms–2000ms**: Functional. Users tolerate it, especially with filler audio.
- **> 2000ms silence**: UX degrades. Users disengage or repeat.

The industry benchmark is sobering: most production voice AI systems — including large, well-funded ones — ship at **1.4–1.7s median TTFA**. This is where users consciously notice the delay. Hitting sub-800ms on simple turns, with < 2s on tool call turns, would make Nexus 2.0 feel genuinely fast in the market.

### The Core Insight

> **"Latency budget is a product decision masquerading as an engineering problem."**

Every millisecond in the pipeline represents a product trade-off:

- Choose Groq over GPT-4o for intent classification → save 200ms → worse (but acceptable) intent quality
- Add filler audio before tool calls → buy 2-3s → slightly less natural but perceived latency collapses
- Use batch TTS instead of streaming → save implementation complexity → add 800ms to TTFA → completely unacceptable

The team must own the latency budget as a product spec, not treat it as a post-launch optimization problem. Every architectural decision has a latency cost. This document makes those costs explicit.

### Nexus 2.0 Targets

| Turn type | Target TTFA | Stretch goal |
|---|---|---|
| Simple response (no tool) | < 800ms | < 600ms |
| Tool call turn (browser, Windows, research) | < 2000ms | < 1500ms |
| Fallback / error | < 500ms (immediate acknowledgment) | — |

**TTFA = Time To First Audio** — the moment the user finishes speaking to the moment they hear the first audio output. This is the only metric that matters for conversational feel.

---

## 2. Pipeline Architecture

### Complete Voice Pipeline

The following diagram shows every stage of the pipeline with its latency contribution. Numbers reflect real-world measurements from each provider.

```
┌─────────────────────────────────────────────────────────────────────┐
│  USER SPEAKS                                                        │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  GetStream Video SDK                                                │
│  WebRTC audio capture → GetStream edge node                        │
│  Latency: 30–50ms                                                   │
│  (Global CDN, no action required — GetStream handles routing)       │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  GetStream Stream Buffer                                            │
│  Audio chunks buffered before forwarding to STT                    │
│  Latency: 0–20ms                                                    │
│  (Negligible; chunked at ~20ms audio frames)                        │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Deepgram Streaming STT (via Vision Agents)                        │
│  Nova-2 or Nova-3 model, streaming mode                            │
│  Latency to first PARTIAL transcript: 150–250ms                    │
│  (Streaming mode is critical — batch would add 800ms+)             │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  VAD: End-of-Utterance Detection                                   │
│  Deepgram utterance_end_ms + local VAD                             │
│  Latency: 50–100ms (VAD window + finalization)                     │
│  (Critical tuning point — see Section 6)                           │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Vision Agents: Text Forwarded to Backend                          │
│  Finalized transcript sent from GetStream agent to Railway backend │
│  Network latency: 20–50ms (Railway US-East ↔ edge)                │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Intent Classification (Groq — Llama 3.1 8B Instant)              │
│  Classifies: simple_answer | tool_call | clarification             │
│  Latency: TTFT 80–150ms (Groq is the fastest inference available)  │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                          ┌───────┴──────────┐
                          │                  │
                          ▼                  ▼
          SIMPLE PATH               TOOL CALL PATH
         (no tool needed)          (browser/Windows/research)
                          │                  │
                          ▼                  ▼
          ┌───────────────────┐   ┌────────────────────────┐
          │  LLM Response     │   │  Filler Audio → User   │
          │  GPT-4o-mini via  │   │  "Let me check that…"  │
          │  OpenRouter       │   │  [plays immediately]   │
          │  TTFT: 200–400ms  │   └──────────┬─────────────┘
          └────────┬──────────┘              │
                   │                         ▼
                   │              ┌────────────────────────┐
                   │              │  Tool Execution        │
                   │              │  Browser: 500–3000ms   │
                   │              │  Windows: 200–500ms    │
                   │              │  Research: 1000–5000ms │
                   │              └──────────┬─────────────┘
                   │                         │
                   │                         ▼
                   │              ┌────────────────────────┐
                   │              │  LLM Summarization     │
                   │              │  GPT-4o-mini           │
                   │              │  TTFT: 200–400ms       │
                   │              └──────────┬─────────────┘
                   │                         │
                   └──────────┬──────────────┘
                              │
                              ▼
          ┌───────────────────────────────────────┐
          │  OpenAI TTS (Streaming)               │
          │  Sentence-level chunking              │
          │  Time to first audio chunk: 150–200ms │
          │  (Streams while generating remainder) │
          └───────────────────┬───────────────────┘
                              │
                              ▼
          ┌───────────────────────────────────────┐
          │  USER HEARS FIRST AUDIO               │
          │  Simple path target: < 800ms          │
          │  Tool call path target: < 2000ms      │
          └───────────────────────────────────────┘
```

### Key Architectural Constraints

1. **GetStream Vision Agents** is the orchestration layer. It wires Deepgram STT, VAD, and the backend webhook together. You do not build raw WebRTC or raw audio capture — GetStream handles that.
2. **Deepgram streaming mode** is non-negotiable. Batch mode adds 800ms+ and breaks the budget.
3. **Groq Llama 3.1 8B Instant** is the fastest publicly available LLM API for intent classification. Use it only for the classification step, not for full responses.
4. **OpenRouter GPT-4o-mini** is the primary response model. It's cheaper and faster than GPT-4o while being accurate enough for >90% of Nexus tasks.
5. **OpenAI TTS streaming** is the only viable TTS path. ElevenLabs streaming is a valid alternative for voice quality experiments but adds ~50ms of overhead.

---

## 3. Latency Budget Allocation

### Simple Response Path — Target: < 800ms TTFA

This is the critical path. Most Nexus turns are simple answers — questions about weather, quick knowledge lookups, brief Windows tips. These must feel instant.

| Stage | Component | Budget (ms) | Optimized (ms) | Notes |
|---|---|---|---|---|
| WebRTC audio transport | GetStream Video SDK | 50 | 30 | Global CDN edge routing |
| Stream buffer | GetStream | 20 | 10 | Audio frame chunking |
| STT first partial | Deepgram streaming | 200 | 150 | Nova-2 streaming mode |
| VAD endpointing | Deepgram + local | 100 | 50 | Tune `utterance_end_ms` |
| Network (client → backend) | Railway | 50 | 30 | Railway US-East or EU-West |
| Intent classification | Groq Llama 3.1 8B | 150 | 100 | Fastest inference path |
| LLM response TTFT | GPT-4o-mini via OpenRouter | 300 | 200 | First token latency only |
| TTS first audio chunk | OpenAI streaming TTS | 200 | 150 | Sentence chunking |
| **Total TTFA** | | **1070ms** | **720ms** | |

**Budget gap analysis:** The "default" budget total is 1070ms — 270ms over the 800ms target. Hitting the target requires the following optimizations all simultaneously:

- Deepgram streaming delivering partials at the low end (~150ms)
- VAD tuned tightly (~50ms finalization window)
- Railway region co-located near user base
- Groq at low latency (~100ms TTFT)
- OpenRouter GPT-4o-mini at the fast end (~200ms TTFT)

The **710ms optimized path** is achievable on a good day with the right regional setup. The **realistic production target is 750–950ms** — plan for this, not the theoretical minimum.

### Tool Call Path — Target: < 2000ms with Filler Audio

Tool calls break the simple latency budget. The strategy is to **never make the user wait in silence** — filler audio plays immediately while the tool executes.

| Stage | Component | Budget (ms) | Notes |
|---|---|---|---|
| WebRTC audio transport | GetStream | 50 | Same as simple path |
| STT + VAD | Deepgram | 300 | Same as simple path |
| Network | Railway | 50 | Same as simple path |
| Intent classification | Groq | 150 | Identifies tool call needed |
| **Filler audio trigger** | **Vision Agents callback** | **< 50ms** | **Must happen before tool starts** |
| Tool execution — browser | Vision Agents browser tool | 500–3000ms | Highly variable |
| Tool execution — Windows | Windows tool (local agent) | 200–500ms | Local execution, lower latency |
| Tool execution — research | Research/web tool | 1000–5000ms | Accept async if needed |
| LLM summarization TTFT | GPT-4o-mini | 300 | Summarizes tool result |
| TTS first chunk | OpenAI streaming | 200 | |
| **Total TTFA (after filler)** | | **1350–4050ms** | Perceived latency < 2s if filler plays |

**The filler strategy is critical:** With filler audio, the perceived TTFA becomes ~200ms (when the filler audio starts). The actual tool result arrives much later, but the user is not sitting in silence. This is how every major voice assistant handles tool calls — Siri, Alexa, and Google Assistant all play acknowledgment audio before completing the action.

### Latency Stack Visualization

```
Timeline (ms from end of user speech):
0ms       200ms      400ms      600ms      800ms     1000ms     2000ms
|─────────|──────────|──────────|──────────|─────────|──────────|
                                                      
[STT]─────[VAD]──[net]─[Groq]────────────[mini TTFT]───[TTS]───▶ AUDIO
 0        200    300   350      500        700       900  1050
                              
Simple path: first audio at ~1050ms (target: <800ms, optimized: ~710ms)

Tool path:
[STT]─[VAD]─[Groq]─[FILLER AUDIO▶▶▶▶▶▶▶▶▶▶▶▶▶▶▶▶▶▶▶▶▶▶▶▶▶▶▶▶]─[TTS]▶ RESULT
 0    300    500    550  <── filler plays at 550ms, buys 2-3 seconds
```

---

## 4. Streaming Architecture (Non-Negotiable)

### Why Everything Must Stream

Latency in voice AI is dominated by a single insight: **every stage that waits for the previous stage to fully complete before starting adds its full latency to the total**. Streaming eliminates this coupling.

The mathematical impact:

```
Non-streaming (sequential):
  STT: 800ms (full transcript) 
  + LLM: 600ms (full response generated) 
  + TTS: 400ms (full audio generated)
  = 1800ms before user hears anything
  
Streaming (overlapped):
  STT partial: 200ms
  + LLM TTFT: 200ms (first token while STT still running)  
  + TTS first chunk: 150ms (audio starts while LLM still generating)
  = ~550ms to first audio byte
```

Streaming cuts TTFA by ~1250ms on a typical turn. This is not a micro-optimization — it's the entire latency strategy.

### Stage-by-Stage Streaming Requirements

#### STT: Deepgram Streaming (Partial Transcripts)

```python
# Required configuration in Vision Agents / Deepgram client
deepgram_config = {
    "model": "nova-2",
    "language": "en-US",
    "encoding": "linear16",
    "sample_rate": 16000,
    "channels": 1,
    "interim_results": True,        # Enable partial transcripts
    "utterance_end_ms": 1000,       # Detect end of utterance
    "vad_events": True,             # Voice activity events
    "endpointing": 400,             # ms of silence before final transcript
}

# Partial results fire as the user speaks
# Final result fires when utterance_end_ms silence detected
# DO NOT wait for final — start processing on high-confidence partial
```

**Key principle:** When Deepgram fires a partial transcript with `is_final: false`, begin intent classification immediately if the partial looks complete (ends with punctuation or has high confidence). Don't wait for the `is_final: true` event.

#### LLM: Token Streaming

```python
# OpenRouter / OpenAI compatible streaming
async def stream_llm_response(transcript: str):
    stream = await openrouter_client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[{"role": "user", "content": transcript}],
        stream=True,  # CRITICAL: must be True
        max_tokens=500,
    )
    
    sentence_buffer = ""
    async for chunk in stream:
        token = chunk.choices[0].delta.content or ""
        sentence_buffer += token
        
        # Fire TTS as soon as a complete sentence arrives
        if ends_sentence(sentence_buffer):
            yield sentence_buffer  # Send to TTS immediately
            sentence_buffer = ""
    
    # Flush any remaining content
    if sentence_buffer:
        yield sentence_buffer

def ends_sentence(text: str) -> bool:
    """Detect sentence boundary for TTS chunking."""
    return bool(re.search(r'[.!?]\s*$', text.strip()))
```

#### TTS: Sentence-Level Chunking

The OpenAI TTS API accepts text and streams audio. The key optimization is **sentence chunking** — don't wait for the full LLM response before sending to TTS.

```python
async def stream_tts_audio(text_stream):
    """
    As LLM tokens arrive, buffer into sentences and send each 
    sentence to TTS as soon as it's complete.
    """
    async for sentence in text_stream:
        # Send sentence to TTS — starts playing immediately
        audio_stream = await openai_client.audio.speech.create(
            model="tts-1",          # tts-1 is faster; tts-1-hd is higher quality
            voice="alloy",          # or "nova", "shimmer" — match brand voice
            input=sentence,
            response_format="opus", # Lower latency than mp3
        )
        # Stream audio chunks to GetStream for playback
        async for audio_chunk in audio_stream.iter_bytes(chunk_size=4096):
            yield audio_chunk
```

**Critical:** Use `tts-1` not `tts-1-hd` for real-time voice. `tts-1-hd` adds ~100ms latency for quality that is imperceptible in a voice conversation.

**Audio format:** Use `opus` encoding (not `mp3`). Opus has lower latency for streaming playback and better network resilience.

### How GetStream Vision Agents Wires This Together

Vision Agents provides the orchestration layer that connects these streaming stages. The flow is:

```
Vision Agents Agent (cloud-hosted)
├── Audio input: GetStream WebRTC room → Deepgram streaming STT
├── STT callback: partial/final transcripts → your backend webhook
├── Response streaming: your LLM stream → TTS → GetStream audio output
└── Filler audio: pre-recorded clips → play on tool_call_detected event

Your backend (Railway):
├── POST /nexus/turn  ← Vision Agents webhook
│   └── classify intent (Groq)
│   └── if tool_call: trigger filler audio + execute tool
│   └── if simple: stream LLM → stream TTS → return audio stream
└── Vision Agents SDK handles audio delivery back to client
```

The streaming chain in Vision Agents terms:

```python
# In your Vision Agents agent configuration
agent = VoiceAgent(
    stt=DeepgramSTT(
        model="nova-2",
        interim_results=True,
        utterance_end_ms=1000,
    ),
    llm=OpenRouterLLM(
        model="openai/gpt-4o-mini",
        stream=True,
    ),
    tts=OpenAITTS(
        model="tts-1",
        voice="alloy",
        streaming=True,
    ),
    # Filler audio config — see Section 5
    filler_phrases=FILLER_AUDIO_MAP,
)
```

GetStream Vision Agents ensures that the audio stream from TTS is played back through the WebRTC room in real time. You do not need to handle WebRTC playback yourself.

---

## 5. Filler Audio Strategy for Tool Calls

### The Problem

Tool calls are latency-unpredictable. A browser navigation might take 500ms or 4000ms. A web research query might take 1s or 8s. No amount of engineering makes this predictable.

The solution is **perceptual latency management**: play audio immediately so the user knows they were heard, then deliver the result whenever it arrives. Users tolerate waiting if they know they've been acknowledged. They don't tolerate silence.

### Filler Audio Library

Define pre-recorded (or TTS-generated) filler phrases for each tool category:

```python
FILLER_AUDIO_MAP = {
    # Generic fallback
    "default": [
        "Let me check that for you.",
        "One moment.",
        "On it.",
        "Sure, give me a second.",
    ],
    
    # Browser / web tasks
    "browser": [
        "Let me pull that up.",
        "Opening that now.",
        "Checking that online.",
        "Let me look that up for you.",
        "Pulling up the page now.",
    ],
    
    # Windows / local tasks (file ops, app launch, etc.)
    "windows": [
        "On it.",
        "Done — or almost.",
        "Taking care of that.",
        "Running that for you.",
    ],
    
    # Research / multi-step reasoning
    "research": [
        "Let me do a quick search on that.",
        "Researching that now — this might take a moment.",
        "Looking into it. I'll have an answer shortly.",
        "That's a good question. Let me check a few sources.",
    ],
    
    # Calendar / scheduling
    "calendar": [
        "Let me check your calendar.",
        "Looking at your schedule.",
        "Pulling up your calendar now.",
    ],
    
    # Email / communication
    "email": [
        "Checking your inbox now.",
        "Let me pull up your email.",
        "Looking through your messages.",
    ],
}
```

**Implementation:** Generate these as audio files offline using OpenAI TTS. Store them as pre-rendered audio clips (`.opus` or `.mp3`) so they play with zero TTS latency when needed.

### When to Trigger Filler Audio

Filler audio must be triggered **before** the tool executes, the moment the intent classifier fires `tool_call`:

```python
async def handle_turn(transcript: str, agent: VoiceAgent):
    # Step 1: Classify intent (Groq — fast, ~100ms)
    intent = await classify_intent(transcript)
    
    if intent.type == "simple_answer":
        # No filler needed — just stream the response
        async for audio in stream_response(transcript):
            await agent.send_audio(audio)
    
    elif intent.type == "tool_call":
        # CRITICAL: Play filler IMMEDIATELY before tool starts
        tool_type = intent.tool_category  # "browser", "windows", etc.
        await agent.play_filler(FILLER_AUDIO_MAP[tool_type])
        
        # Now execute the tool (can take 500ms–5000ms)
        tool_result = await execute_tool(intent.tool_name, intent.tool_args)
        
        # Summarize and stream the result
        async for audio in stream_summarization(tool_result, transcript):
            await agent.send_audio(audio)
```

### Filler Audio Timing Rules

| Scenario | Filler trigger | Notes |
|---|---|---|
| Tool call detected | Immediately on classification | < 50ms after Groq responds |
| Tool takes < 1s | Filler may overlap with result | Fine — sounds natural |
| Tool takes 1–3s | Filler fills the gap cleanly | Ideal scenario |
| Tool takes > 3s | Play second filler or progress update | "Still working on it…" |
| Tool fails | Play error filler | "I had trouble with that — let me try again" |

### Progressive Tool Updates (for long-running tools)

For tasks that take > 3 seconds, implement progressive audio updates:

```python
async def execute_long_tool(tool_name: str, args: dict, agent: VoiceAgent):
    # Initial filler
    await agent.play_filler(FILLER_AUDIO_MAP[tool_name])
    
    # Start tool with progress callback
    result = None
    elapsed = 0
    
    async def tool_task():
        nonlocal result
        result = await run_tool(tool_name, args)
    
    task = asyncio.create_task(tool_task())
    
    # Check every 3 seconds; play progress audio if still waiting
    while not task.done():
        await asyncio.sleep(3.0)
        elapsed += 3
        if not task.done() and elapsed < 15:
            await agent.play_filler(["Still working on that…", "Almost there…"])
    
    await task
    return result
```

---

## 6. VAD (Voice Activity Detection) Tuning

### Why VAD Matters for Latency

VAD (Voice Activity Detection) determines when the user has finished speaking. Get it wrong and:

- **Too aggressive (short silence window):** Assistant interrupts user mid-sentence → extremely annoying, sounds broken
- **Too conservative (long silence window):** Turn takes 400ms longer than needed → TTFA misses budget

For Nexus 2.0, the default Deepgram endpointing is 300ms. For **Windows power users** (the target persona), this needs adjustment upward. Power users:
- Are more likely to speak in command-like utterances with natural pauses (e.g., "Open… uh… the file manager")
- Are comfortable with technology and won't be confused by a 400ms silence threshold
- Would be frustrated by premature cut-off more than by slightly longer waits

### Recommended VAD Configuration

```python
deepgram_vad_config = {
    # Primary endpointing (ms of silence before finalizing utterance)
    "endpointing": 400,             # Default: 300ms → Recommended: 400ms
                                    # For noisy environments: 500ms
                                    # For clean environments: 350ms
    
    # Deepgram-specific end-of-utterance detection
    "utterance_end_ms": 1000,       # Time after last word before firing UtteranceEnd
                                    # Use alongside endpointing for belt-and-suspenders
    
    # VAD sensitivity (if using custom VAD on top of Deepgram)
    "vad_events": True,
    
    # Interim results for pre-processing before final transcript
    "interim_results": True,
    "smart_format": True,           # Punctuation, numbers formatting
}
```

### Silence Threshold Decision Matrix

| Threshold | Behavior | When to use |
|---|---|---|
| 200ms | Very aggressive — cuts off users | Never use in production |
| 300ms | Deepgram default — too fast for thoughtful users | Rapid-fire command users only |
| 400ms | **Nexus 2.0 recommended** | Windows power users (default) |
| 500ms | Conservative — feels slightly sluggish | Noisy environments, accessibility |
| 600ms+ | Very conservative — noticeable pause | Avoid unless users have speech patterns requiring it |

### Environment-Adaptive VAD

Implement adaptive silence threshold based on detected environment noise:

```python
class AdaptiveVAD:
    def __init__(self):
        self.base_threshold_ms = 400
        self.noise_level = "quiet"  # "quiet" | "moderate" | "noisy"
    
    def update_noise_level(self, rms_db: float):
        """Update noise level based on recent audio RMS."""
        if rms_db < -40:
            self.noise_level = "quiet"
            self.threshold_ms = 350
        elif rms_db < -25:
            self.noise_level = "moderate"
            self.threshold_ms = 400
        else:
            self.noise_level = "noisy"
            self.threshold_ms = 500
    
    def get_endpointing_ms(self) -> int:
        return self.threshold_ms
```

### Deepgram `utterance_end_ms` vs. `endpointing`

These are two different mechanisms — use both:

- **`endpointing`**: Deepgram's internal VAD silence detection. Fires `SpeechFinal` event. Set to 400ms.
- **`utterance_end_ms`**: Fires `UtteranceEnd` event after this many ms of no new words. More robust in noisy environments. Set to 1000ms.

In code, listen for whichever fires first:

```python
@deepgram_client.on("SpeechFinal")
async def on_speech_final(result):
    transcript = result.channel.alternatives[0].transcript
    if transcript.strip():
        await process_turn(transcript)

@deepgram_client.on("UtteranceEnd")
async def on_utterance_end(result):
    # Backup trigger if SpeechFinal didn't fire
    if not turn_already_processing:
        await process_turn(current_partial_transcript)
```

### Barge-In Handling

When the user starts speaking while the assistant is still outputting audio, stop playback immediately:

```python
@deepgram_client.on("SpeechStarted")  
async def on_speech_started(event):
    """User started speaking — stop current audio output immediately."""
    if agent.is_playing_audio():
        await agent.stop_audio()
        await agent.reset_state()
    # Deepgram will fire transcription events for the new utterance
```

Barge-in is critical for natural feel. Without it, users must wait for the assistant to finish before speaking, which breaks conversation flow.

---

## 7. Model Selection vs. Latency Trade-offs

### The Fundamental Rule

> **Never use a model bigger than necessary for latency-sensitive paths.**

Model quality is often irrelevant within a task category. GPT-4o-mini is ~95% as good as GPT-4o for simple Q&A — but takes half the time. The 5% quality difference is undetectable in a voice conversation. The 300ms latency difference is.

### Model Latency Reference Table

| Use Case | Fast Option | TTFT | Smart Option | TTFT | Nexus Default |
|---|---|---|---|---|---|
| Intent classification | Groq Llama 3.1 8B Instant | 80–150ms | GPT-4o-mini | 200–400ms | **Groq (always)** |
| Simple Q&A response | GPT-4o-mini (OpenRouter) | 200–400ms | GPT-4o | 400–700ms | **GPT-4o-mini** |
| Browser task planning | GPT-4o-mini | 200–400ms | GPT-4o | 400–700ms | **GPT-4o-mini** |
| Complex reasoning | GPT-4o | 400–700ms | Claude 3.5 Sonnet | 500–800ms | **GPT-4o** |
| Research synthesis | Claude 3.5 Sonnet | 500–800ms | — | — | **Claude (async only)** |
| Windows task planning | Groq Llama 3.1 70B | 150–300ms | GPT-4o-mini | 200–400ms | **Groq 70B** |

### Intent Classification: Always Groq

The intent classification step runs on **every single turn**. It determines whether to route to a simple path or a tool call path. This step must be as fast as possible because it gates everything downstream.

```python
INTENT_CLASSIFICATION_PROMPT = """
Classify this voice command into ONE of these categories:
- simple_answer: general knowledge, quick facts, calculations
- browser_task: web navigation, web search, opening URLs
- windows_task: file operations, app control, system settings
- calendar_task: scheduling, reminders, calendar queries
- email_task: read/send/search email
- research_task: multi-source research, long-horizon tasks
- clarification: ambiguous command, need more info

Command: {transcript}
Respond with JSON: {"intent": "<category>", "confidence": 0.0-1.0}
"""

async def classify_intent(transcript: str) -> Intent:
    response = await groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": INTENT_CLASSIFICATION_PROMPT.format(
                transcript=transcript
            )}
        ],
        max_tokens=50,  # Only need the JSON classification
        temperature=0.0,  # Deterministic classification
    )
    return parse_intent(response.choices[0].message.content)
```

**Why not GPT-4o-mini for classification?** For a binary/categorical classification task with a well-crafted prompt, Llama 3.1 8B is as accurate as GPT-4o-mini. The 150ms savings on every turn compounds massively over a conversation.

### Research Synthesis: Always Async

Research tasks (multi-source synthesis, deep analysis) are explicitly excluded from the real-time TTFA budget. For these:

1. Play filler audio immediately
2. Dispatch research task asynchronously
3. Continue conversation while research runs in background
4. Deliver research result when ready, even if 30–120 seconds later

This is how Perplexity, Gemini, and other voice AI systems handle long-horizon tasks — they acknowledge, then deliver.

### Model Swap-Out Decision Tree

```
Is this a classification/routing decision?
    └── YES → Groq Llama 3.1 8B Instant (always)

Is this a real-time voice response?
    └── YES → Does it require reasoning over complex data?
                  └── YES → GPT-4o via OpenRouter
                  └── NO  → GPT-4o-mini via OpenRouter

Is this a research task (> 30s expected)?
    └── YES → Claude 3.5 Sonnet (async, background task)
```

---

## 8. Tool Call Latency Management

### Strategy Overview

Tool calls are the hardest latency problem in voice AI. The approach has five pillars:

1. Pre-fetch context before the call ends
2. Parallel tool execution when multiple tools needed
3. Hard timeout budgets per tool type
4. Progressive/streaming partial results
5. Caching frequent tool results

### 1. Pre-fetch Context (Speculative Execution)

As the user speaks, predict what tool they're likely to need and pre-fetch auth state or cached data:

```python
class SpeculativePrefetch:
    """
    Start fetching auth tokens and cache checks while STT is still 
    transcribing, so they're ready when the turn finalizes.
    """
    
    async def on_partial_transcript(self, partial: str):
        """Called on every Deepgram interim result."""
        
        # Detect likely intent from partial
        likely_intent = self.quick_classify(partial)
        
        if likely_intent == "calendar" and not self.calendar_token_fresh:
            # Pre-fetch calendar auth token
            asyncio.create_task(self.prefetch_calendar_token())
        
        elif likely_intent == "email" and not self.email_cache_fresh:
            # Pre-fetch unread count (high probability it'll be needed)
            asyncio.create_task(self.prefetch_email_summary())
    
    def quick_classify(self, partial: str) -> str:
        """Regex-based fast classification for speculative execution."""
        patterns = {
            "calendar": r"\b(schedule|meeting|calendar|appointment|when is|remind)\b",
            "email": r"\b(email|inbox|unread|message|from|sent)\b",
            "browser": r"\b(open|go to|search|navigate|website|look up)\b",
            "windows": r"\b(file|folder|open app|launch|close|volume|screen)\b",
        }
        for intent, pattern in patterns.items():
            if re.search(pattern, partial, re.IGNORECASE):
                return intent
        return "unknown"
```

This adds ~0ms to the user's perceived latency (runs concurrently with transcription) but can eliminate 100–300ms from tool setup time.

### 2. Parallel Tool Calls

When a turn requires multiple tools, execute them concurrently:

```python
async def execute_parallel_tools(tool_calls: list[ToolCall]) -> list[ToolResult]:
    """Execute multiple tool calls simultaneously."""
    tasks = [execute_tool(tc.name, tc.args) for tc in tool_calls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [
        r if not isinstance(r, Exception) else ToolError(str(r))
        for r in results
    ]

# Example: "What's on my calendar today, and how many unread emails do I have?"
# Executes both calendar and email tools simultaneously → saves 300-500ms
```

### 3. Tool Timeout Budgets

Hard timeouts prevent runaway tools from freezing the conversation:

```python
TOOL_TIMEOUT_BUDGETS = {
    "browser_navigate": 60.0,      # 60s — browser tasks can be slow
    "browser_search": 30.0,        # 30s — web search
    "windows_file": 10.0,          # 10s — local file operations
    "windows_app": 5.0,            # 5s — app launch/control
    "windows_system": 5.0,         # 5s — system settings
    "calendar_read": 8.0,          # 8s — calendar API
    "calendar_write": 10.0,        # 10s — calendar write
    "email_read": 10.0,            # 10s — email fetch
    "email_send": 15.0,            # 15s — email send
    "research": 120.0,             # 120s — long-horizon research
}

async def execute_tool_with_timeout(
    tool_name: str, 
    args: dict,
    agent: VoiceAgent,
) -> ToolResult:
    timeout = TOOL_TIMEOUT_BUDGETS.get(tool_name, 30.0)
    
    try:
        return await asyncio.wait_for(
            run_tool(tool_name, args),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        await agent.say("That's taking longer than expected. I'll keep trying in the background.")
        # Optionally: retry with backoff or mark as async task
        raise ToolTimeoutError(tool_name, timeout)
```

### 4. Progressive/Streaming Tool Results

For browser tasks that return incremental data, stream partial results back immediately:

```python
async def browser_task_with_streaming(url: str, task: str, agent: VoiceAgent):
    """Navigate to URL and stream partial results to user."""
    
    async for event in vision_agents_browser.execute_streaming(url, task):
        if event.type == "page_loaded":
            await agent.say("Page loaded. Extracting information…")
        
        elif event.type == "partial_result":
            # Stream partial result to TTS immediately
            await agent.say(f"I can see {event.partial_data}. Still reading…")
        
        elif event.type == "final_result":
            await agent.say(event.final_data)
            break
```

### 5. Result Caching

Cache frequent, low-volatility tool results to eliminate round-trip latency:

```python
import redis
import json
from datetime import timedelta

class ToolResultCache:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    # Cache TTL configuration (how long results stay valid)
    CACHE_TTL = {
        "email_unread_count": timedelta(minutes=5),
        "calendar_today": timedelta(minutes=10),
        "calendar_this_week": timedelta(minutes=30),
        "weather_current": timedelta(minutes=15),
        "browser_static_page": timedelta(hours=1),
    }
    
    async def get_or_execute(
        self, 
        tool_name: str, 
        args: dict, 
        executor: callable
    ) -> ToolResult:
        cache_key = f"tool:{tool_name}:{hash(json.dumps(args, sort_keys=True))}"
        ttl = self.CACHE_TTL.get(tool_name)
        
        if ttl:
            cached = await self.redis.get(cache_key)
            if cached:
                return ToolResult.from_json(cached)  # Cache hit — 0ms execution
        
        # Cache miss — execute and store
        result = await executor(tool_name, args)
        
        if ttl and result.success:
            await self.redis.setex(cache_key, int(ttl.total_seconds()), result.to_json())
        
        return result
```

**What to cache vs. what not to cache:**

| Tool | Cache? | TTL | Reason |
|---|---|---|---|
| Email unread count | Yes | 5 min | Changes infrequently, frequently asked |
| Email read/content | No | — | Content changes, privacy |
| Calendar today | Yes | 10 min | Frequently asked, changes ~hourly |
| Calendar write | No | — | Side effects, must execute |
| Weather | Yes | 15 min | Changes slowly |
| Browser (static) | Yes | 1 hr | FAQs, documentation pages |
| Browser (dynamic) | No | — | News, prices, live data |
| Windows file list | No | — | Volatile, user changes files |

---

## 9. Network Optimization

### Railway Region Selection

The backend runs on Railway (cloud). Region selection is a one-time decision with permanent latency impact. Choose based on where the majority of your early user base is located:

| User concentration | Recommended Railway region | Expected backend latency |
|---|---|---|
| North America (East) | `us-east4` (Virginia) | 20–40ms |
| North America (West) | `us-west2` (Oregon) | 30–60ms |
| Europe | `europe-west4` (Netherlands) | 20–40ms |
| Mixed global | `us-east4` (default) | 20–80ms |

For a Windows power user product launching in the US, start with `us-east4`. Add a second region (EU) when you have significant EU users.

### Connection Optimization

#### HTTP/2 for All API Connections

All LLM and TTS API calls must use HTTP/2. This is enabled by default in modern Python `httpx` clients but verify:

```python
import httpx

# HTTP/2 enabled — check this in your client initialization
client = httpx.AsyncClient(http2=True)

# Verify with:
response = await client.get("https://api.openai.com/v1/models")
print(response.http_version)  # Should print "HTTP/2"
```

HTTP/2 multiplexing allows multiple API requests over a single connection, eliminating TCP handshake overhead on every LLM call (~50ms savings per call).

#### Keep-Alive Connections

Maintain persistent connections to LLM providers. A new TCP+TLS handshake to OpenAI or Groq costs 80–150ms. Keep connections alive:

```python
# Create one client per provider at application startup
# Reuse across all requests — never create per-request clients

class APIClients:
    def __init__(self):
        self.openai = openai.AsyncOpenAI(
            http_client=httpx.AsyncClient(
                http2=True,
                limits=httpx.Limits(
                    max_keepalive_connections=20,
                    max_connections=40,
                    keepalive_expiry=30.0,
                )
            )
        )
        self.groq = groq.AsyncGroq(
            http_client=httpx.AsyncClient(http2=True)
        )

# Initialize at startup
api_clients = APIClients()
```

### Railway: Prevent Cold Starts

On Railway's paid tier, configure always-on deployment to eliminate cold start latency (1–3s for cold containers):

```toml
# railway.toml
[deploy]
sleepApplication = false   # Never sleep — always-on
healthcheckPath = "/health"
healthcheckTimeout = 10
restartPolicyType = "ON_FAILURE"
```

A sleeping Railway service wakes up in 1–3 seconds. For voice AI, this means the first user of the day would experience 2–4 second TTFA. Always-on eliminates this.

### GetStream Audio Network

GetStream's global media network handles audio transport automatically. No additional configuration is required for audio latency — GetStream routes audio through the nearest edge node to both client and server. The 30–50ms WebRTC transport budget already accounts for this.

---

## 10. Monitoring & Alerting

### What to Track in Production

Effective latency monitoring requires granular spans, not just end-to-end timers. Every stage of the pipeline needs an individual measurement.

```python
import langfuse
from contextvars import ContextVar

trace_ctx: ContextVar[langfuse.Trace] = ContextVar("trace_ctx")

async def handle_voice_turn(transcript: str, turn_id: str):
    # Create Langfuse trace for this turn
    trace = langfuse.trace(
        name="voice_turn",
        id=turn_id,
        tags=["voice", "nexus-2.0"],
    )
    trace_ctx.set(trace)
    
    with trace.span("intent_classification") as span:
        intent = await classify_intent(transcript)
        span.update(
            output=intent.dict(),
            metadata={"model": "groq/llama-3.1-8b-instant"}
        )
    
    if intent.type == "tool_call":
        with trace.span("filler_audio") as span:
            await play_filler(intent.tool_category)
        
        with trace.span("tool_execution") as span:
            span.update(metadata={"tool": intent.tool_name})
            result = await execute_tool(intent.tool_name, intent.tool_args)
            span.update(output={"success": result.success})
        
        with trace.span("llm_summarization") as span:
            summary_gen = stream_summarization(result, transcript)
    else:
        with trace.span("llm_response") as span:
            summary_gen = stream_llm_response(transcript)
    
    with trace.span("tts_streaming") as span:
        first_audio_at = None
        async for audio_chunk in stream_tts_audio(summary_gen):
            if first_audio_at is None:
                first_audio_at = time.monotonic()
                span.update(metadata={"ttfa_ms": (first_audio_at - turn_start) * 1000})
            yield audio_chunk
```

### Metrics Dashboard: What to Capture

| Metric | Description | Alert threshold |
|---|---|---|
| `ttfa_p50` | Median TTFA across all turns | Alert if > 1200ms |
| `ttfa_p90` | 90th percentile TTFA | Alert if > 1500ms |
| `ttfa_p99` | 99th percentile TTFA | Alert if > 3000ms |
| `stt_latency_p90` | Deepgram processing time | Alert if > 350ms |
| `llm_ttft_p90` | LLM first token time by model | Alert if > 600ms |
| `tts_first_chunk_p90` | TTS time to first audio chunk | Alert if > 300ms |
| `tool_execution_p90` | Tool execution time by tool type | Alert if > 5000ms |
| `intent_classification_p90` | Groq classification time | Alert if > 300ms |
| `turns_per_minute` | Throughput (capacity planning) | Alert if > 80% of rate limit |
| `tool_cache_hit_rate` | Cache effectiveness | Alert if < 30% for frequent tools |

### Langfuse Trace Configuration

Set up Langfuse to capture end-to-end traces with nested spans:

```python
# Initialize in app startup
langfuse.configure(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
)

# Define span hierarchy for Langfuse UI
# Each span shows up as a nested timeline in the trace viewer:
# 
# voice_turn [total: 850ms]
# ├── stt_processing [200ms]
# ├── vad_finalization [50ms]
# ├── intent_classification [110ms]
# ├── llm_response [320ms]
# │   └── openrouter_api_call [310ms]
# └── tts_streaming [170ms]
#     └── openai_tts_api [160ms]
```

### Alerts to Configure

```yaml
# Example alert configuration (Langfuse or your alerting system)
alerts:
  - name: "P90 TTFA Critical"
    condition: "ttfa_p90 > 1500"
    window: "5m"
    severity: "critical"
    channels: ["slack#nexus-ops", "pagerduty"]
  
  - name: "P90 TTFA Warning"
    condition: "ttfa_p90 > 1000"
    window: "10m"
    severity: "warning"
    channels: ["slack#nexus-ops"]
  
  - name: "STT Latency Spike"
    condition: "stt_latency_p90 > 400"
    window: "5m"
    severity: "warning"
    channels: ["slack#nexus-ops"]
  
  - name: "Groq Rate Limited"
    condition: "error_rate{provider='groq', error='rate_limit'} > 0.01"
    window: "1m"
    severity: "critical"
    channels: ["slack#nexus-ops"]
```

---

## 11. Latency Testing Checklist

Run this checklist before every major launch milestone. All measurements should be taken from the Railway backend's perspective, not locally.

### Pre-Launch Benchmarks

- [ ] **Deepgram streaming latency from Railway region**
  ```bash
  # From Railway shell: measure STT latency with a test audio clip
  python benchmark/deepgram_latency.py --audio test_clips/3s_sentence.wav
  # Expected: first partial < 200ms, final transcript < 400ms
  ```

- [ ] **Groq TTFT at expected RPM**
  ```bash
  # Groq Llama 3.1 8B Instant — benchmark at 10, 50, 100 RPM
  python benchmark/groq_ttft.py --rpm 10 --iterations 50
  python benchmark/groq_ttft.py --rpm 100 --iterations 50
  # Expected: P90 < 200ms at up to 100 RPM
  ```

- [ ] **GPT-4o-mini TTFT via OpenRouter**
  ```bash
  python benchmark/openrouter_ttft.py --model openai/gpt-4o-mini --iterations 50
  # Expected: P50 < 300ms, P90 < 500ms
  ```

- [ ] **OpenAI TTS first-chunk latency**
  ```bash
  python benchmark/tts_latency.py --model tts-1 --text "Your appointment is confirmed."
  # Expected: P50 < 200ms, P90 < 300ms
  ```

- [ ] **End-to-end timestamp test**
  ```bash
  # Record: speak → measure → hear response
  # Use test harness with synthetic audio injection
  python e2e/measure_ttfa.py --scenario simple_answer --iterations 20
  # Expected: P50 < 900ms, P90 < 1200ms
  ```

- [ ] **Load test: 10 concurrent voice users**
  ```bash
  python loadtest/voice_concurrent.py --users 10 --duration 300s
  # Expected: P90 stays < 1500ms under 10 concurrent users
  # Monitor: Groq rate limits, Railway CPU, Railway memory
  ```

- [ ] **Filler audio triggers before browser task completes**
  ```bash
  python e2e/tool_call_filler.py --tool browser --scenario open_url
  # Verify: filler audio starts < 600ms after end of user speech
  # Verify: filler audio starts BEFORE browser result returns
  ```

- [ ] **VAD does not cut off 3-second utterances**
  ```bash
  python e2e/vad_test.py --test_clips long_utterances/
  # Test with clips that have 300ms mid-sentence pauses
  # Verify: no premature cut-offs
  ```

- [ ] **Barge-in stops playback within 100ms**
  ```bash
  python e2e/barge_in_test.py
  # Inject audio while assistant is playing; verify audio stops < 100ms
  ```

- [ ] **Cold start latency (simulate Railway restart)**
  ```bash
  # Restart Railway service; immediately send voice turn
  # Expected: < 5s additional latency (acceptable for cold start)
  # Verify: always-on setting prevents this in production
  ```

### Regression Test Suite

After any infrastructure change, run the regression suite:

```bash
# Full regression suite (runs all benchmarks + E2E tests)
python tests/latency_regression.py --env staging

# Pass thresholds:
#   ttfa_p50 < 900ms
#   ttfa_p90 < 1500ms
#   stt_p90 < 400ms
#   llm_ttft_p90 < 600ms
#   tts_first_chunk_p90 < 300ms
```

---

## 12. Optimization Roadmap

### Phase 1: MVP — Accept Defaults, Ship Fast

**Timeline:** Month 1  
**Goal:** Working product, not optimized product.

- Use Deepgram streaming with default settings (endpointing 300ms)
- Use GPT-4o-mini for all responses (including intent — fast enough at low load)
- Use OpenAI TTS streaming (sentence chunking, basic implementation)
- Deploy to Railway US-East4 with always-on
- Add basic Langfuse logging for TTFA end-to-end (no per-span granularity yet)
- Filler audio: implement but use simple pre-recorded clips

**Expected TTFA:** 900ms–1400ms (acceptable for MVP)

**What NOT to do in Phase 1:** Don't over-optimize. Ship working features. Latency data from real users is more valuable than theoretical optimization.

### Phase 2: Monitoring & Baseline — Know Your Numbers

**Timeline:** Month 2  
**Goal:** Full observability; identify the actual bottlenecks.

- Add granular Langfuse spans (STT, intent, LLM, TTS individually)
- Add P50/P90/P99 dashboards for each span
- Add error rate tracking per provider
- Tune VAD endpointing to 400ms based on observed user behavior
- Implement Groq for intent classification (breaking it out from GPT-4o-mini)
- Analyze which tool types have the worst latency → prioritize caching for those

**Expected outcome:** Clear per-stage latency data, actionable bottleneck list for Phase 3.

### Phase 3: Targeted Optimization — Cut the Bottlenecks

**Timeline:** Month 3+  
**Goal:** Hit sub-900ms P50 on simple turns consistently.

**Priority order (attack biggest wins first):**

1. **Redis cache for frequent tool results** — biggest ROI for tool-heavy users
   - Cache calendar, email unread count, weather → eliminates 300–800ms per cached turn
   
2. **Parallel tool execution** — for multi-step commands
   - "Check my email and calendar" → both in parallel → saves 300–500ms
   
3. **Smarter VAD with adaptive threshold** — reduce VAD wait on clean audio
   - 400ms → 350ms in quiet environments → saves 50ms on every turn

4. **Speculative pre-fetch** — start fetching auth state on partial transcripts
   - Saves 100–300ms on tool setup time

5. **Sentence chunking optimization** — tune chunk size for TTS latency
   - Shorter first sentence = faster first audio chunk

6. **OpenRouter fallback routing** — automatic failover if primary model is slow
   - Configure backup routes for GPT-4o-mini if P90 > 500ms

**Expected TTFA after Phase 3:** 700ms–1000ms P50, 1000ms–1400ms P90

### Phase 4: Scale — Multi-Region, Edge Optimization

**Timeline:** Scale phase (> 1000 daily active users)  
**Goal:** Consistent sub-800ms globally, regardless of user geography.

- **Multi-region Railway deployment**: Add EU-West4 for European users
  - Route users to nearest region via Cloudflare or Railway routing
  - Expected savings: 80–150ms for EU users vs. US-only backend
  
- **Dedicated Railway dynos** (Railway Pro): Dedicated CPU for voice processing
  - Eliminates noisy-neighbor latency spikes on shared infrastructure
  
- **Deepgram self-hosted (optional)**: At high volume, Deepgram on-prem in Railway
  - Reduces STT latency by ~50ms (no external API hop)
  - Only worth it at > 50,000 STT requests/day
  
- **OpenAI TTS alternative evaluation**: Benchmark Cartesia, ElevenLabs, Deepgram Aura
  - Some alternatives have 80–100ms TTFC vs. OpenAI's 150–200ms
  
- **Intent model fine-tuning**: Fine-tune a small model on Nexus-specific intent patterns
  - Could replace Groq Llama 3.1 8B with a specialized 1B model → < 50ms classification

---

## Appendix: Quick Reference

### Budget Summary

```
SIMPLE TURN (target: < 800ms)
├── WebRTC transport:    30–50ms
├── STT streaming:       150–200ms
├── VAD finalization:    50–100ms
├── Network:             20–50ms
├── Intent (Groq):       80–150ms
├── LLM TTFT (mini):     200–400ms
└── TTS first chunk:     150–200ms
                         ─────────
Total (optimized):       680–1150ms
Target achieved when all stages hit lower bounds simultaneously.

TOOL CALL TURN (target: < 2s perceived)
├── Everything to intent:   350–550ms
├── Filler audio:           plays at 400–600ms ← perceived TTFA
├── Tool execution:         500–3000ms (invisible to user)
├── LLM summary TTFT:       200–400ms
└── TTS first chunk:        150–200ms
                            ─────────
Perceived TTFA:             400–600ms (filler audio)
Actual result latency:      1200–4000ms
```

### Provider Contacts & SLAs

| Provider | API | Latency SLA | Status page |
|---|---|---|---|
| Deepgram | STT streaming | 99.9% uptime | status.deepgram.com |
| Groq | Llama 3.1 8B | 99.5% uptime | console.groq.com |
| OpenRouter | GPT-4o-mini | 99.5% uptime | openrouter.ai/status |
| OpenAI | TTS-1 | 99.9% uptime | status.openai.com |
| GetStream | WebRTC/Video | 99.99% uptime | getstream.io/status |
| Railway | Hosting | 99.9% uptime | status.railway.app |

### Key Configuration Values

```python
# Copy-paste reference for implementation
NEXUS_LATENCY_CONFIG = {
    # VAD
    "vad_endpointing_ms": 400,
    "vad_utterance_end_ms": 1000,
    
    # Models
    "intent_model": "groq/llama-3.1-8b-instant",
    "response_model": "openai/gpt-4o-mini",  # via OpenRouter
    "tts_model": "tts-1",
    "tts_voice": "alloy",
    "tts_format": "opus",
    
    # Timeouts
    "tool_timeout_browser": 60,
    "tool_timeout_windows": 10,
    "tool_timeout_research": 120,
    "tool_timeout_default": 30,
    
    # Alerts
    "alert_ttfa_p90_ms": 1500,
    "alert_ttfa_critical_ms": 3000,
    
    # Cache TTLs (seconds)
    "cache_email_unread": 300,
    "cache_calendar_today": 600,
    "cache_weather": 900,
}
```
