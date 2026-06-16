# **Technical Architecture Report: Project Nexus**

## **A. Executive Summary**

The transition from cloud-dependent artificial intelligence to localised, privacy-preserving agentic systems represents a fundamental paradigm shift in computing architecture. Project Nexus aims to establish a robust, 100% local, voice-first, Bring-Your-Own-Key (BYOK) AI assistant. Unlike enterprise solutions focused on cloud-based collaboration or remote remote procedure call (RPC) execution1, Nexus is engineered to operate autonomously on consumer-grade hardware. The product operates primarily as a voice-driven operating system layer, facilitating tasks ranging from lead generation and browser automation to deep contextual research and repetitive workflow execution.  
The core engineering challenge of local AI is extreme resource constraint. Cloud models possess virtually infinite computational capacity; local models must aggressively optimise VRAM, CPU cycles, and disk I/O to maintain acceptable latency and prevent thermal throttling. Consequently, the architecture of Nexus prioritises deterministic execution over probabilistic guessing, native operating system integrations over pure vision models, and low-latency Rust backends over heavy Python inference servers. By combining the deterministic nature of accessibility trees for desktop automation3, embedded graph-vector databases for memory5, and ultra-low-latency voice synthesis7, Nexus delivers a seamless, voice-first user experience without compromising user privacy. Furthermore, because Nexus operates entirely locally for domestic purposes, it achieves absolute exemption from strict data protection laws such as India’s Digital Personal Data Protection (DPDP) Act 20239, forming a formidable legal and architectural moat.

## **B. Taxonomy of Terms and Subsystem Analysis**

This section deconstructs the requisite technologies for Nexus, providing a technical taxonomy, implementation parameters, and staging recommendations for each subsystem.

### **1\) Core AI / ML Concepts**

The foundational intelligence of Nexus relies on generative models, retrieval architectures, and hardware-specific inference optimisations.

| Concept / Subsystem | Implementation Complexity | Runtime Cost | Latency Impact | Privacy Impact | Recommended Stage | Alternatives & Tradeoffs |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **Transformers & Attention** | Low (Pre-built) | High | High | Neutral | MVP | RNNs (Lower context, lower cost but poorer reasoning) |
| **Deep Neural Networks** | Low (Pre-built) | High | High | Neutral | MVP | Symbolic AI (Brittle, lacks generalisation) |
| **RNNs / CNNs** | Low | Low | Low | Neutral | MVP | Transformers for all tasks (Too slow for wake words) |
| **Embeddings** | Medium | Low | Low | Neutral | MVP | Keyword extraction (Lacks semantic understanding) |
| **Semantic Search** | Medium | Low | Low | Neutral | MVP | Lexical search (Faster, less accurate) |
| **Vector Databases** | Medium | Low | Low | Neutral | MVP | Flat arrays (Unscalable beyond a few thousand records) |
| **RAG** | Medium | Medium | Medium | Low Risk | MVP | In-context learning (Exhausts context window) |
| **GraphRAG** | High | High | High | Low Risk | v2 | Standard RAG (Misses multi-hop relational context) |
| **Hybrid Search** | Medium | Medium | Medium | Neutral | v2 | Pure vector search (Misses exact entity names) |
| **Reranking** | High | Medium | Medium | Neutral | v2 | Top-K similarity (Often retrieves irrelevant context) |
| **Fine-tuning / SFT** | High | Low (Inference) | None | Neutral | Long-term | Prompt engineering (Lower accuracy, higher token cost) |
| **LoRA / QLoRA** | High | Low | Low | Neutral | Long-term | Full-parameter tuning (Impossible on consumer hardware) |
| **Distillation** | Very High | Low | Low | Neutral | Long-term | Using base models (Slower, requires more VRAM) |
| **Synthetic Data Generation** | High | High | None | Low Risk | Long-term | Manual data labelling (Too expensive) |
| **RLHF / Constitutional AI** | Very High | Low | None | Neutral | Avoid | System prompts (Slightly less robust but vastly cheaper) |
| **MoE (Mixture of Experts)** | Low (Usage) | Medium | Medium | Neutral | v2 | Dense models (Slower inference for same parameter count) |
| **Context Window** | Base constraint | High | High | Neutral | MVP | Infinite context (Impossible locally) |
| **Context Compression** | High | Medium | Reduces | Neutral | v2 | Raw context injection (Exceeds context limits rapidly) |
| **Summarisation** | Medium | Medium | Medium | Neutral | MVP | Storing raw logs (Creates severe cognitive debt) |
| **Token Efficiency** | High | Low | Reduces | Neutral | MVP | Verbose prompting (Wastes compute cycles) |
| **KV Cache** | Medium (Engine) | High VRAM | Reduces | Neutral | MVP | Recomputing attention (Catastrophically slow) |
| **Speculative Decoding** | High | Medium | Reduces | Neutral | MVP | Standard autoregressive (Slower Time-to-First-Token) |
| **Batching** | Medium | High | High | Neutral | Avoid | Sequential processing (Inefficient for servers, fine locally) |
| **Model Routing** | Medium | Low | Low | Neutral | v2 | Single monolithic model (Inefficient for simple tasks) |

