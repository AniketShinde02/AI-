# NEXUS: NOVA VISION
**Future Architecture Document**
*Status: Concept & Long-Term Vision Only (Do Not Implement Yet)*

---

## 1. Core Philosophy

**Nexus Core** remains the unyielding intelligence layer—the processing engine, the reasoning system, and the backend orchestrator. 

**Nova** becomes the visual embodiment of Nexus. 
Nova does not *replace* the AI; Nova *represents* the AI's internal state visually. 

**Design Goal:**
Make Nexus feel fundamentally alive and reactive without becoming a "VTuber." The assistant must feel like a premium, state-of-the-art AI operating system rather than a generic chatbot. Nova should be an elegant, sophisticated entity that bridges the gap between raw data processing and human-like responsiveness.

---

## 2. Visual States & Behaviors

Nova acts as a visual state machine, directly mirroring the internal processing and context of the Nexus Core.

| State | Visual Representation & Animation Concept |
| :--- | :--- |
| **Idle** | Subtle, calm breathing animation. Gentle ambient glow. Waiting for interaction. |
| **Listening** | Active focus. Elements shift to indicate acoustic processing (e.g., subtle audio reactivity, leaning in, or brightened aura). |
| **Thinking** | Processing mode. Eyes close or narrow in focus, accompanied by computational particle effects, data streams, or orbital ring activity. |
| **Speaking** | Mouth/core sync with audio output. Dynamic waveform integration that reacts perfectly to syllables and tone. |
| **Searching** | Scanning mode. Green/cyan data effects, rapid eye movement, or sweeping light passes indicating high-speed information retrieval. |
| **Coding** | Deep focus mode. Terminal glow reflection, sharp focus expression. Possibly accompanied by floating syntax elements or hex grids. |
| **Error** | Disrupted state. Subtle red/amber warning pulses, glitch effects, or a pained/confused expression indicating a blockage or fault. |
| **Celebration** | Success state. Bright, expansive energy, positive expression, soft warm colors indicating task completion or user praise. |

---

## 3. Future Technical Requirements

To achieve this vision, the Nova embodiment layer will require a specific technical architecture built on top of the Nexus frontend:

### 3.1 Live2D / WebGL Compatibility
- **Primary Engine:** Integration of a WebGL rendering context (e.g., PixiJS, Three.js, or Live2D Cubism Web Framework) to render the Nova entity smoothly in the browser or Tauri desktop app.
- **Fluidity:** Must run at a locked 60/120fps to maintain the "premium OS" feel. Jitter breaks the illusion.

### 3.2 PNG / Canvas Fallback
- **Graceful Degradation:** A lightweight, static, or CSS-animated PNG/SVG fallback system for low-power devices, mobile modes, or when WebGL contexts are lost.

### 3.3 Expression Engine
- **Procedural Blending:** An engine capable of blending expressions (e.g., moving from "Thinking" to "Speaking" seamlessly without rigid frame jumps).
- **Micro-expressions:** Procedural eye darts, blinks, and subtle head tilts to simulate presence.

### 3.4 State Machine Integration
- **Strict Coupling:** Nova's animation state must be strictly bound to the `useNexusVoice` / `NexusContext` state machine (e.g., `status === 'thinking' -> trigger('Thinking')`).

### 3.5 Voice Reactive Animation
- **Real-time Lip Sync:** Hooking into the AudioContext API or receiving real-time viseme data from the backend TTS (e.g., Cartesia/ElevenLabs) to drive mouth shapes and overall body reactivity accurately.

### 3.6 Tool-Aware Animations
- **Contextual Awareness:** Nova should react to the *type* of tool being used. (e.g., running `search_web` triggers the "Searching" state; running `write_to_file` triggers the "Coding" state).

---

## 4. UI / UX Aesthetic Integration

Drawing inspiration from high-end AI concepts (like the *Mia Personal AI Assistant*), Nova will live within the existing glassmorphic, dark-themed UI. 

- **Placement:** Nova will either occupy a dedicated "Vision Core" card or sit persistently in a designated holographic quadrant of the screen.
- **Lighting:** Nova's lighting should reflect the overall UI theme (Indigo/Purple default) but shift dynamically based on state (e.g., Green for network/search, Amber for warnings).

---
*Note: This document is for architectural alignment and future planning. Implementation of the Nova embodiment layer is deferred until the core text/voice and reasoning pipelines are fully stabilized and deployed.*
