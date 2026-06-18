import { useState, useCallback, useRef, useEffect } from 'react';

// Simple logger to prevent Next.js error overlays in development
const logger = {
  info: (msg: string, ...args: any[]) => console.info(`%c${msg}`, 'color: #3b82f6', ...args),
  warn: (msg: string, ...args: any[]) => console.warn(`%c${msg}`, 'color: #f59e0b', ...args),
  error: (msg: string, ...args: any[]) => console.error(`%c${msg}`, 'color: #ef4444', ...args),
  debug: (msg: string, ...args: any[]) => {
    if (process.env.NODE_ENV === 'development') {
      console.debug(`%c${msg}`, 'color: #10b981', ...args);
    }
  }
};

interface UseNexusVoiceProps {
  onMessage?: (msg: any) => void;
  onTranscript?: (text: string) => void;
  onAgentMessage?: (text: string, isParagraphEnd: boolean) => void;
  persona?: string;
  ttsProvider?: string;
  language?: string;
  voiceEngine?: string;
}

export function useNexusVoice({ onTranscript, onAgentMessage, persona, ttsProvider, language, voiceEngine }: UseNexusVoiceProps = {}) {
  const [isConnected, setIsConnected] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [micCaptured, setMicCaptured] = useState(false);
  const [systemMetrics, setSystemMetrics] = useState<any>(null);
  
  const socketRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const micWorkletRef = useRef<AudioWorkletNode | null>(null);
  const nextStartTimeRef = useRef<number>(0);
  const activeAudioNodesRef = useRef<AudioBufferSourceNode[]>([]);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const workletLoadedRef = useRef<Promise<void> | null>(null);

  const connectionStateRef = useRef<"idle" | "connecting" | "connected" | "reconnecting" | "disconnected">("idle");
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const maxRetries = 99999;

  const isConnectingRef = useRef(false);

  const pingTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Stable ref to connect so the reconnect timer never captures a stale closure
  const connectRef = useRef<() => void>(() => {});
  // Stable refs for callbacks so connect/disconnect never change identity
  const onTranscriptRef = useRef(onTranscript);
  const onAgentMessageRef = useRef(onAgentMessage);
  useEffect(() => { onTranscriptRef.current = onTranscript; }, [onTranscript]);
  useEffect(() => { onAgentMessageRef.current = onAgentMessage; }, [onAgentMessage]);

  // Global Autoplay Unlocker: Initialize/Resume AudioContext on any user interaction
  useEffect(() => {
    const unlockAudio = () => {
      try {
        if (!audioContextRef.current) {
          audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({
            sampleRate: 16000,
          });
        }
        if (audioContextRef.current.state === 'suspended') {
          audioContextRef.current.resume().catch(() => {});
        }
      } catch (err) {
        console.warn("[NexusVoice] Clean close failed:", err);
        // Ignore initialization errors
      }
    };

    window.addEventListener('click', unlockAudio, { passive: true });
    window.addEventListener('keydown', unlockAudio, { passive: true });

    return () => {
      window.removeEventListener('click', unlockAudio);
      window.removeEventListener('keydown', unlockAudio);
    };
  }, []);

  useEffect(() => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      logger.info("[Nexus WS] 📤 Sending settings...", { persona, ttsProvider, language, voiceEngine });
      socketRef.current.send(JSON.stringify({
        type: 'settings',
        persona,
        ttsProvider,
        language,
        voiceEngine
      }));
    }
  }, [persona, ttsProvider, language, voiceEngine, isConnected]);

  // Intercept Vision frames from GeminiVision and send them via WS
  useEffect(() => {
    const handleVisionFrame = (e: any) => {
      const frameBase64 = e.detail?.frame;
      if (frameBase64 && socketRef.current?.readyState === WebSocket.OPEN) {
        socketRef.current.send(JSON.stringify({
          type: "vision_frame",
          mime_type: "image/jpeg",
          data: frameBase64
        }));
      }
    };
    window.addEventListener("nexus_vision_frame", handleVisionFrame);
    return () => window.removeEventListener("nexus_vision_frame", handleVisionFrame);
  }, []);

  const disconnect = useCallback(() => {
    logger.info("[Nexus WS] Disconnecting...");
    connectionStateRef.current = "disconnected";
    setIsConnected(false);
    setIsListening(false);
    
    if (pingTimerRef.current) {
      clearInterval(pingTimerRef.current);
      pingTimerRef.current = null;
    }
    
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }

    if (socketRef.current) {
      socketRef.current.onclose = null; // Prevent reconnect logic
      socketRef.current.close(1000, "Intentional disconnect");
      socketRef.current = null;
    }

    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach(t => t.stop());
      micStreamRef.current = null;
    }
    
    setMicCaptured(false);

    if (audioContextRef.current?.state !== 'closed') {
      audioContextRef.current?.close();
    }
    
    activeAudioNodesRef.current.forEach((node) => {
      try { node.stop(); node.disconnect(); } catch { /* ignore */ }
    });
    activeAudioNodesRef.current = [];
    nextStartTimeRef.current = 0;
    
    micWorkletRef.current?.disconnect();
  }, []);

  const ensureAudioContext = useCallback(async () => {
    if (typeof window === 'undefined') return null;
    try {
      if (!audioContextRef.current) {
        const ctx = new (window.AudioContext || (window as any).webkitAudioContext)({
          sampleRate: 16000,
        });
        audioContextRef.current = ctx;
      }
      const ctx = audioContextRef.current;
      if (ctx.state === 'suspended') {
        try {
          await ctx.resume();
        } catch (e) {
          console.warn("[Nexus Voice] AudioContext resume blocked by browser policy:", e);
        }
      }
      if (!analyserRef.current) {
        analyserRef.current = ctx.createAnalyser();
        analyserRef.current.connect(ctx.destination);
      }
      return ctx;
    } catch (err) {
      console.error("[Nexus Voice] Failed to ensure AudioContext:", err);
      return null;
    }
  }, []);

  const connect = useCallback(() => {
    if (connectionStateRef.current === "connected" || connectionStateRef.current === "connecting") {
      return;
    }

    let sessionId = typeof window !== 'undefined' ? localStorage.getItem('nexus_session_id') : null;
    if (!sessionId && typeof window !== 'undefined') {
      sessionId = crypto.randomUUID();
      localStorage.setItem('nexus_session_id', sessionId);
    }

    isConnectingRef.current = true;
    connectionStateRef.current = reconnectAttemptsRef.current > 0 ? "reconnecting" : "connecting";
    
    // Choose endpoint based on voice engine preference
    let engine = typeof window !== 'undefined' ? localStorage.getItem('nexus_voice_engine') : 'standard';
    const endpoint = engine === 'gemini_live' ? 'gemini-live' : 'nexus';
    const wsUrl = `ws://localhost:8001/ws/${endpoint}?session_id=${sessionId}`;
    
    logger.info(`[WS] ${connectionStateRef.current === "reconnecting" ? "Reconnecting" : "Connecting"} to: ${wsUrl}`);
    if (socketRef.current) {
      socketRef.current.onclose = null;
      socketRef.current.close();
      socketRef.current = null;
    }

    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onopen = () => {
      logger.info("[Nexus WS] ✅ Connected");
      connectionStateRef.current = "connected";
      isConnectingRef.current = false;
      reconnectAttemptsRef.current = 0;
      setIsConnected(true);

      if (pingTimerRef.current) clearInterval(pingTimerRef.current);
      pingTimerRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "ping", timestamp: Date.now() }));
        }
      }, 10000);
    };

    ws.onmessage = async (event) => {
      if (typeof event.data === 'string') {
        try {
          const msg = JSON.parse(event.data);
          
          if (msg.type === 'audio_chunk') {
            const { data } = msg;
            const base64Bytes = data.length; // base64 string length
            const pcmBytes = Math.floor(base64Bytes * 0.75); // approx decoded bytes
            console.log(`[FORENSIC] AUDIO_CHUNK_RECEIVED chunk_index=${msg.meta?.chunk_index} base64_len=${base64Bytes} approx_pcm_bytes=${pcmBytes} turn=${msg.meta?.turn_id}`);
            
            // Convert base64 to Int16Array -> Float32Array
            const binaryString = window.atob(data);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
              bytes[i] = binaryString.charCodeAt(i);
            }
            const int16Array = new Int16Array(bytes.buffer);
            const float32Data = new Float32Array(int16Array.length);
            for (let i = 0; i < int16Array.length; i++) {
              float32Data[i] = int16Array[i] / 32768.0;
            }

            // Playback via AudioBufferSourceNode
            const ctx = await ensureAudioContext();
            console.log(`[FORENSIC] AUDIO_CONTEXT_STATE state=${ctx?.state} analyser_exists=${!!analyserRef.current}`);
            if (ctx && analyserRef.current) {
                if (ctx.state === 'suspended') {
                    console.error(`[FORENSIC] PLAYBACK_BLOCKED reason=AUDIO_CONTEXT_SUSPENDED`);
                    if (socketRef.current?.readyState === WebSocket.OPEN) {
                        socketRef.current.send(JSON.stringify({ type: 'audio_finished' }));
                    }
                    return;
                }
                
                if (float32Data.length === 0) {
                    console.warn(`[FORENSIC] PLAYBACK_SKIPPED reason=ZERO_LENGTH_CHUNK`);
                    return;
                }
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

                console.log(`[FORENSIC] PLAYBACK_STARTED scheduled_at=${nextStartTimeRef.current.toFixed(3)} ctx_time=${currentTime.toFixed(3)} buffer_duration=${buffer.duration.toFixed(3)}s samples=${float32Data.length}`);
                source.start(nextStartTimeRef.current);
                nextStartTimeRef.current += buffer.duration;

                activeAudioNodesRef.current.push(source);
                
                source.onended = () => {
                  activeAudioNodesRef.current = activeAudioNodesRef.current.filter((n) => n !== source);
                  console.log(`[FORENSIC] PLAYBACK_FINISHED remaining_nodes=${activeAudioNodesRef.current.length}`);
                  if (activeAudioNodesRef.current.length === 0) {
                    setIsSpeaking(false);
                    console.log(`[FORENSIC] ALL_AUDIO_FINISHED sending audio_finished to backend`);
                    if (socketRef.current?.readyState === WebSocket.OPEN) {
                      socketRef.current.send(JSON.stringify({ type: 'audio_finished' }));
                    }
                  }
                };
                
                setIsSpeaking(true);
            } else {
                console.error(`[FORENSIC] PLAYBACK_SKIPPED reason=CTX_OR_ANALYSER_NULL ctx=${!!ctx} analyser=${!!analyserRef.current}`);
            }
            
          } else if (msg.type === 'tts_end') {
            logger.info(`🏁 [WS] Received tts_end for Turn ${msg.turn_id}`);
            // Failsafe: if we receive tts_end and nothing is playing, the backend will deadlock waiting for audio_finished
            if (activeAudioNodesRef.current.length === 0) {
              setIsSpeaking(false);
              if (socketRef.current?.readyState === WebSocket.OPEN) {
                socketRef.current.send(JSON.stringify({ type: 'audio_finished' }));
              }
            }
          } else if (msg.type === 'user_transcript') {
            onTranscriptRef.current?.(msg.text);
          } else if (msg.type === 'agent_partial') {
            onAgentMessageRef.current?.(msg.text, !!msg.is_paragraph_end);
          } else if (msg.type === 'metrics') {
            setSystemMetrics(msg.data);
          } else if (msg.type === 'agent_message') {
            onAgentMessageRef.current?.(msg.text, true);
          } else if (msg.type === 'interrupt') {
            // Immediately stop playback on barge-in
            activeAudioNodesRef.current.forEach((node) => {
              try { node.stop(); node.disconnect(); } catch { /* ignore */ }
            });
            activeAudioNodesRef.current = [];
            nextStartTimeRef.current = 0;
            
            setIsSpeaking(false);
            logger.info("[Nexus WS] 💥 Agent interrupted");
          } else if (msg.type === 'pong') {
            const latency = Date.now() - msg.timestamp;
            logger.debug(`[Nexus WS] 🏓 Pong received in ${latency}ms`);
          } else if (msg.type === 'system_metrics') {
            setSystemMetrics(msg.data);
          } else if (msg.type === 'log') {
            if (logger[msg.level as keyof typeof logger]) {
              (logger as any)[msg.level](`[Backend] ${msg.message}`);
            } else {
              logger.info(`[Backend] ${msg.message}`);
            }
          }
        } catch (e) {
          logger.error("[Nexus WS] Message Parse Error:", e);
        }
      }
    };

    ws.onclose = (event: CloseEvent) => {
      const isIntentional = connectionStateRef.current === "disconnected";
      
      if (isIntentional) {
        logger.debug(`[Nexus WS] Disconnected (Code: ${event.code})`);
      } else {
        if (reconnectAttemptsRef.current > 0) {
          logger.warn(`[Nexus WS] Connection lost (Code: ${event.code})`);
        }
      }

      // RC-2 FIX: Always reset listening state on disconnect — prevents OFFLINE+LISTENING invalid state
      setIsConnected(false);
      setIsListening(false);
      setIsSpeaking(false);
      isConnectingRef.current = false;

      // Stop mic hardware stream if active — prevents ghost mic capture
      if (micStreamRef.current) {
        micStreamRef.current.getTracks().forEach(t => t.stop());
        micStreamRef.current = null;
      }
      if (micWorkletRef.current) {
        micWorkletRef.current.disconnect();
        micWorkletRef.current = null;
      }
      setMicCaptured(false);
      workletLoadedRef.current = null;

      if (isIntentional) {
        connectionStateRef.current = "idle";
        return;
      }

      if (reconnectAttemptsRef.current < maxRetries) {
        connectionStateRef.current = "reconnecting";
        const backoffMs = Math.min(1000 * Math.pow(1.5, reconnectAttemptsRef.current), 5000);
        console.log(`[Nexus WS] Reconnecting in ${backoffMs}ms (Attempt ${reconnectAttemptsRef.current + 1}/${maxRetries})`);
        reconnectAttemptsRef.current += 1;
        
        if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = setTimeout(() => {
          if (connectionStateRef.current === "reconnecting") {
            connectionStateRef.current = "idle";
            connectRef.current();
          }
        }, backoffMs);
      } else {
        logger.error("[Nexus WS] ⛔ Max reconnect attempts reached.");
        connectionStateRef.current = "disconnected";
      }
    };

    ws.onerror = (event) => {
      if (reconnectAttemptsRef.current < 1) {
         logger.debug("[Nexus WS] Connectivity hint", event);
      }
    };
  }, []); // stable — callbacks accessed via refs, no external deps

  // Keep connectRef in sync so the reconnect timer always calls the live function
  useEffect(() => { connectRef.current = connect; }, [connect]);

  // Cleaned up properly by VoiceProvider on unmount.

  const startListening = useCallback(async () => {
    try {
      if (!audioContextRef.current) {
        const ctx = new (window.AudioContext || (window as any).webkitAudioContext)({
          sampleRate: 16000,
        });
        audioContextRef.current = ctx;
      }
      
      // RC-2 FIX: Connect WS first, then wait for it before starting mic
      if (connectionStateRef.current !== "connected") {
        connect();
        // Wait up to 5s for WS to open before activating mic
        let waited = 0;
        while ((connectionStateRef.current as string) !== "connected" && waited < 50) {
          await new Promise(r => setTimeout(r, 100));
          waited++;
        }
        if ((connectionStateRef.current as string) !== "connected") {
          logger.warn("[Nexus Voice] WS not connected after 5s, deferring mic start");
          return;
        }
      }
      
      const audioCtx = audioContextRef.current;
      if (audioCtx.state === 'suspended') {
        await audioCtx.resume();
      }

      if (!workletLoadedRef.current) {
        workletLoadedRef.current = audioCtx.audioWorklet.addModule('/worklets/voice-processor.js').catch(e => {
          workletLoadedRef.current = null;
          throw e;
        });
      }
      
      await workletLoadedRef.current;

      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
        } 
      });
      micStreamRef.current = stream;

      // FIX: Ensure we are still connected after getting mic permissions
      if (connectionStateRef.current !== "connected") {
        stream.getTracks().forEach(t => t.stop());
        micStreamRef.current = null;
        logger.warn("[Nexus Voice] WS disconnected while getting mic. Aborting.");
        return;
      }

      // 1. Setup Capture
      const source = audioCtx.createMediaStreamSource(stream);
      const micNode = new AudioWorkletNode(audioCtx, 'voice-processor');
      micWorkletRef.current = micNode;

      let audioBuffer: Float32Array[] = [];
      let audioBufferLength = 0;

      micNode.port.onmessage = (e) => {
        if (socketRef.current?.readyState === WebSocket.OPEN) {
          const inputData = e.data; // Float32Array
          audioBuffer.push(inputData);
          audioBufferLength += inputData.length;

          if (audioBufferLength >= 4096) {
            const combined = new Float32Array(audioBufferLength);
            let offset = 0;
            for (const buf of audioBuffer) {
              combined.set(buf, offset);
              offset += buf.length;
            }
            
            const pcmData = new Int16Array(combined.length);
            for (let i = 0; i < combined.length; i++) {
              pcmData[i] = Math.max(-1, Math.min(1, combined[i])) * 0x7FFF;
            }
            socketRef.current.send(pcmData.buffer);
            
            audioBuffer = [];
            audioBufferLength = 0;
          }
        }
      };

      source.connect(micNode);

      // 2. Setup Playback
      if (!analyserRef.current) {
        analyserRef.current = audioCtx.createAnalyser();
        analyserRef.current.fftSize = 256;
      }

      setIsListening(true);
      setMicCaptured(true);
      console.log(`[Nexus Voice] 🎙 Mic capture and playback stream started. AudioContext State: ${audioCtx.state}`);
      
      audioCtx.onstatechange = () => {
        console.log(`[Nexus Voice] 🔊 AudioContext state changed: ${audioCtx.state}`);
      };
    } catch (err) {
      console.error("[Nexus Voice] Failed to start voice system:", err);
    }
  }, []);

  const setMicMuted = useCallback((muted: boolean) => {
    if (micStreamRef.current) {
      micStreamRef.current.getAudioTracks().forEach(track => {
        track.enabled = !muted;
      });
    }
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ action: muted ? 'mute' : 'unmute' }));
    }
    
    if (!muted && connectionStateRef.current !== "connected") {
      logger.warn("[Nexus Voice] Cannot listen while offline.");
      setIsListening(false);
      return;
    }
    
    setIsListening(!muted);
    console.log(`[Nexus Voice] Mic is now ${muted ? 'muted' : 'unmuted'}`);
  }, []);

  const stopListening = useCallback(() => {
    setMicMuted(true);
  }, [setMicMuted]);

  // Removed redundant disconnect definition here as it was moved up

  const sendTextMessage = useCallback((text: string, speech: boolean = true) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ text, speech }));
    } else {
      logger.warn("[Nexus Voice] Socket not open, message queued or lost");
    }
  }, []);

  const updateSettings = useCallback((settings: any) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({
        type: 'settings',
        ...settings
      }));
    }
  }, []);

  const testVoice = useCallback(async (text?: string) => {
    console.log("[VOICE_STUDIO] Request sent", { readyState: socketRef.current?.readyState, text });
    await ensureAudioContext();
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'test_voice', text }));
    } else {
      console.warn("[VOICE_STUDIO] WebSocket not open, cannot test voice");
    }
  }, [ensureAudioContext]);

  useEffect(() => {
    return () => {
      if (socketRef.current && (socketRef.current.readyState === WebSocket.OPEN || socketRef.current.readyState === WebSocket.CONNECTING)) {
        socketRef.current.close(1000, "Component unmounted");
      }
    };
  }, []);

  return {
    isConnected,
    isListening,
    isSpeaking,
    micCaptured,
    systemMetrics,
    connect,
    disconnect,
    startListening,
    stopListening,
    setMicMuted,
    sendTextMessage,
    updateSettings,
    testVoice,
  };
}