**Foundational Architectures: Transformers, Attention, and Neural Networks** A transformer is a deep neural network architecture that utilises a self-attention mechanism, allowing the model to weigh the importance of all tokens in a sequence simultaneously. This architecture dictates the reasoning capabilities of Nexus. While older architectures like Recurrent Neural Networks (RNNs) and Convolutional Neural Networks (CNNs) have been superseded in text generation, they remain highly relevant for low-latency signal processing; for instance, the livekit-wakeword engine leverages convolutional-attention classifiers to detect wake words at the edge with minimal CPU overhead11.  
**Memory Foundations: Embeddings, Semantic Search, and Vector Databases** Embeddings are high-dimensional numerical representations of unstructured data. Semantic search leverages these embeddings to find meaning rather than exact keyword matches. Vector databases store and index these embeddings for rapid retrieval. For Nexus, a local vector database is mandatory for long-term memory. Client-server databases like Qdrant are overkill for local applications; instead, embedded solutions like sqlite-vec operate directly within the host process, providing robust performance without infrastructure overhead6.  
**Retrieval Systems: RAG, GraphRAG, Hybrid Search, and Reranking** Retrieval-Augmented Generation (RAG) injects retrieved context into the model's prompt. GraphRAG introduces a knowledge graph to map entities and their relationships, vastly improving contextual reasoning over disparate documents5. Hybrid search combines semantic vector search with traditional BM25 keyword search, and reranking uses a secondary cross-encoder model to sort the results. For Nexus, a hybrid GraphRAG system utilizing GraphQLite inside standard SQLite creates a highly advanced, single-file local memory engine, suitable for v2 implementation5.  
**Model Tuning: SFT, LoRA, QLoRA, Distillation, and Synthetic Data** Supervised Fine-Tuning (SFT) adjusts pre-trained weights based on instruction-response pairs. Low-Rank Adaptation (LoRA) and Quantised LoRA (QLoRA) freeze the base model and inject small, trainable matrices, drastically reducing compute requirements. Distillation trains a smaller model to mimic a larger one. Reinforcement Learning from Human Feedback (RLHF) and Constitutional AI align model behaviour to safety guidelines. For Nexus, generating synthetic data to train LoRA adapters locally allows the agent to learn a user's specific workflow without sending data to the cloud. This requires significant engineering and is designated for the long-term roadmap.  
**Inference Optimisations: MoE, KV Cache, Speculative Decoding, and Token Efficiency** Mixture of Experts (MoE) activates only a subset of neural pathways per token, maximising parameter count without proportionally increasing inference compute. The Key-Value (KV) cache stores previous attention calculations in VRAM, preventing redundant computation during ongoing chats. Speculative decoding uses a smaller "draft" model (e.g., a 1.5B parameter model) to predict multiple tokens ahead, which a larger "target" model (e.g., a 12B model) verifies in parallel, significantly accelerating local inference by up to 2x without quality degradation15. For Nexus, speculative decoding via llama.cpp is a strict MVP requirement to achieve real-time conversational latency on consumer Mac/Windows hardware17. Model routing involves directing simple requests (e.g., "what time is it") to smaller models, saving compute. Batching groups multiple requests together; while vital for cloud servers (vLLM), single-user local instances (llama.cpp) prioritise sequential Time-To-First-Token (TTFT) over batched throughput18.

### **2\) Memory and Cognition Systems**

Memory dictates the agent's ability to maintain context over time without overwhelming local hardware and degrading into hallucinatory states.

| Concept / Subsystem | Implementation Complexity | Runtime Cost | Latency Impact | Privacy Impact | Recommended Stage | Alternatives & Tradeoffs |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **Cognitive Debt** | Medium (Mgmt) | Low | Low | Neutral | MVP | Ignoring it (Model degrades rapidly) |
| **Working / Short-term Memory** | Low | Medium | High | Neutral | MVP | Stateless (No context across turns) |
| **Episodic Memory** | High | Low | Low | High Risk | v2 | Flat file logs (Slow, inaccurate) |
| **Semantic Memory** | High | Low | Low | High Risk | v2 | RAG only (Fails to generalise facts) |
| **Long-term Memory** | High | Low | Low | High Risk | MVP | No long-term retention (Amnesic agent) |
| **Memory Layers** | High | Medium | Medium | Low Risk | v2 | Single database (High cognitive debt) |
| **Memory Synchronisation** | High | Low | Low | Neutral | Long-term | Ephemeral state (Loss of context on reboot) |
| **Context Engineering** | Medium | Low | Low | Neutral | MVP | Standard prompting (Wastes tokens) |
| **Prompt Engineering** | Low | Low | Low | Neutral | MVP | Zero-shot prompting (Unreliable output) |
| **Retrieval Pipelines** | Medium | Medium | Medium | Neutral | MVP | Load all data (OOM errors) |
| **Memory Eviction** | Medium | Low | Low | Neutral | v2 | FIFO deletion (Loss of vital core data) |
| **Importance Scoring** | High | Low | Low | Neutral | v2 | Random deletion (Unpredictable behaviour) |
| **User State Modelling** | High | Low | Low | High Risk | v2 | Static persona (Fails to adapt to user mood) |

**Cognitive Debt and Memory Types** Cognitive debt refers to the degradation of model reasoning when the context window is flooded with irrelevant or contradictory data. Working memory (short-term) handles the current session context. Episodic memory stores specific chronological past events ("Yesterday, the user booked a flight to London"), while semantic memory stores synthesised, generalised facts ("The user prefers aisle seats"). Nexus requires a multi-layered memory architecture to isolate these states, preventing context flooding and cognitive debt.  
**Memory Layers, Eviction, and Importance Scoring** A layered approach moves data from active context to vector storage as it ages. Local agents cannot store infinite context in VRAM. Importance scoring algorithms evaluate and rank the relevance of memory nodes based on recency, frequency of access, and emotional weight. Memory eviction protocols then compress or delete low-scoring memories. Implementing importance scoring prevents local databases from bloating and preserves retrieval speed.  
**Context Engineering, Prompt Engineering, and User State Modelling** Context engineering structures data efficiently within the prompt to maximise token efficiency. Prompt engineering dictates the instructions the model follows. User state modelling dynamically tracks the user's ongoing projects, mood, and preferences. For Nexus, modelling the user state allows the system to proactively adjust its tone or tool selection without requiring explicit commands.

### **3\) Agent Architecture**

Agent architecture dictates how Nexus translates natural language user intent into reliable computer actions.

