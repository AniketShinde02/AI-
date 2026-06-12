import { useState, useCallback, useRef } from 'react';
import { logger } from "@/lib/logger";
import { traceStore } from "@/lib/traceStore";

interface UseGeminiLiveProps {
  onTranscript?: (text: string) => void;
  onAgentMessage?: (text: string, isParagraphEnd: boolean) => void;
  onToolCall?: (toolCall: any) => Promise<any>;
}

export function useGeminiLive({ onTranscript, onAgentMessage, onToolCall }: UseGeminiLiveProps = {}) {
  const [isConnected, setIsConnected] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [micCaptured, setMicCaptured] = useState(false);
  const recognitionRef = useRef<any>(null);
  
  const socketRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const micWorkletRef = useRef<AudioWorkletNode | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const workletLoadedRef = useRef<Promise<void> | null>(null);
  
  const activeAudioNodesRef = useRef<AudioBufferSourceNode[]>([]);
  const nextStartTimeRef = useRef<number>(0);
  const analyserRef = useRef<AnalyserNode | null>(null);
  
  // Parser state for separating reasoning
  const isThinkingRef = useRef<boolean>(false);
  const textBufferRef = useRef<string>("");
  const hasEmittedThinkingRef = useRef<boolean>(false);
  
  const apiKeyRef = useRef<string | null>(null);

  const setApiKey = useCallback((key: string) => {
    apiKeyRef.current = key;
  }, []);

  const disconnect = useCallback(() => {
    logger.info("[Gemini Live] Disconnecting...");
    setIsConnected(false);
    setIsListening(false);
    
    if (socketRef.current) {
      socketRef.current.onclose = null;
      socketRef.current.close(1000, "Intentional disconnect");
      socketRef.current = null;
    }

    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach(t => t.stop());
      micStreamRef.current = null;
    }
    
    setMicCaptured(false);

    if (audioContextRef.current?.state !== 'closed') {
      try { audioContextRef.current?.close(); } catch {}
    }
    
    activeAudioNodesRef.current.forEach(node => {
      try { node.stop(); node.disconnect(); } catch {}
    });
    activeAudioNodesRef.current = [];
    nextStartTimeRef.current = 0;
    
    isThinkingRef.current = false;
    textBufferRef.current = "";
    hasEmittedThinkingRef.current = false;
    
    micWorkletRef.current?.disconnect();
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch {}
    }
  }, []);

  const connect = useCallback(async () => {
    if (!apiKeyRef.current) {
      logger.error("[Gemini Live] Missing API Key");
      return;
    }

    const url = `wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key=${apiKeyRef.current}`;
    const ws = new WebSocket(url);
    socketRef.current = ws;

    ws.onopen = async () => {
      logger.info("[Gemini Live] ✅ Connected to WebRTC Socket");
      setIsConnected(true);

      let memoryText = "";
      try {
        const memRes = await fetch("http://localhost:8000/memory");
        if (memRes.ok) {
          const memory = await memRes.json();
          memoryText = `\n\n**USER PREFERENCES (LONG-TERM MEMORY):**\n${JSON.stringify(memory, null, 2)}\n\nIMPORTANT: Use these preferences to guide your behavior. Update them if the user asks you to remember something new.`;
        }
      } catch (e) {
        console.warn("Failed to load memory:", e);
      }

      const setupMsg = {
        setup: {
          model: 'models/gemini-2.5-flash-native-audio-preview-12-2025',
          systemInstruction: {
            parts: [{ text: `You are Nexus, a highly intelligent, fast, and natural human-like chief-of-staff.
Your voice must sound like a real person—conversational, confident, and slightly casual.

**1. Tone & Vocabulary (CRITICAL):**
- Speak using natural Indian English idioms. 
- Use casual human acknowledgments: "Sure, tell me what's up", "Got it", "Give me a second", "Let me check that".
- NEVER say "I am currently analyzing", "I am prioritizing", "I am structuring", or "How may I assist you".
- Never narrate your internal processes or chain-of-thought.

**2. Multi-Lingual Code-Switching:**
- You natively understand English, Hindi, and Marathi.
- If the user speaks Hindi or Marathi, match their language naturally. 
- Use Hinglish code-switching seamlessly. Do not sound like a translated textbook.

**3. Brevity (Voice-First):**
- Simple questions: 1 sentence.
- Medium questions: 2-4 sentences maximum.
- Deep research: Only give long answers if explicitly asked. 
- Write exactly how a human speaks aloud. No bullet points, no markdown, no emojis in your spoken output.

**4. Separation of Reasoning (CRITICAL):**
- If you must process thoughts, plan, or analyze instructions before speaking, you MUST wrap that internal reasoning entirely within <think>...</think> XML tags.
- NEVER output reasoning or chain-of-thought as plain text. Only the final spoken response should be outside the <think> tags.` + memoryText }]
          },
          generationConfig: {
            speechConfig: {
              voiceConfig: {
                prebuiltVoiceConfig: {
                  voiceName: "Puck"
                }
              }
            }
          },
          tools: [
            // Dummy tool schema to test routing
            {
              functionDeclarations: [
                {
                  name: "search_web",
                  description: "Search the web for information.",
                  parameters: {
                    type: "OBJECT",
                    properties: { query: { type: "STRING" } },
                    required: ["query"]
                  }
                },
                {
                  name: "run_command",
                  description: "Execute a shell command on the local Windows machine. Do NOT use this for destructive actions.",
                  parameters: {
                    type: "OBJECT",
                    properties: { command: { type: "STRING" } },
                    required: ["command"]
                  }
                },
                {
                  name: "open_application",
                  description: "Open a Windows application or file.",
                  parameters: {
                    type: "OBJECT",
                    properties: { app_name: { type: "STRING" } },
                    required: ["app_name"]
                  }
                },
                {
                  name: "create_task",
                  description: "Create a new task or todo item for the user.",
                  parameters: {
                    type: "OBJECT",
                    properties: {
                      title: { type: "STRING", description: "The task title or description." },
                      priority: { type: "STRING", description: "high, medium, or low" },
                      due_date: { type: "STRING", description: "Optional due date (e.g. 'tomorrow')." }
                    },
                    required: ["title"]
                  }
                },
                {
                  name: "create_note",
                  description: "Save a personal note, memo, or piece of information.",
                  parameters: {
                    type: "OBJECT",
                    properties: {
                      title: { type: "STRING", description: "A short descriptive title for the note." },
                      content: { type: "STRING", description: "The full text content of the note." }
                    },
                    required: ["title", "content"]
                  }
                },
                {
                  name: "update_preferences",
                  description: "Save important facts or preferences about the user to long-term memory.",
                  parameters: {
                    type: "OBJECT",
                    properties: {
                      preferences: { type: "OBJECT", description: "Key-value pairs of user preferences or facts." }
                    },
                    required: ["preferences"]
                  }
                },
                {
                  name: "get_user_memory",
                  description: "Retrieve all saved long-term user preferences.",
                  parameters: {
                    type: "OBJECT",
                    properties: {}
                  }
                },
                {
                  name: "delete_user_preference",
                  description: "Delete a saved user preference.",
                  parameters: {
                    type: "OBJECT",
                    properties: {
                      category: { type: "STRING" },
                      key: { type: "STRING" }
                    },
                    required: ["category", "key"]
                  }
                },
                {
                  name: "read_file",
                  description: "Read the text content of a file.",
                  parameters: {
                    type: "OBJECT",
                    properties: {
                      file_path: { type: "STRING", description: "The absolute path to the file." }
                    },
                    required: ["file_path"]
                  }
                },
                {
                  name: "write_file",
                  description: "Write text to a file (creates or overwrites).",
                  parameters: {
                    type: "OBJECT",
                    properties: {
                      file_name: { type: "STRING", description: "File name (e.g. notes.txt) or full path." },
                      content: { type: "STRING", description: "The text content to write." }
                    },
                    required: ["file_name", "content"]
                  }
                },
                {
                  name: "read_directory",
                  description: "Scan a directory (folder) to see what files are inside.",
                  parameters: {
                    type: "OBJECT",
                    properties: {
                      directory_path: { type: "STRING", description: "The folder path (e.g. 'Desktop', 'Documents', 'C:/Projects')." }
                    },
                    required: ["directory_path"]
                  }
                },
                {
                  name: "get_weather",
                  description: "Get current weather conditions for a city.",
                  parameters: {
                    type: "OBJECT",
                    properties: {
                      city: { type: "STRING", description: "The name of the city, e.g. 'London', 'Mumbai', 'New York'" }
                    },
                    required: ["city"]
                  }
                },
                {
                  name: "ingest_codebase",
                  description: "Scan a directory and build a vector database for semantic search. Do this before answering complex codebase questions.",
                  parameters: {
                    type: "OBJECT",
                    properties: {
                      dir_path: { type: "STRING", description: "The absolute path to the project directory." }
                    },
                    required: ["dir_path"]
                  }
                },
                {
                  name: "consult_oracle",
                  description: "Query the RAG (Retrieval-Augmented Generation) memory for answers about the codebase. Ensure ingest_codebase was called first.",
                  parameters: {
                    type: "OBJECT",
                    properties: {
                      query: { type: "STRING", description: "A detailed natural language question about the code." }
                    },
                    required: ["query"]
                  }
                }
              ]
            }
          ]
        }
      };
      ws.send(JSON.stringify(setupMsg));
    };

    ws.onmessage = async (event) => {
      try {
        let msgStr = event.data;
        if (event.data instanceof Blob) {
            msgStr = await event.data.text();
        }
        const msg = JSON.parse(msgStr);
        
        if (msg.serverContent) {
          const content = msg.serverContent;
          
          if (content.interrupted) {
            logger.info("[Gemini Live] 💥 Interrupted");
            activeAudioNodesRef.current.forEach(node => {
              try { node.stop(); node.disconnect(); } catch {}
            });
            activeAudioNodesRef.current = [];
            nextStartTimeRef.current = 0;
            setIsSpeaking(false);
          }

          if (content.modelTurn) {
            const parts = content.modelTurn.parts;
            for (const part of parts) {
              if (part.inlineData && part.inlineData.mimeType.startsWith("audio/pcm")) {
                const binaryString = window.atob(part.inlineData.data);
                const bytes = new Uint8Array(binaryString.length);
                for (let i = 0; i < binaryString.length; i++) {
                  bytes[i] = binaryString.charCodeAt(i);
                }
                const int16Array = new Int16Array(bytes.buffer);
                
                const float32Data = new Float32Array(int16Array.length);
                for (let i = 0; i < int16Array.length; i++) {
                  float32Data[i] = int16Array[i] / 32768.0;
                }

                const ctx = audioContextRef.current;
                if (ctx && analyserRef.current) {
                  const buffer = ctx.createBuffer(1, float32Data.length, 24000);
                  buffer.getChannelData(0).set(float32Data);

                  const source = ctx.createBufferSource();
                  source.buffer = buffer;

                  source.connect(analyserRef.current);
                  analyserRef.current.connect(ctx.destination);

                  const currentTime = ctx.currentTime;
                  if (nextStartTimeRef.current < currentTime) {
                      nextStartTimeRef.current = currentTime + 0.02; 
                  }

                  source.start(nextStartTimeRef.current);
                  nextStartTimeRef.current += buffer.duration;

                  activeAudioNodesRef.current.push(source);
                  
                  if (!isSpeaking) {
                    setIsSpeaking(true);
                    traceStore.addTrace('🔊', 'Generating Voice');
                  }
                  
                  source.onended = () => {
                    activeAudioNodesRef.current = activeAudioNodesRef.current.filter((n) => n !== source);
                    if (activeAudioNodesRef.current.length === 0) {
                      setIsSpeaking(false);
                    }
                  };
                }
              } else if (part.text && onAgentMessage) {
                // Stream text chunk through the reasoning parser
                textBufferRef.current += part.text;
                let buffer = textBufferRef.current;
                let emitText = "";

                while (buffer.length > 0) {
                  if (isThinkingRef.current) {
                    const endIdx = buffer.indexOf("</think>");
                    if (endIdx !== -1) {
                      const thinkContent = buffer.substring(0, endIdx);
                      if (thinkContent) {
                        logger.info("[Gemini Reasoning]", thinkContent);
                        if (!hasEmittedThinkingRef.current) {
                          traceStore.addTrace('🧠', 'Thinking');
                          hasEmittedThinkingRef.current = true;
                        }
                      }
                      isThinkingRef.current = false;
                      buffer = buffer.substring(endIdx + 8);
                    } else {
                      const lastLt = buffer.lastIndexOf("<");
                      if (lastLt !== -1 && "</think>".startsWith(buffer.substring(lastLt))) {
                        const safeLog = buffer.substring(0, lastLt);
                        if (safeLog) logger.info("[Gemini Reasoning]", safeLog);
                        buffer = buffer.substring(lastLt);
                        break;
                      } else {
                        logger.info("[Gemini Reasoning]", buffer);
                        buffer = "";
                      }
                    }
                  } else {
                    const startIdx = buffer.indexOf("<think>");
                    if (startIdx !== -1) {
                      emitText += buffer.substring(0, startIdx);
                      isThinkingRef.current = true;
                      buffer = buffer.substring(startIdx + 7);
                    } else {
                      const lastLt = buffer.lastIndexOf("<");
                      if (lastLt !== -1 && "<think>".startsWith(buffer.substring(lastLt))) {
                        emitText += buffer.substring(0, lastLt);
                        buffer = buffer.substring(lastLt);
                        break;
                      } else {
                        emitText += buffer;
                        buffer = "";
                      }
                    }
                  }
                }

                textBufferRef.current = buffer;

                if (emitText) {
                  onAgentMessage(emitText, false);
                }
              }
            }
          }

          if (content.turnComplete) {
            logger.info("[Gemini Live] 🏁 Turn Complete");
            traceStore.addTrace('✅', 'Complete');
            hasEmittedThinkingRef.current = false;
            if (onAgentMessage) onAgentMessage("", true);
            // No need to send stream_end to worklet; onended handles the end of speech
          }
        } else if (msg.toolCall) {
          logger.info("[Gemini Live] 🛠️ Tool Call Request:", msg.toolCall);
          
          msg.toolCall.functionCalls.forEach((call: any) => {
            if (call.name === "search_web") traceStore.addTrace('🔍', 'Searching Web');
            else if (call.name === "consultOracle" || call.name === "run_rag") traceStore.addTrace('📚', 'Consulting Oracle');
            else if (call.name === "update_preferences" || call.name === "get_user_memory" || call.name === "delete_user_preference") traceStore.addTrace('📚', 'Consulting Memory');
            else if (call.name === "browser_subagent") traceStore.addTrace('🌐', 'Browser Shadow Active');
            else if (call.name === "run_command") traceStore.addTrace('💻', 'Executing Command');
            else traceStore.addTrace('🛠️', `Running Tool: ${call.name}`);
          });

          if (onToolCall) {
            const results = await Promise.all(msg.toolCall.functionCalls.map(async (call: any) => {
              const res = await onToolCall(call);
              return {
                id: call.id,
                name: call.name,
                response: { result: res }
              };
            }));
            
            ws.send(JSON.stringify({
              toolResponse: {
                functionResponses: results
              }
            }));
          }
        }
      } catch (e) {
        logger.error("[Gemini Live] Message Parse Error:", e);
      }
    };

    ws.onclose = (event: CloseEvent) => {
      logger.info("[Gemini Live] Disconnected", { code: event.code, reason: event.reason });
      setIsConnected(false);
      setIsListening(false);
    };
  }, [onToolCall, onAgentMessage]);

  const startListening = useCallback(async () => {
    try {
      if (!audioContextRef.current) {
        const ctx = new (window.AudioContext || (window as any).webkitAudioContext)({
          sampleRate: 16000,
        });
        audioContextRef.current = ctx;
        
        workletLoadedRef.current = ctx.audioWorklet.addModule('/worklets/voice-processor.js').then(() => {});
      }
      if (workletLoadedRef.current) {
        await workletLoadedRef.current;
      }
      
      const audioCtx = audioContextRef.current;
      if (audioCtx.state === 'suspended') await audioCtx.resume();

      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
        } 
      });
      micStreamRef.current = stream;

      const source = audioCtx.createMediaStreamSource(stream);
      const micNode = new AudioWorkletNode(audioCtx, 'voice-processor');
      micWorkletRef.current = micNode;

      micNode.port.onmessage = (e) => {
        if (socketRef.current?.readyState === WebSocket.OPEN) {
          const inputData = e.data; // Float32Array
          const pcmData = new Int16Array(inputData.length);
          for (let i = 0; i < inputData.length; i++) {
            pcmData[i] = Math.max(-1, Math.min(1, inputData[i])) * 0x7FFF;
          }
          
          const base64Data = btoa(String.fromCharCode(...new Uint8Array(pcmData.buffer)));
          
          socketRef.current.send(JSON.stringify({
            realtimeInput: {
              mediaChunks: [{
                mimeType: "audio/pcm;rate=16000",
                data: base64Data
              }]
            }
          }));
        }
      };

      source.connect(micNode);

      // 2. Setup Playback Analyser
      if (!analyserRef.current) {
        analyserRef.current = audioCtx.createAnalyser();
        analyserRef.current.fftSize = 256;
      }

      // 3. User Speech Recognition for Chat UI
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition && onTranscript) {
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = false;
        recognition.lang = 'en-US'; // or dynamic based on user preference
        
        recognition.onresult = (event: any) => {
          const resultIndex = event.resultIndex;
          const transcript = event.results[resultIndex][0].transcript;
          if (transcript.trim()) {
            onTranscript(transcript.trim());
            traceStore.addTrace('📝', `Speech Recognized: "${transcript.trim()}"`);
          }
        };
        
        recognition.onend = () => {
          if (isListening) {
             try { recognition.start(); } catch {}
          }
        };
        
        try {
          recognition.start();
          recognitionRef.current = recognition;
        } catch(e) {
          logger.warn("[Gemini Live] SpeechRecognition failed to start:", e);
        }
      }

      setIsListening(true);
      setMicCaptured(true);
      logger.info("[Gemini Live] 🎙 Mic capture and playback stream started.");
      traceStore.addTrace('🎤', 'Listening');
    } catch (err) {
      logger.error("[Gemini Live] Failed to start voice system:", err);
    }
  }, [onTranscript, isListening]);

  const setMicMuted = useCallback((muted: boolean) => {
    if (micStreamRef.current) {
      micStreamRef.current.getAudioTracks().forEach(track => {
        track.enabled = !muted;
      });
    }
    setIsListening(!muted);
  }, []);

  const stopListening = useCallback(() => {
    setMicMuted(true);
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch {}
    }
  }, [setMicMuted]);

  const sendTextMessage = useCallback(async (text: string) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({
        clientContent: {
          turns: [{ role: "user", parts: [{ text }] }],
          turnComplete: true
        }
      }));
    } else {
      logger.warn("[Gemini Live] Socket not open, cannot send message.");
    }
  }, [onAgentMessage, onToolCall]);

  return {
    isConnected,
    isListening,
    isSpeaking,
    micCaptured,
    connect,
    disconnect,
    startListening,
    stopListening,
    setMicMuted,
    sendTextMessage,
    setApiKey
  };
}
