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
  { id: "mistral-large-latest",     label: "Mistral Large",  badge: "Mistral"  },
  { id: "pixtral-large-2411",       label: "Pixtral Large",  badge: "Mistral"  },
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
  const [isFocused, setIsFocused]         = useState(false);

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
    <div className="w-full flex flex-col gap-3 relative z-20">
      {/* Main input card */}
      <div className="border border-white/10 bg-[#06060c] overflow-visible focus-within:border-[#00FFFF]/40 transition-colors relative clip-cut-sm shadow-[0_0_20px_rgba(0,0,0,0.8)]">
        {/* Corner glowing accents */}
        <div className="absolute top-0 left-0 w-4 h-4 border-t border-l border-[#00FFFF]/50 pointer-events-none"></div>
        <div className="absolute bottom-0 right-0 w-4 h-4 border-b border-r border-[#6137FF]/50 pointer-events-none"></div>

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          rows={1}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKey}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setTimeout(() => setIsFocused(false), 200)}
          placeholder="Awaiting Directive…"
          className="w-full bg-transparent px-4 pt-4 pb-2 text-[12px] font-mono text-white placeholder:text-zinc-600 resize-none outline-none leading-relaxed min-h-[44px] max-h-[160px] overflow-y-auto scroll-hide uppercase tracking-wide"
        />

        {/* Bottom toolbar */}
        <div className="flex items-center justify-between px-3 pb-3 pt-2">
          {/* Left: attach + model dropdown */}
          <div className="flex items-center gap-3">
            <button
              className="text-zinc-600 hover:text-[#00FFFF] transition-colors p-1"
              title="Attach file"
            >
              <Paperclip size={14} />
            </button>

            {/* Model selector */}
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => setModelOpen((v) => !v)}
                className="flex items-center gap-2 px-3 py-1.5 bg-black hover:bg-[#6137FF]/20 border border-white/10 hover:border-[#6137FF]/50 transition-colors text-[9px] font-quantico font-bold text-zinc-400 hover:text-white uppercase tracking-[0.2em] clip-cut-sm shadow-[inset_0_0_10px_rgba(97,55,255,0.1)]"
              >
                <span className="w-1.5 h-1.5 bg-[#00FFFF] shadow-[0_0_5px_#00FFFF] shrink-0 transform rotate-45" />
                <span>{selectedModel.label}</span>
                <ChevronDown
                  size={12}
                  className={`text-[#6137FF] transition-transform ${modelOpen ? "rotate-180" : ""}`}
                />
              </button>

              {modelOpen && (
                <div className="absolute bottom-full mb-3 left-0 w-56 border border-[#6137FF]/40 bg-[#06060c] shadow-[0_0_30px_rgba(0,0,0,0.9)] overflow-hidden z-50 clip-cut">
                  <div className="px-4 py-3 border-b border-white/5 bg-black/50">
                    <span className="text-[9px] font-quantico font-bold text-[#6137FF] uppercase tracking-[0.3em]">
                      Neural_Model_Select
                    </span>
                  </div>
                  <div className="p-1">
                    {MODELS.map((m) => (
                      <button
                        key={m.id}
                        onClick={() => { setSelectedModel(m); setModelOpen(false); }}
                        className="w-full flex items-center justify-between px-3 py-2.5 hover:bg-[#00FFFF]/10 border border-transparent hover:border-[#00FFFF]/30 transition-all group clip-cut-sm"
                      >
                        <div className="flex items-center gap-3">
                          {selectedModel.id === m.id
                            ? <Check size={12} className="text-[#00FFFF] drop-shadow-[0_0_5px_#00FFFF] shrink-0" />
                            : <span className="w-[12px] shrink-0" />
                          }
                          <span className="text-[10px] font-quantico font-bold tracking-[0.1em] text-zinc-400 group-hover:text-white transition-colors uppercase">
                            {m.label}
                          </span>
                        </div>
                        <span className="text-[8px] font-bold text-black bg-[#6137FF] px-2 py-0.5 uppercase tracking-widest clip-cut-sm">
                          {m.badge}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Persona Switcher */}
            <div className="flex items-center gap-1 p-1 bg-black border border-white/10 clip-cut-sm">
              {PERSONAS.map((p) => (
                <button
                  key={p.id}
                  onClick={() => setPersona(p.id)}
                  className={`px-3 py-1 text-[9px] font-quantico font-bold uppercase tracking-[0.2em] transition-all clip-cut-sm ${
                    persona === p.id 
                      ? 'bg-[#00FFFF] text-black shadow-[0_0_10px_#00FFFF]' 
                      : 'text-zinc-500 hover:text-white hover:bg-white/5'
                  }`}
                >
                  <span className="mr-1.5">{p.icon}</span>
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Right: mic + send */}
          <div className="flex items-center gap-3">
            <button
              onClick={toggleListening}
              className={`transition-all p-2 clip-cut-sm border ${
                isChecking
                  ? "text-zinc-400 bg-zinc-500/10 border-zinc-500/30"
                  : isSpeaking
                  ? "text-[#00FFFF] bg-[#00FFFF]/10 border-[#00FFFF]/50 shadow-[0_0_15px_rgba(0,255,255,0.3)]"
                  : isListening 
                  ? "text-[#ff3366] bg-[#ff3366]/10 border-[#ff3366]/50 shadow-[0_0_15px_rgba(255,51,102,0.3)]" 
                  : "text-zinc-500 bg-black/50 border-white/10 hover:border-[#6137FF]/50 hover:text-white"
              }`}
              title={isListening ? "Stop listening" : "Voice input"}
            >
              {isChecking ? (
                <Loader2 size={16} className="animate-spin" />
              ) : isSpeaking ? (
                <Volume2 size={16} className="animate-pulse" />
              ) : isListening ? (
                <Mic size={16} className="animate-pulse" />
              ) : (
                <MicOff size={16} />
              )}
            </button>
            <button
              onClick={handleSend}
              disabled={!inputValue.trim() || isSending}
              className="w-9 h-9 bg-[#6137FF] hover:bg-[#00FFFF] disabled:bg-black disabled:border disabled:border-white/10 disabled:text-zinc-600 text-white hover:text-black flex items-center justify-center transition-all active:scale-95 shadow-[0_0_15px_rgba(97,55,255,0.4)] disabled:shadow-none clip-cut-sm"
              title="Send"
            >
              <ArrowUp size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* Suggestion pills - ONLY show if focused or has text */}
      {(isFocused || inputValue.trim().length > 0) && (
        <div className="flex gap-2 flex-wrap px-1 animate-in fade-in slide-in-from-top-2 duration-200">
          {SUGGESTIONS.map(({ label, icon: Icon }) => (
            <button
              key={label}
              onClick={() => fillSuggestion(label)}
              className="flex items-center gap-2 px-3 py-1.5 border border-white/10 bg-black/40 hover:bg-[#6137FF]/20 hover:border-[#6137FF]/50 text-zinc-500 hover:text-white text-[9px] font-quantico font-bold uppercase tracking-[0.2em] transition-all clip-cut-sm"
            >
              <Icon size={12} className="text-[#00FFFF]" />
              {label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