| Concept / Subsystem | Implementation Complexity | Runtime Cost | Latency Impact | Privacy Impact | Recommended Stage | Alternatives & Tradeoffs |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **Agentic Workflows** | High | High | High | Neutral | MVP | Single-shot scripts (Rigid, no reasoning) |
| **Planning vs Reactive** | High | High | High | Neutral | v2 | ReAct loops (Slower, error-prone) |
| **Tool / Function Calling** | Medium | Low | Low | Neutral | MVP | Text-only parsing (Unreliable) |
| **Task Decomposition** | Medium | Medium | High | Neutral | MVP | Monolithic tasks (Fails often) |
| **Orchestration** | High | Low | Low | Neutral | MVP | Unmanaged execution (Chaos) |
| **State Machines** | Medium | Low | Low | Neutral | MVP | Unconstrained LLM (Hallucination risk) |
| **Workflow Graphs** | High | Low | Low | Neutral | v2 | Linear scripts (Cannot handle branching) |
| **Multi-agent Systems** | Very High | Very High | Very High | Neutral | Long-term | Single agent (Limited capability) |
| **Swarm Architectures** | Very High | Very High | Very High | Neutral | Avoid | Single orchestrator (More feasible locally) |
| **Autonomous vs Supervised** | Medium | Low | Low | High Risk | MVP | Open execution (Dangerous) |
| **Human-in-the-Loop (HITL)** | Low | Low | Increases | Neutral | MVP | Full autonomy (Risks data loss) |
| **Error Recovery / Retries** | Medium | Medium | Medium | Neutral | MVP | Fail immediately (Frustrating UX) |
| **Guardrails** | Medium | Low | Low | Neutral | MVP | No safety checks (Vulnerable) |
| **Self-checking / Reflection** | High | High | High | Neutral | v2 | Zero-shot execution (High error rate) |

**Agentic Workflows, State Machines, and Orchestration** Rather than allowing an LLM to freely loop using generic ReAct (Reason \+ Act) patterns—which frequently leads to fatal errors and infinite loops—deterministic state machines and workflow graphs restrict the model's choices based on the current execution state. Orchestration layers manage the routing between the LLM and its tools. For a local system where compute is constrained, state machines are critical for the MVP. They enforce reliability without requiring massive, computationally expensive models.  
**Planning vs Reactive Agents and Task Decomposition** Reactive agents execute the first viable step they identify. Planning agents (like Plan-and-Solve architectures) decompose a large objective into a sequence of steps before taking any action. Task decomposition is crucial for complex desktop automation, but planning requires higher cognitive overhead. Nexus should default to reactive state machines for MVP, migrating to autonomous planning for complex workflows in v2.  
**Tool Calling and Multi-Agent Swarms** Tool calling is the mechanism by which an LLM outputs structured data (usually JSON) to execute a predefined programmatic function. A swarm architecture utilises multiple specialised agents (e.g., a "research agent" and a "summarisation agent") working in tandem. While powerful, multi-agent swarms exponentially increase local VRAM requirements and latency. Nexus must rely on a single, highly capable orchestrator for its MVP, avoiding swarm architectures entirely until consumer hardware catches up.  
**Human-in-the-Loop (HITL), Guardrails, and Reflection** Supervised execution (HITL) pauses the workflow to request user approval before destructive actions. Guardrails prevent the LLM from executing malicious commands. Self-checking and reflection loops force the model to evaluate its own output before executing. Strict error recovery (retry strategies) and HITL are mandatory MVP features to prevent the agent from accidentally damaging the local filesystem.

### **4\) Voice AI Stack**

A voice-first agent requires a full-duplex, highly interruptible audio pipeline.

| Concept / Subsystem | Implementation Complexity | Runtime Cost | Latency Impact | Privacy Impact | Recommended Stage | Alternatives & Tradeoffs |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **Wake Word Detection** | Medium | Low | Low | Neutral | MVP | Push-to-talk (Less natural, breaks immersion) |
| **VAD** | Medium | Low | Low | Neutral | MVP | Continuous recording (Privacy risk, high compute) |
| **STT (Speech-to-Text)** | Medium | Medium | Medium | Low Risk | MVP | Cloud STT (Violates BYOK/privacy) |
| **TTS (Text-to-Speech)** | High | High | High | Neutral | MVP | OS Native TTS (Robotic, low quality) |
| **Streaming Inference** | High | Medium | Reduces | Neutral | v2 | Turn-based audio (High perceived latency) |
| **Barge-in Handling** | High | Low | Reduces | Neutral | v2 | Non-interruptible (Frustrating UX) |
| **Latency Budgets** | Medium | Low | None | Neutral | MVP | Ignoring latency (Unusable voice product) |
| **Speaker Adaptation** | High | Medium | Medium | Neutral | Long-term | Generic voice (Less personalized) |
| **Voice Persona Design** | Medium | Low | Low | Neutral | v2 | Default voices (Lacks branding/character) |
| **Prosody Control** | High | Medium | Low | Neutral | v2 | Flat inflection (Sounds robotic) |
| **Interruption Management** | High | Low | Reduces | Neutral | v2 | Ignoring user interruptions (Poor UX) |

**Wake Word Detection and Voice Activity Detection (VAD)** Wake word detection continuously monitors the microphone buffer for a specific phrase without transmitting data. The livekit-wakeword framework utilises an ONNX-based convolutional-attention classifier, achieving 86% recall with virtually zero false positives11. VAD determines when a user has started or stopped speaking. Both are critical MVP components for a hands-free experience.  
**Speech-to-Text (STT) and Text-to-Speech (TTS)** STT transcribes local audio to text, while TTS synthesises audio from text. For local TTS, Kokoro-82M offers state-of-the-art performance, utilising a pure-Rust phonemiser for extreme speed and low latency (less than 150ms time-to-first-audio)7. This avoids the severe overhead of larger codebook-based diffusion models while maintaining emotional prosody.  
**Streaming Inference, Barge-in Handling, and Interruption Management** Streaming inference synthesises audio in chunks as the text is generated, drastically reducing perceived latency. Barge-in handling allows the user to interrupt the agent mid-sentence, instantly halting the TTS generation and resetting the VAD state. This requires complex asynchronous threading in Rust to manage the audio buffers but is mandatory for a natural, conversational experience (v2). Latency budgets must be strictly enforced: total glass-to-glass latency (STT \+ LLM \+ TTS) must remain under 800ms.

### **5\) Local Computer Control**

To automate tasks, Nexus must perceive and manipulate the desktop environment natively.

