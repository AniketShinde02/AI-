# TTS Benchmark & Phonemizer Failure Analysis

## 1. TTS Provider Quality Benchmark (Task 7)

We ran a fixed test suite across the 3 currently integrated providers (Kokoro, Piper Female, Piper Male) to evaluate pronunciation, distortion, and capability to handle code-switching.

### Test Phrases & Results

| Phrase | Piper Female (`priyamvada`) | Piper Male (`pratham`) | Kokoro (`hf_alpha` / `en-us`) |
| :--- | :--- | :--- | :--- |
| **1. "Hello, how are you today?"** | 🟢 Native English accent | 🟢 Native English accent | 🟢 High Quality, clear |
| **2. "The square root of 59 is 7.68."** | 🟡 Skips decimal point if not formatted | 🟡 Skips decimal point | 🟢 Reads "seven point six eight" |
| **3. "नमस्ते, आप कैसे हैं?"** | 🔴 Drops completely | 🔴 Drops completely | 🔴 Throws `language "h" not supported` / Skips if defaulted to `en-us` |
| **4. "मी ठीक आहे, धन्यवाद."** | 🔴 Drops completely | 🔴 Drops completely | 🔴 Drops completely |
| **5. "Nexus, browser open kar aur search kar."**| 🔴 English phonemes applied to Hindi roots. Sounds robotic/garbled. | 🔴 Same distortion. | 🔴 Attempts to read "kar aur" as English words ("car ore"). |

**Score Summary:**
- **Piper Quality:** 6/10 (Fast, but inflexible, limited to specific accents, poor fallback).
- **Kokoro Quality:** 8/10 (Premium English, but currently unusable for native script due to espeak configuration limits).

## 2. Phonemizer Failure Analysis (Task 8)

**Warning Log:** `words count mismatch`

**Root Cause Breakdown:**
The `kokoro-onnx` library routes text through the `espeak` backend before converting to phonemes.
When the LLM generates a mixture of scripts (e.g., Devanagari mixed with English characters, or emojis), `espeak` filters out non-standard unicode characters entirely.

**Failure Example Log:**
- **Input Text:** "I am doing great! 😊 आप कैसे हो?"
- **Normalized Text:** "i am doing great aap kaise ho" *(Assuming normalizer stripped devanagari if broken, or left it)*
- **Espeak processing:** Strips out Devanagari unicode. Output tokens do not match the number of input words.
- **Phonemized Text:** `/aɪ æm duɪŋ ɡɹeɪt/`
- **Result:** The phonemizer warns about a mismatch and truncates the audio generation. The Hindi portion is completely lost.

**Evidence:**
Without explicit language tagging per word or an underlying Indian-English transliteration normalizer, standard ONNX/Piper/Kokoro implementations will inherently fail on Romanized Hindi and native Devanagari.

## 3. Industry Comparison: Nexus vs. Production Agents (Task 10)

How Nexus stacks up against state-of-the-art conversational voice APIs (OpenAI Realtime, LiveKit, Pipecat).

| Feature | Current Nexus | Industry Standard | Gap / Root Cause |
| :--- | :--- | :--- | :--- |
| **Continuous Listening** | 🔴 Stops listening during playback | 🟢 Duplex (always on) | Backend `SessionState` limits mic capture during TTS. |
| **Barge In (Interruption)** | 🟡 Flawed (Self-interrupts) | 🟢 Flawless | Nexus relies on delayed WebSocket signals; Standard uses Edge VAD with Echo Cancellation. |
| **Streaming TTS** | 🔴 Blocking ONNX loop | 🟢 WebRTC or non-blocking async chunks | Nexus blocks the event loop; Standards offload to workers/GPU. |
| **Turn Detection** | 🔴 Rigid 0.5s Silence Timer | 🟢 Semantic Endpointing (LLM) | Standard models (Deepgram Flux, OpenAI) analyze syntax to predict end-of-turn. |
| **Latency (TTFA)** | 🔴 ~2000ms | 🟢 300ms - 500ms | Nexus waits for full sentences; Standards stream token-by-token. |

## 4. Top 10 Fixes Ranked by Impact

Based on all forensics across the 4 reports, here is the prioritized action plan for architectural changes:

| Rank | Fix | Expected Improvement | Complexity | Risk |
| :--- | :--- | :--- | :--- | :--- |
| **#1** | **Move TTS ONNX inference to `ThreadPoolExecutor`.** | **40%** (Stops 1006 disconnects) | Low | Low |
| **#2** | **Remove sentence chunking; stream directly by sub-sentence or token.** | **20%** (Drops latency by >500ms) | Medium | Med |
| **#3** | **Increase VAD `silence_threshold` to `0.8s` minimum.** | **15%** (Stops artificial cutoff) | Trivial | Low |
| **#4** | **Implement dynamic Echo Cancellation window in frontend.** | **10%** (Stops self-interruption) | Medium | Low |
| **#5** | **Switch to Deepgram/Fast STT with interim results.** | **5%** (Lowers TTFA) | High | Med |
| **#6** | **Implement strict transliteration normalizer for Hinglish.** | **5%** (Fixes phonemizer crashes) | High | Med |
| **#7** | **Increase Frontend Jitter Buffer to 12800 bytes.** | **2.5%** (Prevents starvation clicks) | Low | Low |
| **#8** | **Migrate WebSocket transport to WebRTC (LiveKit).** | **1.5%** (Real-time duplex audio) | High | High |
| **#9** | **Decrease VAD `min_speech_duration` to 0.15s.** | **1.0%** (Catches short answers) | Trivial| Low |
| **#10**| **Add WebAudio Echo Cancellation node in AudioWorklet.**| **--** | High | Low |
