"use client";

import { useState, useEffect } from "react";
import { Volume2, ArrowLeft, Play, Settings2, ShieldAlert, Activity, SlidersHorizontal } from "lucide-react";
import Link from "next/link";
import { useNexus } from "@/contexts/NexusContext";
import { useVoice } from "@/contexts/VoiceContext";

interface VoiceOption { id: string; label: string; }

interface Voices {
  gemini: VoiceOption[];
  edge: VoiceOption[];
}

export default function VoiceStudioPage() {
  const {
    ttsProvider,
    setTtsProvider,
    voice,
    setVoice,
    speed,
    setSpeed,
    pitch,
    setPitch,
    voiceVolume,
    setVoiceVolume,
    isListening
  } = useNexus();

  const { setMicMuted, systemMetrics } = useVoice();

  const [voices, setVoices] = useState<Voices>({ gemini: [], edge: [] });
  const [loading, setLoading] = useState(true);
  const [previewState, setPreviewState] = useState<"IDLE" | "GENERATING" | "PLAYING" | "SUCCESS" | "FAILED">("IDLE");
    const [healthStatus, setHealthStatus] = useState<any>(null);

  const showCosmeticControls = false;

  useEffect(() => {
    const checkHealth = () => {
      fetch("http://localhost:8001/health")
        .then(res => res.json())
        .then(data => setHealthStatus(data))
        .catch(err => console.error("Failed to fetch health:", err));
    };
    checkHealth();
    const interval = setInterval(checkHealth, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    fetch("http://localhost:8001/api/voices")
      .then(res => res.json())
      .then(data => {
        setVoices(data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to fetch voices:", err);
        setLoading(false);
      });
  }, []);

  const handleTestVoice = async () => {
    if (previewState === "GENERATING" || previewState === "PLAYING") return;
    console.log("[VOICE_STUDIO] Button clicked");
    setPreviewState("GENERATING");
    
    const payload = {
      provider: ttsProvider,
      voice: voice || (currentProviderVoices[0]?.id || ""),
      speed: parseFloat(String(speed)),
      pitch: parseFloat(String(pitch))
    };
    
    try {
      console.log("[VOICE_STUDIO] Request sent", payload);
      const res = await fetch("http://localhost:8001/api/voice/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      
      const audioBlob = await res.blob();
      console.log("[VOICE_STUDIO] Audio received", { size: audioBlob.size });
      
      const arrayBuffer = await audioBlob.arrayBuffer();
      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const audioBuffer = await ctx.decodeAudioData(arrayBuffer);
      const source = ctx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(ctx.destination);
      
      console.log("[VOICE_STUDIO] Playback started");
      setPreviewState("PLAYING");
      
      const wasListening = isListening;
      if (wasListening) {
        setMicMuted(true);
      }
      
      source.onended = () => {
        setPreviewState("SUCCESS");
        if (wasListening) {
          setMicMuted(false);
        }
      };
      
      source.start(0);
    } catch (err) {
      console.error("[VOICE_STUDIO] Test voice failed:", err);
      setPreviewState("FAILED");
      setMicMuted(false); // Fallback safe-restore
    }
  };

  const currentProvider = ttsProvider.toLowerCase() === "gemini" ? "gemini" : (ttsProvider.toLowerCase() === "edge" ? "edge" : "auto");
  
  // Safe extraction with fallback to empty array
  const currentProviderVoices = currentProvider === "gemini" 
    ? (voices?.gemini || []) 
    : (currentProvider === "edge" ? (voices?.edge || []) : []);

  // Make sure selected voice is valid for provider, else reset
  useEffect(() => {
    if (currentProvider !== "auto" && currentProviderVoices.length > 0) {
      if (!currentProviderVoices.find(v => v.id === voice)) {
        setVoice(currentProviderVoices[0].id);
      }
    }
  }, [currentProvider, currentProviderVoices, voice, setVoice]);

  return (
    <div className="h-full flex flex-col overflow-hidden p-4 gap-4 bg-[#06060c]">
      {/* Header */}
      <div className="flex items-center gap-4 shrink-0">
        <Link href="/settings" className="w-8 h-8 flex items-center justify-center bg-zinc-900 border border-zinc-700 hover:bg-zinc-800 transition-colors clip-cut">
          <ArrowLeft size={16} className="text-zinc-400" />
        </Link>
        <div>
          <h1 className="text-[11px] font-quantico font-bold uppercase tracking-[0.3em] text-[#00FFFF]">Voice Studio</h1>
          <p className="text-[9px] font-mono text-zinc-500 uppercase tracking-widest">Acoustic Parameter Configuration</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto scroll-hide pb-20">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          
          {/* Provider Selection */}
          <div className="bg-[#0a0a12] border border-[#00FFFF]/15 clip-cut p-5">
            <div className="flex items-center gap-2 mb-4">
              <Settings2 size={14} className="text-[#00FFFF]" />
              <h2 className="text-[10px] font-quantico font-bold uppercase tracking-widest text-white">TTS Provider</h2>
            </div>
            <div className="flex flex-col gap-2">
              {(() => { console.log("Rendering provider selection button list"); return null; })()}
              {[
                { value: "auto", label: "Auto (Router Default)", badge: "DYNAMIC" },
                { value: "gemini", label: "Gemini TTS", badge: "24kHz PCM" },
                { value: "edge", label: "Edge TTS", badge: "MICROSOFT" },
              ].map((provider) => (
                <button
                  key={provider.value}
                  onClick={() => setTtsProvider(provider.value)}
                  className={`flex items-center justify-between p-3 border clip-cut-sm text-left transition-all ${
                    currentProvider === provider.value
                      ? "border-[#00FFFF]/50 bg-[#00FFFF]/5 text-white"
                      : "border-white/5 text-zinc-400 hover:border-white/15 hover:text-white"
                  }`}
                >
                  <span className="text-[11px] font-mono">{provider.label}</span>
                  <span className="text-[8px] font-bold uppercase tracking-widest px-2 py-0.5 border border-white/10 text-zinc-500 clip-cut-sm">
                    {provider.badge}
                  </span>
                </button>
              ))}
            </div>
            {currentProvider === "auto" && (
                <div className="mt-4 p-3 bg-blue-500/10 border border-blue-500/20 text-blue-400 text-[10px] font-mono clip-cut-sm flex gap-2">
                    <ShieldAlert size={14} className="shrink-0" />
                    Auto mode uses the Nexus TTS Router to dynamically select the best provider based on language and speed requirements.
                </div>
            )}
          </div>

          {/* Voice Selection */}
          <div className={`bg-[#0a0a12] border ${currentProvider !== 'auto' ? 'border-purple-500/15' : 'border-white/5'} clip-cut p-5 ${currentProvider === 'auto' ? 'opacity-50 pointer-events-none' : ''}`}>
            <div className="flex items-center gap-2 mb-4">
              <Volume2 size={14} className={currentProvider !== 'auto' ? "text-purple-500" : "text-zinc-500"} />
              <h2 className="text-[10px] font-quantico font-bold uppercase tracking-widest text-white">Voice Model</h2>
            </div>
            {loading ? (
                <div className="text-[10px] font-mono text-zinc-500 animate-pulse">Loading voices...</div>
            ) : (
                <div className="flex flex-col gap-2 max-h-[200px] overflow-y-auto scroll-hide pr-2">
                {(() => { console.log("voices state:", voices); return null; })()}
                {(() => { console.log("currentProviderVoices:", currentProviderVoices); return null; })()}
                {Array.isArray(currentProviderVoices) ? currentProviderVoices.map((v) => {
                    if (!v || !v.id) return null; // Protect against stale backend strings
                    return (
                    <button
                    key={v.id}
                    onClick={() => setVoice(v.id)}
                    className={`flex items-center justify-between p-3 border clip-cut-sm text-left transition-all ${
                        voice === v.id
                        ? "border-purple-500/50 bg-purple-500/10 text-white"
                        : "border-white/5 text-zinc-400 hover:border-white/15 hover:text-white"
                    }`}
                    >
                    <span className="text-[11px] font-mono">{v.label || v.id}</span>
                    </button>
                    );
                }) : null}
                </div>
            )}
          </div>

          {/* Acoustic Parameters */}
          <div className="bg-[#0a0a12] border border-orange-500/15 clip-cut p-5 col-span-1 md:col-span-2">
            <div className="flex items-center gap-2 mb-6">
              <Settings2 size={14} className="text-orange-500" />
              <h2 className="text-[10px] font-quantico font-bold uppercase tracking-widest text-white">Acoustic Parameters</h2>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                {/* Speed */}
                <div className="flex flex-col gap-3">
                    <div className="flex justify-between items-center">
                        <label className="text-[10px] font-mono text-zinc-400 uppercase">Speed</label>
                        <span className="text-[10px] font-bold text-orange-400">{speed.toFixed(1)}x</span>
                    </div>
                    <input 
                        type="range" 
                        min="0.5" max="2.0" step="0.1" 
                        value={speed} 
                        onChange={(e) => setSpeed(parseFloat(e.target.value))}
                        className="w-full accent-orange-500"
                    />
                </div>

                {/* Pitch */}
                <div className="flex flex-col gap-3">
                    <div className="flex justify-between items-center">
                        <label className="text-[10px] font-mono text-zinc-400 uppercase">Pitch</label>
                        <span className="text-[10px] font-bold text-orange-400">{pitch > 0 ? `+${pitch}` : pitch}</span>
                    </div>
                    <input 
                        type="range" 
                        min="-20" max="20" step="1" 
                        value={pitch} 
                        onChange={(e) => setPitch(parseInt(e.target.value, 10))}
                        className="w-full accent-orange-500"
                    />
                </div>

                {/* Volume */}
                <div className="flex flex-col gap-3">
                    <div className="flex justify-between items-center">
                        <label className="text-[10px] font-mono text-zinc-400 uppercase">Volume</label>
                        <span className="text-[10px] font-bold text-orange-400">{voiceVolume}%</span>
                    </div>
                    <input 
                        type="range" 
                        min="0" max="100" step="1" 
                        value={voiceVolume} 
                        onChange={(e) => setVoiceVolume(parseInt(e.target.value, 10))}
                        className="w-full accent-orange-500"
                    />
                </div>
            </div>
            
            {showCosmeticControls && (
            <>
          {/* Speed Control */}
          <div className="col-span-1 p-5 border border-zinc-800 bg-zinc-900/50 clip-cut hover:border-zinc-700 transition-colors">
            <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-blue-500/10 rounded-lg">
                    <Activity size={16} className="text-blue-400" />
                </div>
                <div>
                    <h3 className="text-xs font-bold text-zinc-300">Speech Rate</h3>
                    <p className="text-[10px] text-zinc-500 mt-0.5 font-mono">1.0x (Normal)</p>
                </div>
            </div>
            
            <div className="mt-4">
                <input 
                    type="range" 
                    min="0.5" max="2.0" step="0.1"
                    value={speed}
                    onChange={(e) => setSpeed(parseFloat(e.target.value))}
                    className="w-full accent-blue-500 h-1 bg-zinc-800 rounded-lg appearance-none cursor-pointer"
                />
                <div className="flex justify-between mt-2 px-1">
                    <span className="text-[9px] font-mono text-zinc-600">0.5x</span>
                    <span className="text-[9px] font-mono text-zinc-300 font-bold">{speed.toFixed(1)}x</span>
                    <span className="text-[9px] font-mono text-zinc-600">2.0x</span>
                </div>
            </div>
          </div>

          {/* Pitch Control */}
          <div className="col-span-1 p-5 border border-zinc-800 bg-zinc-900/50 clip-cut hover:border-zinc-700 transition-colors">
            <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-rose-500/10 rounded-lg">
                    <SlidersHorizontal size={16} className="text-rose-400" />
                </div>
                <div>
                    <h3 className="text-xs font-bold text-zinc-300">Vocal Pitch</h3>
                    <p className="text-[10px] text-zinc-500 mt-0.5 font-mono">0 (Default)</p>
                </div>
            </div>
            
            <div className="mt-4">
                <input 
                    type="range" 
                    min="-10" max="10" step="1"
                    value={pitch}
                    onChange={(e) => setPitch(parseInt(e.target.value))}
                    className="w-full accent-rose-500 h-1 bg-zinc-800 rounded-lg appearance-none cursor-pointer"
                />
                <div className="flex justify-between mt-2 px-1">
                    <span className="text-[9px] font-mono text-zinc-600">-10</span>
                    <span className="text-[9px] font-mono text-zinc-300 font-bold">{pitch > 0 ? `+${pitch}` : pitch}</span>
                    <span className="text-[9px] font-mono text-zinc-600">+10</span>
                </div>
            </div>
          </div>

          {/* Volume Control */}
          <div className="col-span-1 md:col-span-2 p-5 border border-zinc-800 bg-zinc-900/50 clip-cut hover:border-zinc-700 transition-colors">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-emerald-500/10 rounded-lg">
                        <Volume2 size={16} className="text-emerald-400" />
                    </div>
                    <div>
                        <h3 className="text-xs font-bold text-zinc-300">Master Gain</h3>
                        <p className="text-[10px] text-zinc-500 mt-0.5 font-mono">Output Amplitude</p>
                    </div>
                </div>
                
                <div className="w-full md:w-1/2">
                    <input 
                        type="range" 
                        min="0" max="200" step="10"
                        value={voiceVolume}
                        onChange={(e) => setVoiceVolume(parseInt(e.target.value))}
                        className="w-full accent-emerald-500 h-1 bg-zinc-800 rounded-lg appearance-none cursor-pointer"
                    />
                    <div className="flex justify-between mt-2 px-1">
                        <span className="text-[9px] font-mono text-zinc-600">0%</span>
                        <span className="text-[9px] font-mono text-zinc-300 font-bold">{voiceVolume}%</span>
                        <span className="text-[9px] font-mono text-zinc-600">200%</span>
                    </div>
                </div>
            </div>
          </div>
            </>
          )}
          </div>

          {/* Test Voice Control */}
          <div className="col-span-1 md:col-span-2 flex justify-end mt-4">
            <button
                onClick={handleTestVoice}
                disabled={previewState === "GENERATING" || previewState === "PLAYING"}
                className={`flex items-center gap-3 px-6 py-3 border transition-all clip-cut ${
                    previewState === "FAILED" ? "bg-red-500/10 border-red-500/30 text-red-500 hover:bg-red-500/20" :
                    previewState === "SUCCESS" ? "bg-green-500/10 border-green-500/30 text-green-500 hover:bg-green-500/20" :
                    "bg-[#10b981]/10 border-[#10b981]/30 text-[#10b981] hover:bg-[#10b981]/20"
                } ${previewState === "GENERATING" || previewState === "PLAYING" ? "opacity-50 cursor-not-allowed" : ""}`}
            >
                {previewState === "GENERATING" ? <span className="animate-pulse">●</span> :
                 previewState === "PLAYING" ? <Play size={14} className="fill-current animate-pulse" /> :
                 previewState === "SUCCESS" ? <span>✓</span> :
                 previewState === "FAILED" ? <span>✕</span> :
                 <Play size={14} className="fill-current" />}
                <span className="text-[11px] font-bold uppercase tracking-widest">
                    {previewState === "GENERATING" ? "Generating..." :
                     previewState === "PLAYING" ? "Playing..." :
                     previewState === "SUCCESS" ? "Test Again" :
                     previewState === "FAILED" ? "Test Failed" :
                     "Test Voice"}
                </span>
            </button>
          </div>

          {/* Provider Diagnostics Panel */}
          <div className="col-span-1 md:col-span-2 mt-2 p-4 border border-zinc-800 bg-zinc-900/50 clip-cut">
            <h3 className="text-[10px] font-quantico font-bold uppercase tracking-widest text-zinc-500 mb-3">Provider Diagnostics</h3>
            <div className="flex flex-wrap gap-6 mb-4">
                <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-zinc-500 uppercase">Current Provider:</span>
                    <span className="text-[10px] font-mono text-white capitalize">{currentProvider}</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-zinc-500 uppercase">Current Voice:</span>
                    <span className="text-[10px] font-mono text-white capitalize">{currentProviderVoices.find(v => v.id === voice)?.label || voice}</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-zinc-500 uppercase">Last Voice Used:</span>
                    <span className="text-[10px] font-mono text-[#00FFFF] capitalize">{systemMetrics?.voice || 'None'}</span>
                </div>
            </div>
            <div className="flex flex-wrap gap-6 border-t border-zinc-800 pt-3">
                <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${healthStatus?.tts_providers?.gemini === 'ready' ? 'bg-green-500' : 'bg-red-500'}`}></div>
                    <span className="text-[10px] font-mono text-zinc-400">Gemini TTS</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${healthStatus?.tts_providers?.edge === 'ready' ? 'bg-green-500' : 'bg-red-500'}`}></div>
                    <span className="text-[10px] font-mono text-zinc-400">Edge TTS</span>
                </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