| Concept / Subsystem | Implementation Complexity | Runtime Cost | Latency Impact | Privacy Impact | Recommended Stage | Alternatives & Tradeoffs |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **Browser Automation** | Medium | Medium | Low | Medium Risk | MVP | Requesting APIs directly (Often blocked by auth) |
| **Desktop Automation** | High | Low | Low | Medium Risk | MVP | PyAutoGUI (Brittle, breaks on resolution change) |
| **Computer-use Agents** | High | High | High | Medium Risk | v2 | API-only interaction (Cannot use legacy apps) |
| **RPA** | Medium | Medium | Low | Neutral | MVP | Manual macros (Unintelligent) |
| **OS-level Permissions** | High | Low | Low | High Risk | MVP | Root access (Massive security vulnerability) |
| **Sandboxing** | Very High | Low | None | High Risk | Long-term | Unrestricted access (Dangerous) |
| **Input Simulation** | Medium | Low | Low | Neutral | MVP | Native API calls only (Some apps block APIs) |
| **Accessibility APIs** | High | Low | Low | Neutral | MVP | Vision models (Slow, token-heavy, high VRAM) |
| **Browser DOM Control** | Medium | Low | Low | Medium Risk | MVP | Pixel-clicking (Extremely flaky) |
| **GUI Perception** | High | High | High | High Risk | v2 | Relying solely on structured data (Fails on custom UI) |
| **OCR when needed** | Medium | Medium | Medium | Neutral | v2 | Ignoring inaccessible text (Loss of context) |
| **Reliable Action Verif.** | High | Low | High | Neutral | v2 | Blind clicking (Agent gets lost easily) |
| **Safe Rollback** | Very High | High | High | Neutral | Long-term | Irreversible actions (High risk of data loss) |

**Accessibility APIs and Desktop Automation** Historically, desktop automation relied on computer vision models (like Qwen2.5-VL)21 to analyse screenshots and predict pixel coordinates. However, vision models are token-heavy, slow, and computationally expensive for local hardware. A vastly superior approach leverages native accessibility trees (UIA on Windows, AXUIElement on macOS, AT-SPI2 on Linux) via Rust libraries like xa11y3. This provides a deterministic, zero-latency JSON representation of the UI. This structured control is vital for a reliable MVP, ensuring Nexus knows exactly where buttons are without guessing pixels.  
**Browser Automation, DOM Control, and RPA** For web tasks, tools like Playwright interface directly with the browser's Document Object Model (DOM)24. This allows the agent to target elements by ID or role rather than brittle pixel coordinates, surviving dynamic layout shifts.  
**GUI Perception, OCR, and Input Simulation** When accessibility trees fail (e.g., custom rendering engines like games or legacy apps), Optical Character Recognition (OCR) and vision-language models provide a necessary fallback21. Input simulation utilises OS libraries to inject raw mouse and keyboard events.  
**Reliable Action Verification and Sandboxing** Verification ensures a clicked button actually triggered a state change. Sandboxing isolates the agent's actions to a virtual machine or restricted container. True sandboxing is incredibly difficult on a host OS and should be pushed to the long-term roadmap; strict permission boundaries and HITL must suffice for the MVP.

### **6\) Backend and Infra**

The architectural backbone must be ruthlessly efficient to leave maximum compute for the AI models.

| Concept / Subsystem | Implementation Complexity | Runtime Cost | Latency Impact | Privacy Impact | Recommended Stage | Alternatives & Tradeoffs |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **Local-first Architecture** | High | Low | Reduces | Neutral | MVP | Cloud-dependent (High latency, privacy risk) |
| **Rust Perf. Architecture** | High | Low | Reduces | Neutral | MVP | Python/Electron (High memory, slow execution) |
| **Async Pipelines** | Medium | Low | Low | Neutral | MVP | Synchronous blocking (UI freezes during generation) |
| **Event-driven Systems** | Medium | Low | Low | Neutral | MVP | Polling loops (Wastes CPU cycles) |
| **Queues** | Low | Low | Low | Neutral | MVP | Direct execution (Crashes under concurrent load) |
| **Caching** | Medium | Low | Reduces | Neutral | MVP | Recomputing (Slow and expensive) |
| **Local Databases** | Medium | Low | Low | Neutral | MVP | Client-Server DBs (Overkill, complex setup) |
| **Indexed Storage** | Low | Low | Low | Neutral | MVP | Flat files (Extremely slow search) |
| **Embedding Stores** | Medium | Low | Low | Neutral | MVP | API Vector DBs (Requires network access) |
| **Observability** | Medium | Low | Low | Neutral | MVP | Blind execution (Impossible to debug) |
| **Telemetry-free Design** | Low | Low | None | High Risk | MVP | Analytics engines (Violates core privacy ethos) |
| **Crash Recovery** | Medium | Low | Low | Neutral | v2 | Total failure (Data loss on panic) |
| **Modular Plugins** | High | Low | Low | Neutral | v2 | Monolithic binary (Hard to extend) |
| **Update Mechanisms** | Medium | Low | Low | Neutral | v2 | Manual downloads (Poor user retention) |
| **Offline Mode** | Low | Low | None | Neutral | MVP | Always-on DRM (Infuriating UX) |
| **Cross-platform Support** | High | Low | Low | Neutral | v2 | Single OS lock-in (Limits addressable market) |

**Local-First Architecture and Rust Performance Architecture** A local-first system implies that all logic executes on the edge device. Rust provides memory safety, C-like performance, and predictable latency (no garbage collection pauses). Given the heavy memory footprint of local LLMs, the orchestrator itself must consume negligible resources.  
**Async Pipelines, Event-Driven Systems, Queues, and Caching** Handling audio streaming, model inference, and UI rendering simultaneously requires an asynchronous, event-driven pipeline (e.g., using tokio in Rust). Task queues prevent the system from crashing under concurrent loads. Caching prevents redundant execution of identical queries.  
**Local Databases, Indexed Storage, and Embedding Stores** A combination of standard SQL (for state) and vector stores (for semantic memory) is required. Using in-process embedded databases like sqlite-vec prevents the user from needing to configure Docker containers or local server ports, ensuring seamless deployment5.  
**Observability, Telemetry-Free Design, and Crash Recovery** Observability ensures the system logs its failures, but a telemetry-free design guarantees those logs never leave the device, upholding the privacy promise. Crash recovery ensures state is saved iteratively. Modular plugins allow the community to extend Nexus without altering the core binary.

### **7\) Security and Privacy**

Nexus operates under a strict Bring-Your-Own-Key (BYOK) threat model, demanding absolute data sovereignty.

