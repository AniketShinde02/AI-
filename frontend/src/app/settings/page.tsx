"use client";

import { useState } from "react";
import { Settings, Shield, Mic, Volume2, Cpu, Zap, Globe, Save } from "lucide-react";
import Link from "next/link";
import { useNexus } from "@/contexts/NexusContext";

export default function SettingsPage() {
  const { selectedModel, setSelectedModel, persona, setPersona, ttsProvider, setTtsProvider, language, setLanguage, voiceEngine, setVoiceEngine } = useNexus();
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="h-full flex flex-col overflow-hidden p-4 gap-4">
      {/* Header */}
      <div className="flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-[#6137FF]/20 border border-[#6137FF]/40 flex items-center justify-center clip-cut">
            <Settings size={16} className="text-[#6137FF]" />
          </div>
          <div>
            <h1 className="text-[11px] font-quantico font-bold uppercase tracking-[0.3em] text-white">Command Center</h1>
            <p className="text-[9px] font-mono text-zinc-500 uppercase tracking-widest">System Configuration</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleSave}
            className={`flex items-center gap-2 px-3 py-2 text-[9px] font-bold uppercase tracking-widest clip-cut transition-all ${
              saved
                ? "bg-[#10b981] text-white shadow-[0_0_15px_rgba(16,185,129,0.3)]"
                : "bg-[#6137FF] hover:bg-[#7b5cff] text-white shadow-[0_0_15px_rgba(97,55,255,0.3)]"
            }`}
          >
            <Save size={12} />
            {saved ? "Saved!" : "Save Config"}
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto scroll-hide">
        <div className="grid grid-cols-2 gap-4">
          {/* LLM Model */}
          <div className="bg-[#06060c] border border-[#6137FF]/15 clip-cut p-5">
            <div className="flex items-center gap-2 mb-4">
              <Cpu size={14} className="text-[#6137FF]" />
              <h2 className="text-[10px] font-quantico font-bold uppercase tracking-widest text-white">LLM Model</h2>
            </div>
            <div className="flex flex-col gap-2">
              {[
                { value: "llama-3.3-70b-versatile", label: "Llama 3.3 70B", badge: "GROQ" },
                { value: "llama-3.1-8b-instant", label: "Llama 3.1 8B (Fast)", badge: "GROQ" },
                { value: "gemini-2.0-flash", label: "Gemini 2.0 Flash", badge: "GOOGLE" },
                { value: "deepseek-chat", label: "DeepSeek Chat", badge: "DEEPSEEK" },
              ].map((model) => (
                <button
                  key={model.value}
                  onClick={() => setSelectedModel(model.value)}
                  className={`flex items-center justify-between p-3 border clip-cut-sm text-left transition-all ${
                    selectedModel === model.value
                      ? "border-[#6137FF]/50 bg-[#6137FF]/10 text-white"
                      : "border-white/5 text-zinc-400 hover:border-white/15 hover:text-white"
                  }`}
                >
                  <span className="text-[11px] font-mono">{model.label}</span>
                  <span className="text-[8px] font-bold uppercase tracking-widest px-2 py-0.5 border border-white/10 text-zinc-500 clip-cut-sm">
                    {model.badge}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Voice Studio Link */}
          <div className="bg-[#06060c] border border-[#00FFFF]/15 clip-cut p-5 flex flex-col">
            <div className="flex items-center gap-2 mb-4">
              <Volume2 size={14} className="text-[#00FFFF]" />
              <h2 className="text-[10px] font-quantico font-bold uppercase tracking-widest text-white">Voice Output</h2>
            </div>
            <div className="flex-1 flex flex-col justify-center items-center gap-4 py-4">
              <p className="text-[10px] text-zinc-400 text-center font-mono px-4">
                Configure TTS Providers, Voices, Pitch, Speed, and Volume in the dedicated Voice Studio.
              </p>
              <Link
                href="/settings/voice-studio"
                className="px-4 py-2 bg-[#00FFFF]/10 border border-[#00FFFF]/30 text-[#00FFFF] text-[10px] font-bold uppercase tracking-widest clip-cut transition-all hover:bg-[#00FFFF]/20 flex items-center gap-2"
              >
                <Volume2 size={12} />
                Open Voice Studio
              </Link>
            </div>
          </div>

          {/* Persona */}
          <div className="bg-[#06060c] border border-white/5 clip-cut p-5">
            <div className="flex items-center gap-2 mb-4">
              <Mic size={14} className="text-[#ff3366]" />
              <h2 className="text-[10px] font-quantico font-bold uppercase tracking-widest text-white">Voice Persona</h2>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {[
                { value: "sarah", label: "Sarah", icon: "👩" },
                { value: "nexus_male", label: "Nexus Male", icon: "👨‍💻" },
                { value: "professional_male", label: "Professional Male", icon: "👔" },
                { value: "casual_female", label: "Casual Female", icon: "👱‍♀️" }
              ].map((p) => (
                <button
                  key={p.value}
                  onClick={() => setPersona(p.value)}
                  className={`p-4 border clip-cut text-center transition-all ${
                    persona === p.value
                      ? "border-[#ff3366]/50 bg-[#ff3366]/10 text-white"
                      : "border-white/5 text-zinc-500 hover:border-white/15 hover:text-white"
                  }`}
                >
                  <div className="text-2xl mb-1">{p.icon}</div>
                  <span className="text-[10px] font-bold uppercase tracking-widest">{p.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Language */}
          <div className="bg-[#06060c] border border-white/5 clip-cut p-5">
            <div className="flex items-center gap-2 mb-4">
              <Globe size={14} className="text-[#10b981]" />
              <h2 className="text-[10px] font-quantico font-bold uppercase tracking-widest text-white">Language</h2>
            </div>
            <div className="flex flex-col gap-2">
              {[
                { value: "auto", label: "Auto Detect" },
                { value: "en", label: "English" },
                { value: "hi", label: "हिंदी (Hindi)" },
                { value: "mr", label: "मराठी (Marathi)" },
              ].map((lang) => (
                <button
                  key={lang.value}
                  onClick={() => setLanguage(lang.value)}
                  className={`flex items-center justify-between p-3 border clip-cut-sm text-left transition-all ${
                    language === lang.value
                      ? "border-[#10b981]/50 bg-[#10b981]/5 text-white"
                      : "border-white/5 text-zinc-400 hover:border-white/15 hover:text-white"
                  }`}
                >
                  <span className="text-[11px] font-mono">{lang.label}</span>
                  {lang.value === "auto" && (
                    <Zap size={12} className="text-[#10b981]" />
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Voice Engine (Experimental) */}
          <div className="col-span-2 bg-[#06060c] border border-orange-500/15 clip-cut p-5">
            <div className="flex items-center gap-2 mb-4">
              <Zap size={14} className="text-orange-500" />
              <h2 className="text-[10px] font-quantico font-bold uppercase tracking-widest text-white">Voice Engine</h2>
            </div>
            <div className="grid grid-cols-2 gap-4">
              {[
                { value: "standard", label: "Standard", badge: "GROQ + TTS" },
                { value: "gemini_live", label: "Gemini Live Experimental", badge: "NATIVE AUDIO" },
              ].map((engine) => (
                <button
                  key={engine.value}
                  onClick={() => setVoiceEngine(engine.value)}
                  className={`flex items-center justify-between p-3 border clip-cut-sm text-left transition-all ${
                    voiceEngine === engine.value
                      ? "border-orange-500/50 bg-orange-500/10 text-white"
                      : "border-white/5 text-zinc-400 hover:border-white/15 hover:text-white"
                  }`}
                >
                  <span className="text-[11px] font-mono">{engine.label}</span>
                  <span className="text-[8px] font-bold uppercase tracking-widest px-2 py-0.5 border border-white/10 text-zinc-500 clip-cut-sm">
                    {engine.badge}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* System Info */}
          <div className="col-span-2 bg-[#06060c] border border-white/5 clip-cut p-5">
            <div className="flex items-center gap-2 mb-4">
              <Shield size={14} className="text-zinc-500" />
              <h2 className="text-[10px] font-quantico font-bold uppercase tracking-widest text-white">System Info</h2>
            </div>
            <div className="grid grid-cols-4 gap-4">
              {[
                { label: "Frontend", value: "Next.js 15" },
                { label: "Backend", value: "FastAPI + WS" },
                { label: "STT", value: "Groq Whisper" },
                { label: "Version", value: "Nexus v1.0" },
              ].map(({ label, value }) => (
                <div key={label} className="flex flex-col gap-1">
                  <span className="text-[8px] font-mono uppercase tracking-widest text-zinc-600">{label}</span>
                  <span className="text-[11px] font-bold text-zinc-300">{value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
