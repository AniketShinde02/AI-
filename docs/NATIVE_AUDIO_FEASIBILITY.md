# Gemini Native Audio Dialog Feasibility Study

## Objective
To determine whether Google's experimental Gemini Native Audio Dialog model (`gemini-2.5-flash-native-audio-latest`) can realistically replace the dedicated `gemini-2.5-flash-preview-tts` model in Nexus to bypass the 100 RPM rate limit, *without* altering the core architecture (Groq STT → Groq LLM → Audio).

## Verification Results

A standalone test script (`test_native_audio.py`) was successfully executed using the `google-genai` Python SDK against the `gemini-2.5-flash-native-audio-latest` model.

*   **Does it accept text-only input?** 
    **Yes.** It can accept text strings via `session.send(input="text")` without needing live microphone audio.
*   **Does it return audio output?** 
    **Yes.** By setting `response_modalities=["AUDIO"]`, the model returns raw PCM audio data in its `server_content` parts.
*   **Does it support custom voices?** 
    **Yes.** It accepts `SpeechConfig` -> `VoiceConfig` to set predefined voice personas (e.g., "Puck", "Aoede").
*   **Does it support system prompts/personas?** 
    **Yes.** System instructions can be passed during the connection initialization.
*   **Does it require websocket sessions?** 
    **YES (Critical Blocker).** The standard REST API (`generate_content`) throws a `404 NOT_FOUND / INVALID_ARGUMENT` when attempting to request the `AUDIO` modality. The Native Audio model enforces the use of the **Live API**, which requires establishing an asynchronous WebSocket connection (`client.aio.live.connect()`).
*   **Can it operate without microphone streaming?** 
    **Yes.** It functions purely on text sending over the websocket.

## The "LLM Interpretation" Problem (Major Limitation)
During the test, the input text was: 
`"Hello from Nexus. This is a test of the Native Audio Dialog model acting as a text to speech provider."`

The model successfully returned ~200KB of audio, but it **also returned text** and *interpreted* the input as a prompt to respond to, rather than text to dictate. 

**Model's internal response logic:**
> *"I recognize "Nexus" as the user and understand their purpose: a test of the Native Audio Dialog model for text-to-speech. I am the text-to-speech provider for this evaluation."*

**Why this breaks Nexus:** 
Because Groq LLM already generates the final response, if we feed Groq's output into Gemini Native Audio, Gemini will try to "converse" with Groq's output instead of simply reciting it word-for-word. We would have to inject heavy system prompts (e.g., "You are a dumb TTS engine, recite exactly what is given to you without adding commentary") which is highly unstable and prone to hallucinations or conversational drift.

## Architectural Impact

To implement this inside `tts_gemini.py`, we would need to:
1. Replace the simple REST `generate_content` call with a WebSocket session lifecycle management system.
2. If we open/close the WebSocket for every single sentence (since Nexus chunks sentences for low latency), the handshake overhead will introduce massive latency.
3. If we keep a persistent WebSocket open, we must overhaul the TTS Router to maintain persistent state per-user session.

## Conclusion: Feasibility = LOW / UNSUPPORTED

While technologically possible, replacing the dedicated Gemini TTS model with the Gemini Live Audio model **violates the core requirement** of keeping modifications minimal and preserving the current architecture. 

### Required Changes (If we forced it)
- Complete rewrite of `tts_gemini.py` to support persistent WebSockets via the Live API.
- Implementation of a strict "Recitation-only" system prompt.
- Complex parsing to strip out any conversational text/audio hallucinations the model adds to the output.

### Recommendation
**Do not proceed with migration.** The dedicated `gemini-2.5-flash-preview-tts` model is fundamentally designed to be a dumb pipe (Text In -> Exact Audio Out). The Native Audio model is an intelligent agent that expects a conversation. To solve the rate limit issue, the only stable path is utilizing Edge TTS as the primary fallback, or upgrading the Google AI Studio tier.