| Concept / Subsystem | Implementation Complexity | Runtime Cost | Latency Impact | Privacy Impact | Recommended Stage | Alternatives & Tradeoffs |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **Data Minimisation** | Low | Low | None | High Risk | MVP | Logging everything (Creates local privacy leak) |
| **BYOK Threat Model** | Medium | Low | None | High Risk | MVP | Hosted API keys (Company assumes liability) |
| **Permission Boundaries** | High | Low | Low | High Risk | MVP | Root access (Dangerous) |
| **Encryption at Rest** | Medium | Medium | Medium | High Risk | v2 | Unencrypted local DBs (Vulnerable to data theft) |
| **Local Secrets Handling** | Medium | Low | None | High Risk | MVP | Plaintext storage (Insecure) |
| **Sandboxing** | Very High | Low | Low | High Risk | Long-term | Full OS access (Malware risk) |
| **Consent Layers** | Low | Low | High | Neutral | MVP | Silent execution (Loss of user agency) |
| **Audit Logs** | Low | Low | Low | Neutral | MVP | Ephemeral state (No accountability) |
| **Privacy-preserving AI** | High | Low | Low | High Risk | MVP | Cloud processing (Data interception risk) |
| **Secure Browser Control** | Medium | Low | Low | High Risk | MVP | Sharing user cookies (Session hijacking risk) |
| **Prompt Injection Defense** | High | Low | Low | High Risk | v2 | Unfiltered inputs (Agent hijacking via malicious sites) |
| **Model Exfiltration Risks** | Low | Low | None | Neutral | N/A | DRM (Conflicts with open-source ethos) |
| **Local Memory Isolation** | High | Low | Low | High Risk | v2 | Shared memory spaces (Cross-contamination) |

**BYOK Threat Model, Local Secrets Handling, and Permission Boundaries** If the user enables optional cloud models (BYOK), API keys must be securely stored in the native OS keychain (e.g., macOS Keychain, Windows Credential Manager). Permission boundaries dictate exactly which directories the agent can read or write.  
**Privacy-Preserving AI & Regulatory Context (Pune, Maharashtra, India)** Nexus is designed with global privacy regulations in mind, specifically India's Digital Personal Data Protection (DPDP) Act 2023\. Under Section 3(2)(a) of the DPDP Act, personal data processed by an individual for any "personal or domestic purpose" is entirely exempt from the Act's obligations9. Because Nexus runs 100% locally on the user's hardware and acts strictly as a domestic/personal tool without transmitting telemetry, the software provider is not legally classified as a "Data Fiduciary"27. This local-only isolation removes the requirement for complex Consent Managers and Data Protection Officers, offering a massive architectural and legal advantage over cloud competitors.  
**Encryption at Rest, Prompt Injection Defense, and Secure Browser Control** Encryption prevents malware from scraping the agent's memory database. Local memory isolation prevents the agent from reading browser cookies belonging to secure sessions (banking, etc.). Because the model is local, prompt injection is a severe risk. If the agent reads a malicious webpage that instructs it to format the hard drive, a naive system will comply. Robust parsing and semantic sandboxing are required to neutralise these threats.

### **8\) Product Experience and Personalisation**

The user interface must adapt dynamically to the user's technical proficiency and workflow preferences.

| Concept / Subsystem | Implementation Complexity | Runtime Cost | Latency Impact | Privacy Impact | Recommended Stage | Alternatives & Tradeoffs |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **Persona Systems** | Medium | Low | Low | Neutral | MVP | Generic assistant (Lacks engagement) |
| **Adaptive Interfaces** | High | Medium | Low | Neutral | v2 | Static UI (Cluttered for casual users) |
| **Theme Engines** | Low | Low | None | Neutral | v2 | Hardcoded colours (Poor accessibility) |
| **Avatar-based UI** | High | High | High | Neutral | Long-term | Minimalist UI (Less engaging but faster) |
| **User Preference Model.** | High | Low | Low | High Risk | v2 | Manual configuration settings (High friction) |
| **Simple UI vs Sci-Fi** | Medium | Low | None | Neutral | v2 | One-size-fits-all UI (Poor UX) |
| **Voice-only Workflows** | High | Low | Low | Neutral | MVP | Chat UI (Standard, requires visual focus) |
| **Accessibility** | Medium | Low | None | Neutral | MVP | Ignoring visually impaired users (Poor design) |
| **Custom Characters** | High | Low | Low | Neutral | Long-term | Single voice/persona (Rigid) |
| **Dynamic Style Adapt.** | Medium | Low | Low | Neutral | v2 | Static prompt generation (Repetitive) |

**Adaptive Interfaces, Theme Engines, Simple UI vs Sci-Fi Mode** A dynamic user interface provides a minimalist "command bar" (Simple UI) for standard users, and a deeply verbose terminal-style overlay displaying internal states, JSON payloads, and confidence scores (Sci-Fi Mode) for developers.  
**Voice-Only Workflows and Accessibility** Nexus must be fully operable without a screen, enabling visually impaired users or hands-free workers to navigate their operating system entirely via natural language.  
**Persona Systems, User Preference Modelling, Custom Characters** The system dynamically adjusts its tone, brevity, and execution speed based on modelled user preferences. Avatar-based UIs and visual character rendering require intensive graphics processing and are relegated to the long-term roadmap to preserve computational overhead for the underlying intelligence.

### **9\) Evaluation and Quality**

Continuous evaluation is critical for ensuring non-destructive behaviour and system reliability.

