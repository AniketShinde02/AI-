# Nexus Speech Cleanup Plan

Voice dictation directly from STT engines is often messy, containing filler words, self-corrections, and poor punctuation. To make the assistant sound human, smart, and professional, we must implement a deterministic **Speech Cleanup Pipeline**.

## The Problem
Raw STT output looks like:
> *"Uh, wait, actually can you, um, tell me the weather in, no, wait, tell me the time in London?"*

Target Output:
> *"Tell me the time in London."*

## Free Path Comparison

### 1. Whisper (Current Groq Implementation)
* **Pros**: Free (via Groq API), exceptionally fast (< 500ms latency), excellent multilingual support.
* **Cons**: Tends to hallucinate during silence, captures filler words verbatim if prompted loosely.
* **Verdict**: Keep as the primary STT engine.

### 2. OWSM v3.1 / Kaldi-based Toolkits
* **Pros**: Open-source, highly accurate for offline setups.
* **Cons**: Heavy local installation, high CPU/RAM overhead, slower latency than Groq cloud. 
* **Verdict**: Not recommended for a lightweight, web-first brain architecture.

## The Chosen Strategy: LLM-Based Normalization Pipeline
Instead of relying on heavy local audio parsers, we will use an ultra-fast, secondary LLM pass (using a highly quantized local model or a cheap Groq endpoint like Llama-3-8b) specifically instructed for *Denoising and Normalization*.

### The Pipeline Architecture
1. **Raw Transcription**: Groq Whisper generates raw text.
2. **Text Normalization Node**: The text is immediately passed to a secondary, lightning-fast LLM prompt:
   * **System Prompt**: `You are a transcription cleaner. Remove all filler words (um, uh, actually, wait), resolve self-corrections, fix punctuation, and output ONLY the final intended sentence. Do not answer the prompt.`
3. **Command Extraction**: If the cleaned text matches a known tool command schema, route to Tool Registry. Else, route to Main LLM for conversation.

### Implementation Steps
1. Create `backend/voice_agent/speech_cleaner.py`.
2. Insert the `SpeechCleaner` class into `ws_main.py` immediately after the Groq Whisper STT returns.
3. Measure the latency. If the Llama-3-8b pass takes < 200ms on Groq, it is viable for production real-time voice streaming.
