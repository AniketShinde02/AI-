"use client";

import { useState, useEffect, useRef } from "react";
import { useNexus } from "@/contexts/NexusContext";
import {
  Paperclip,
  Mic,
  MicOff,
  ArrowUp,
  Zap,
  Code2,
  Palette,
  Globe,
  ChevronDown,
  Check,
  Loader2,
  Volume2
} from "lucide-react";

const MODELS = [
  { id: "llama-3.3-70b-versatile",  label: "Llama 3.3 70B",  badge: "Fast"     },
  { id: "llama-3.1-8b-instant",     label: "Llama 3.1 8B",   badge: "Instant"  },
  { id: "mixtral-8x7b-32768",       label: "Mixtral 8×7B",   badge: "Long ctx" },
  { id: "gemma2-9b-it",             label: "Gemma 2 9B",     badge: "Light"    },
];

const PERSONAS = [
  { id: "female", label: "Sarah", icon: "👩" },
  { id: "male",   label: "Alex",  icon: "👨" },
] as const;

const SUGGESTIONS = [
  { label: "Summary", icon: Zap },
  { label: "Code",    icon: Code2 },
  { label: "Design",  icon: Palette },
  { label: "Search",  icon: Globe },
];

export function InputArea() {
  const { 
    sendMessage, 
    isSending, 
    persona, 
    setPersona, 
    toggleListening, 
    isListening,
    isSpeaking,
    isChecking
  } = useNexus();

  const [inputValue, setInputValue]       = useState("");
  const [modelOpen, setModelOpen]         = useState(false);
  const [selectedModel, setSelectedModel] = useState(MODELS[0]);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);



  /* Auto-grow textarea */
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [inputValue]);


  /* Close dropdown on outside click */
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setModelOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleSend = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!inputValue.trim() || isSending) return;
    const content = inputValue;
    setInputValue("");
    await sendMessage({ content, model: selectedModel.id });
    
    // Immediate focus after state clear
    textareaRef.current?.focus();
    
    // Delayed focus after any layout shifts or re-renders
    setTimeout(() => {
        textareaRef.current?.focus();
    }, 100);
  };

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const fillSuggestion = (label: string) => {
    setInputValue(label + ": ");
    textareaRef.current?.focus();
  };

  return (
    <div className="w-full flex flex-col gap-2">
      {/* Main input card */}
      <div className="rounded-2xl border border-white/10 bg-black/50 backdrop-blur-xl overflow-visible focus-within:border-indigo-500/40 transition-colors relative">
        {/* Textarea */}
        <textarea
          ref={textareaRef}
          rows={1}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Ask me anything…"
          className="w-full bg-transparent px-4 pt-3.5 pb-2 text-[13px] text-white placeholder:text-zinc-600 resize-none outline-none leading-relaxed min-h-[44px] max-h-[160px] overflow-y-auto scroll-hide"
        />

        {/* Bottom toolbar */}
        <div className="flex items-center justify-between px-3 pb-2.5 pt-1">
          {/* Left: attach + model dropdown */}
          <div className="flex items-center gap-2">
            <button
              className="text-zinc-600 hover:text-zinc-300 transition-colors p-1"
              title="Attach file"
            >
              <Paperclip size={14} />
            </button>

            {/* Model selector */}
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => setModelOpen((v) => !v)}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/5 hover:bg-white/10 border border-white/5 transition-colors text-[10px] font-semibold text-zinc-400 hover:text-zinc-200"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 shrink-0" />
                <span>{selectedModel.label}</span>
                <ChevronDown
                  size={10}
                  className={`text-zinc-600 transition-transform ${modelOpen ? "rotate-180" : ""}`}
                />
              </button>

              {modelOpen && (
                <div className="absolute bottom-full mb-2 left-0 w-52 rounded-xl border border-white/10 bg-[#0d0d10] shadow-2xl shadow-black/60 overflow-hidden z-50">
                  <div className="px-3 py-2 border-b border-white/5">
                    <span className="text-[9px] font-black text-zinc-600 uppercase tracking-widest">
                      Select Model
                    </span>
                  </div>
                  {MODELS.map((m) => (
                    <button
                      key={m.id}
                      onClick={() => { setSelectedModel(m); setModelOpen(false); }}
                      className="w-full flex items-center justify-between px-3 py-2 hover:bg-white/5 transition-colors group"
                    >
                      <div className="flex items-center gap-2.5">
                        {selectedModel.id === m.id
                          ? <Check size={11} className="text-indigo-400 shrink-0" />
                          : <span className="w-[11px] shrink-0" />
                        }
                        <span className="text-[11px] font-semibold text-zinc-300 group-hover:text-white transition-colors">
                          {m.label}
                        </span>
                      </div>
                      <span className="text-[9px] font-bold text-zinc-600 bg-white/5 px-1.5 py-0.5 rounded-full">
                        {m.badge}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Persona Switcher */}
            <div className="flex items-center gap-1 p-1 bg-white/5 rounded-full border border-white/5">
              {PERSONAS.map((p) => (
                <button
                  key={p.id}
                  onClick={() => setPersona(p.id)}
                  className={`px-3 py-1 rounded-full text-[9px] font-bold transition-all ${
                    persona === p.id 
                      ? 'bg-indigo-500 text-white shadow-lg' 
                      : 'text-zinc-500 hover:text-zinc-300'
                  }`}
                >
                  <span className="mr-1">{p.icon}</span>
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Right: mic + send */}
          <div className="flex items-center gap-2">
            <button
              onClick={toggleListening}
              className={`transition-all p-1.5 rounded-full ${
                isChecking
                  ? "text-zinc-400 bg-zinc-500/10"
                  : isSpeaking
                  ? "text-emerald-400 bg-emerald-500/10 shadow-[0_0_15px_rgba(52,211,153,0.2)]"
                  : isListening 
                  ? "text-indigo-400 bg-indigo-500/10 shadow-[0_0_15px_rgba(99,102,241,0.2)]" 
                  : "text-red-400 bg-red-500/10 shadow-[0_0_10px_rgba(248,113,113,0.1)] hover:bg-red-500/20"
              }`}
              title={isListening ? "Stop listening" : "Voice input"}
            >
              {isChecking ? (
                <Loader2 size={14} className="animate-spin" />
              ) : isSpeaking ? (
                <Volume2 size={14} className="animate-pulse" />
              ) : isListening ? (
                <Mic size={14} className="animate-pulse" />
              ) : (
                <MicOff size={14} />
              )}
            </button>
            <button
              onClick={handleSend}
              disabled={!inputValue.trim() || isSending}
              className="w-7 h-7 rounded-full bg-indigo-600 hover:bg-indigo-500 disabled:bg-white/10 disabled:text-zinc-600 text-white flex items-center justify-center transition-all active:scale-90 shadow-lg shadow-indigo-500/20 disabled:shadow-none"
              title="Send"
            >
              <ArrowUp size={13} />
            </button>
          </div>
        </div>
      </div>

      {/* Suggestion pills */}
      <div className="flex gap-1.5 flex-wrap">
        {SUGGESTIONS.map(({ label, icon: Icon }) => (
          <button
            key={label}
            onClick={() => fillSuggestion(label)}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-white/8 bg-white/[0.04] hover:bg-white/[0.08] text-zinc-500 hover:text-zinc-200 text-[10px] font-semibold transition-all"
          >
            <Icon size={10} />
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}