| Concept / Subsystem | Implementation Complexity | Runtime Cost | Latency Impact | Privacy Impact | Recommended Stage | Alternatives & Tradeoffs |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **Latency Measurement** | Low | Low | None | Neutral | MVP | No measurement (Blind profiling) |
| **Task Success Rate** | High | High | None | Neutral | v2 | Manual QA (Unscalable, misses edge cases) |
| **Hallucination Rate** | High | High | None | Neutral | v2 | User reporting (High friction, delayed fixes) |
| **Automation Reliability** | High | Medium | None | Neutral | MVP | Brittle scripts (Constant breakage) |
| **Tool Exec. Accuracy** | Medium | Low | None | Neutral | MVP | Unvalidated JSON (Causes pipeline crashes) |
| **Cost per Task** | Low | Low | None | Neutral | MVP | Ignoring compute budgets (I/O bottlenecks) |
| **Token Efficiency** | Medium | Low | None | Neutral | MVP | Verbose prompting (Slower generation) |
| **Benchmark Design** | High | Low | None | Neutral | v2 | Generic LLM benchmarks (Irrelevant to OS agents) |
| **Regression Testing** | Medium | High | None | Neutral | MVP | Pushing untested code (Dangerous for local OS) |
| **Eval Harnesses** | High | High | None | Neutral | v2 | Manual testing (Slow iteration cycles) |
| **Red-teaming** | High | Medium | None | Neutral | v2 | Assuming the model is safe (Vulnerable to injection) |
| **Failure Analysis** | Medium | Low | None | Neutral | MVP | Silent failures (Frustrating user experience) |

**Latency Measurement, Token Efficiency, and Cost Per Task** Inference speed is tracked precisely, targeting \<300ms Time-To-First-Token (TTFT) for voice interactions. Token efficiency measures how well the prompt engineering minimises context overhead, directly impacting compute "cost" (battery life and thermal load).  
**Task Success Rate, Hallucination Rate, Automation Reliability** Success metrics evaluate whether the agent successfully manipulated the DOM or OS state as intended without generating hallucinatory tool calls. Tool execution accuracy measures the syntactical correctness of the LLM's JSON outputs.  
**Benchmark Design, Eval Harnesses, Red-Teaming, Regression Testing** Custom evaluation harnesses programmatically test the agent against simulated environments (e.g., mock websites and fake desktop apps) before any code is merged. Red-teaming involves adversarial attacks to verify the agent will not execute destructive commands via prompt injection.

### **10\) Competitive Differentiation (The Moats)**

To separate Nexus from cloud wrappers and basic local chatbots, the system leverages the following deep moats:

1. **Deterministic Desktop Control**: Utilising accessibility trees (xa11y) instead of vision models ensures 100% accurate GUI manipulation at near-zero inference cost3.  
2. **Embedded GraphRAG Memory**: Using sqlite-vec \+ GraphQLite to create a single-binary, fully offline topological map of the user's digital life without requiring server-based databases5.  
3. **Local Latency Engineering**: Achieving sub-500ms voice response times through the combination of Rust, livekit-wakeword, speculative decoding via llama.cpp, and Kokoro-82M TTS7.  
4. **Absolute Legal Privacy**: Under India's DPDP Act, running a completely offline tool for domestic processing entirely removes the regulatory burden of being a Data Fiduciary9.  
5. **Self-Healing Workflows**: Implementing deterministic reflection loops that allow the agent to correct its own DOM selectors if a website updates its layout24.

## **C. Architecture Diagram (Text Form)**

\[ User Input Modalities \] │ │ (Microphone) (Keyboard/GUI) │ │ \[ Wake Word / VAD \] │ (livekit-wakeword) │ │ │ \[ Local STT Engine \] │ (Whisper.cpp/FluidAudio) │ │ │ ▼ ▼ \+---------------------------------------------------+  
| NEXUS CORE ORCHESTRATOR | | (Rust Async Runtime) | | \[ BYOK Local Secrets Manager \] | \+---------------------------------------------------+ │ │ │ │ ▼ ▼ ▼ ▼ \[ State Mach. \] \[ LLM Engine \] \[ Memory \] \[ Tool Router \] (Workflows) (llama.cpp \+ (sqlite- (Access APIs, Speculative vec \+ Playwright) Decoding) GraphQL) │ │ │ │ │ \+-----------+------------+-----------+ │ │ ▼ ▼ \[ TTS Generation \] \---\> (Action Verification & (Kokoro-82M native) Human-in-the-Loop) │ │ ▼ ▼ \[ System Outputs \] \---\> (Audio Out, UI Update, OS Automation execution)

## **D. MVP, v2, and Long-Term Roadmap**

### **Phase 1: MVP (Months 1-3)**

*Focus: Speed, core local functionality, and safety.*

* **Engine**: Rust backend orchestrator, llama.cpp wrapper for core LLM inference.  
* **Voice**: livekit-wakeword for activation; Kokoro-82M for fast TTS generation.  
* **Control**: Playwright for robust browser automation; xa11y for basic deterministic OS control.  
* **Memory**: Flat SQLite logging and simple vector retrieval (sqlite-vec) for recent context.  
* **Safety**: Strict Human-in-the-Loop (HITL) for all destructive/state-changing OS actions.

### **Phase 2: v2 (Months 4-8)**

*Focus: Advanced cognition, automation reliability, and dynamic UI.*

* **Memory**: Implementation of GraphQLite for local GraphRAG and semantic relationship mapping.  
* **Inference**: Speculative decoding using draft models for massive TTFT improvements16.  
* **Automation**: Fallback to vision-language models (e.g., Qwen2.5-VL) when accessibility trees fail21.  
* **Voice**: Full streaming TTS inference and audio barge-in/interruption handling.  
* **UX**: "Sci-Fi" developer terminal overlay vs. simple command bar.

### **Phase 3: Long-Term (Months 9+)**

*Focus: Absolute autonomy and personalisation.*

* **Personalisation**: Local LoRA / QLoRA fine-tuning based on synthetic data generated from user habits.  
* **Architecture**: Multi-agent local orchestration for complex task breakdown (e.g., separate research and execution agents).  
* **Visuals**: Avatar-based UI and prosody-driven animation.  
* **Security**: Full OS-level sandboxing and rollback states.

## **E. Recommended Stack for a Local-First AI Agent**

1. **Core Application Backend**: Rust (for memory safety, ultra-low latency, and minimal overhead).  
2. **LLM Inference**: llama.cpp (C++ with Rust bindings) for unparalleled local hardware support across Apple Metal, CUDA, and ROCm18. It outperforms vLLM for single-user Time-To-First-Token.  
3. **Voice Activity & Wake Word**: livekit-wakeword (ONNX-based, highest open-source accuracy, 86% recall)11.  
4. **Text-to-Speech (TTS)**: Kokoro-82M combined with pure-Rust phonemisers (e.g., any-tts crate) for real-time edge synthesis under 150ms7.  
5. **Browser Automation**: Playwright via Node/Python wrappers communicated over local IPC25.  
6. **Desktop Automation**: xa11y (Rust library) for accessing UIA, AXUIElement, and AT-SPI2 accessibility trees deterministically3.  
7. **Local Memory/Database**: SQLite with sqlite-vec (for zero-dependency vector search) and GraphQLite (for localised GraphRAG)5.  
8. **Vision Fallback**: Qwen2.5-VL running locally for OCR and spatial reasoning when OS accessibility trees are unavailable21.

## **F. Risks, Failure Modes, and Tradeoffs**

**Thermal Throttling and Hardware Fragmentation** *Risk*: Local AI is extremely resource-intensive. Running a 7B LLM, a TTS model, and a continuous wake-word listener will stress consumer hardware, leading to thermal throttling and rapid battery drain. *Tradeoff*: Nexus must aggressively swap models out of VRAM when idle and use highly quantised weights (e.g., GGUF Q4\_K\_M)19, sacrificing slight reasoning accuracy for thermal stability.  
**The "Hallucinated Click"***Risk*: The agent misinterprets the accessibility tree and clicks a destructive element (e.g., "Delete Repository").*Tradeoff*: Autonomous execution must be restricted. The implementation of strict bounding boxes, deterministic state machines, and a mandatory confirmation layer (HITL) for high-risk applications slows down execution but prevents catastrophic user failure.  
**Cognitive Overhead of GraphRAG***Risk*: Creating a knowledge graph from local files using LLMs is incredibly slow and token-heavy.*Tradeoff*: GraphRAG index building must be relegated to asynchronous background processes that only run when the machine is plugged into power and idle.

## **G. What *Not* to Build First**

To ensure survival and momentum, a small team must explicitly avoid building the following for the MVP:

1. **Multi-Agent Swarms**: Orchestrating multiple LLMs simultaneously will crush a standard laptop's VRAM. A single capable orchestrator is required first.  
2. **Cloud Synchronisation**: Building a cloud sync engine violates the local-first ethos and introduces massive security, regulatory (DPDP Act), and infrastructure complexities.  
3. **Vision-First Automation**: Relying on models like OmniParser or raw vision for screen clicking is too slow for real-time use. Stick to xa11y and Playwright for MVP.  
4. **Avatar and Sci-Fi UIs**: 3D character rendering drains GPU compute needed for actual LLM inference.  
5. **Custom Synthetic Data Pipelines for SFT**: Do not train custom models initially. Rely on high-quality open weights (Llama 3, Mistral, Qwen) and system prompting.

## **H. Final Prioritised Technology Stack Recommendation**

To architect Nexus correctly, prioritise mastering these concepts and technologies, ranked by critical impact:

1. **Rust Async/Multithreading**: The foundation of the low-latency, non-blocking core loop.  
2. **llama.cpp internals & GGUF formats**: Understanding local quantisation and hardware acceleration (Metal/CUDA)19.  
3. **Speculative Decoding & KV Caching**: Crucial for hitting real-time conversational speeds locally via draft models15.  
4. **Accessibility Tree APIs (xa11y)**: The secret to deterministic, fast, token-efficient OS automation3.  
5. **Browser DOM & Playwright**: Essential for executing web-based tasks resiliently24.  
6. **Embedded Vector/Graph Search (sqlite-vec, GraphQLite)**: For building a zero-dependency local memory engine5.  
7. **ONNX Runtime Optimisation**: Required for running fast, lightweight models like wake-words locally.  
8. **Kokoro-82M Architecture**: Implementing lightweight, real-time TTS without heavy codebooks8.  
9. **livekit-wakeword / VAD**: Audio buffering and streaming signal processing11.  
10. **State Machine Orchestration**: Architecting constrained agent workflows rather than open-ended loops.  
11. **RAG / Context Engineering**: Injecting localised OS state into LLM prompts efficiently.  
12. **Tool/Function Calling via JSON**: Bridging the gap between LLM output and Rust execution logic.  
13. **Local Inter-Process Communication (IPC)**: Connecting the Rust core to browser processes securely.  
14. **Qwen2.5-VL / Spatial Reasoning**: Using local vision models as a fallback for non-standard GUIs21.  
15. **Streaming Audio Pipelines (PortAudio)**: Handling real-time audio input/output and barge-in logic.  
16. **India DPDP Act 2023 (Section 3\)**: Understanding the legal moat provided by the "personal or domestic purpose" exemption9.  
17. **Sandboxing / OS Permissions**: Securing the agent's filesystem and network access boundaries.  
18. **Continuous Evaluation (Evals)**: Building programmatic harnesses to test UI interaction success rates.  
19. **GraphRAG Algorithms**: Understanding PageRank and community detection for semantic relationship mapping.  
20. **LoRA / QLoRA**: For the eventual long-term goal of personalising the model weights locally to the user.

#### **Works cited**

1. Iris AI Reviews & Ratings 2026 | Gartner Peer Insights, [https://www.gartner.com/reviews/product/iris-ai-952936189](https://www.gartner.com/reviews/product/iris-ai-952936189)  
2. Docusign Agreement Manager: Unlocking Agreement Intelligence with Iris AI \- Fluidlabs, [https://fluidlabs.com/resources/docusign-navigator-agreement-intelligence-iris-ai](https://fluidlabs.com/resources/docusign-navigator-agreement-intelligence-iris-ai)  
3. Show HN: Xa11y – cross-platform desktop automation via accessibility trees | Hacker News, [https://news.ycombinator.com/item?id=48446496](https://news.ycombinator.com/item?id=48446496)  
4. Show HN: Agent-desktop – Native desktop automation CLI for AI agents | Hacker News, [https://news.ycombinator.com/item?id=47982708](https://news.ycombinator.com/item?id=47982708)  
5. GraphQLite \- Embedded graph database for building GraphRAG with SQLite \- Reddit, [https://www.reddit.com/r/LocalLLaMA/comments/1q0si1a/graphqlite\_embedded\_graph\_database\_for\_building/](https://www.reddit.com/r/LocalLLaMA/comments/1q0si1a/graphqlite_embedded_graph_database_for_building/)  
6. Embedded Vector Databases for Go in 2026: chromem-go vs sqlite-vec vs Bleve vs LanceDB \- Shaharia Azam, [https://shaharia.com/blog/choosing-embeddable-vector-database-go-application/](https://shaharia.com/blog/choosing-embeddable-vector-database-go-application/)  
7. Best Text-to-Speech TTS Models in 2026: A Benchmark-Based Comparison \- MarkTechPost, [https://www.marktechpost.com/2026/05/30/best-text-to-speech-tts-models-in-2026-a-benchmark-based-comparison/](https://www.marktechpost.com/2026/05/30/best-text-to-speech-tts-models-in-2026-a-benchmark-based-comparison/)  
8. Any-TTS is an open-source, high-quality text-to-speech (TTS) toolkit for generating natural-sounding speech from text—featuring easy setup, flexible voices/languages, and developer-friendly APIs for apps, bots, and automation. · GitHub, [https://github.com/TM9657/any-tts](https://github.com/TM9657/any-tts)  
9. Digital Personal Data Protection Act, 2023 DPDPA SECTION 3 WITH INTERPRETATION, [https://www.dpdpa.com/dpdpa2023/chapter-1/section3.html](https://www.dpdpa.com/dpdpa2023/chapter-1/section3.html)  
10. Decoding the Digital Personal Data Protection Act, 2023 \- KPMG International, [https://assets.kpmg.com/content/dam/kpmgsites/in/pdf/2023/08/decoding-the-digital-personal-data-protection-act-2023.pdf](https://assets.kpmg.com/content/dam/kpmgsites/in/pdf/2023/08/decoding-the-digital-personal-data-protection-act-2023.pdf)  
11. Open-source wake word training in a single command \- LiveKit, [https://livekit.com/blog/livekit-wakeword](https://livekit.com/blog/livekit-wakeword)  
12. GitHub \- livekit/livekit-wakeword: An open-source wake word library for creating voice-enabled applications., [https://github.com/livekit/livekit-wakeword](https://github.com/livekit/livekit-wakeword)  
13. Which vector database do we like for local/selfhosted? : r/Rag \- Reddit, [https://www.reddit.com/r/Rag/comments/1r3y4ys/which\_vector\_database\_do\_we\_like\_for/](https://www.reddit.com/r/Rag/comments/1r3y4ys/which_vector_database_do_we_like_for/)  
14. GraphRAG: Hierarchical Approach to Retrieval-Augmented Generation \- LanceDB, [https://www.lancedb.com/blog/graphrag-hierarchical-approach-to-retrieval-augmented-generation](https://www.lancedb.com/blog/graphrag-hierarchical-approach-to-retrieval-augmented-generation)  
15. LM Studio 0.3.10: Speculative Decoding, [https://lmstudio.ai/blog/lmstudio-v0.3.10](https://lmstudio.ai/blog/lmstudio-v0.3.10)  
16. Model Configuration \- LocalAI, [https://localai.io/advanced/model-configuration/index.print](https://localai.io/advanced/model-configuration/index.print)  
17. How to Setup a Local Coding Agent on macOS \- Kyle Howells, [https://ikyle.me/blog/2026/how-to-setup-a-local-coding-agent-on-macos](https://ikyle.me/blog/2026/how-to-setup-a-local-coding-agent-on-macos)  
18. vLLM, Ollama, LM Studio, llama.cpp: Choosing the best LLM inference engine in 2026 \[ Updated \] \- Bizon-tech, [https://bizon-tech.com/blog/best-llm-inference-engines](https://bizon-tech.com/blog/best-llm-inference-engines)  
19. vLLM vs llama.cpp vs Ollama: Benchmarks & Latency (2026) \- Decodes Future, [https://www.decodesfuture.com/articles/vllm-vs-llama-cpp-vs-ollama-benchmark-guide](https://www.decodesfuture.com/articles/vllm-vs-llama-cpp-vs-ollama-benchmark-guide)  
20. The Best Open-Source Text-to-Speech Models in 2026 \- BentoML, [https://www.bentoml.com/blog/exploring-the-world-of-open-source-text-to-speech-models](https://www.bentoml.com/blog/exploring-the-world-of-open-source-text-to-speech-models)  
21. How to Use Qwen2.5-VL Locally \- DataCamp, [https://www.datacamp.com/tutorial/use-qwen2-5-vl-locally](https://www.datacamp.com/tutorial/use-qwen2-5-vl-locally)  
22. shaneholloman/qwen2.5-vl \- GitHub, [https://github.com/shaneholloman/qwen2.5-vl](https://github.com/shaneholloman/qwen2.5-vl)  
23. Cross-platform desktop automation through accessibility APIs \- crowecawcaw blog, [https://crowecawcaw.github.io/general/2026/05/30/accessibility-for-computer-use.html](https://crowecawcaw.github.io/general/2026/05/30/accessibility-for-computer-use.html)  
24. Computer Use Agents | AI Engineering | AlgoMaster.io, [https://algomaster.io/learn/ai-engineering/computer-use-agents](https://algomaster.io/learn/ai-engineering/computer-use-agents)  
25. Open-source browser automation for local AI agents (Playwright? Selenium?) \- Reddit, [https://www.reddit.com/r/AI\_Agents/comments/1ri0iwx/opensource\_browser\_automation\_for\_local\_ai\_agents/](https://www.reddit.com/r/AI_Agents/comments/1ri0iwx/opensource_browser_automation_for_local_ai_agents/)  
26. Building Computer Use Agents (CUA) | ai-agents-for-beginners \- Microsoft Open Source, [https://microsoft.github.io/ai-agents-for-beginners/15-browser-use/](https://microsoft.github.io/ai-agents-for-beginners/15-browser-use/)  
27. Digital Personal Data Protection Act India: Compliance Guide 2026 \- Atlas Systems, [https://www.atlassystems.com/blog/digital-personal-data-protection-act-india](https://www.atlassystems.com/blog/digital-personal-data-protection-act-india)  
28. Speculative Decoding | Unsloth Documentation, [https://unsloth.ai/docs/basics/inference-and-deployment/saving-to-gguf/speculative-decoding](https://unsloth.ai/docs/basics/inference-and-deployment/saving-to-gguf/speculative-decoding)