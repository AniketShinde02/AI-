import { useState, useEffect, useRef } from "react";
import { Paperclip, Globe, ChevronDown, Mic, ArrowUp, FileText, Code, Palette, Search } from "lucide-react";
import { useDebounce } from "@/hooks/useDebounce";
import { useNexusChat } from "@/hooks/useNexusChat";
import { apiClient } from "@/lib/api-client";
import { useFeature } from "@/lib/features";
import { useQuery } from "@tanstack/react-query";

interface InputAreaProps {
  isListening: boolean; 
  toggleListening: () => void;
  uiMode: 'voice' | 'chat';
  setUiMode: (mode: 'voice' | 'chat') => void;
}

/**
 * Nexus Production Input Area
 * Implements:
 * - Rule #4: Debouncing & Throttling
 * - Rule #5: Optimistic Updates
 * - Rule #6: Feature Flags
 */
export function InputArea({ 
  isListening, 
  toggleListening, 
  uiMode, 
  setUiMode 
}: InputAreaProps) {
  const [inputValue, setInputValue] = useState("");
  const debouncedInput = useDebounce(inputValue, 500);
  const { sendMessage, isSending } = useNexusChat();
  const showSuggestions = useFeature('ai-suggestions');

  // Intelligent Suggestions with Rule #4 (Cancellation)
  const { data: suggestions, isLoading: isSearching } = useQuery({
    queryKey: ['suggestions', debouncedInput],
    queryFn: async ({ signal }) => {
      if (!debouncedInput || !showSuggestions) return [];
      return apiClient.get<string[]>('/api/suggestions', { 
        params: { q: debouncedInput },
        signal 
      });
    },
    enabled: !!debouncedInput && showSuggestions && debouncedInput.length > 2,
  });

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value);
  };

  const handleSendMessage = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!inputValue.trim() || isSending) return;
    
    sendMessage(inputValue);
    setInputValue("");
    if (uiMode === 'voice') setUiMode('chat');
  };

  return (
    <footer className="w-full max-w-4xl mx-auto mt-auto px-4 pb-10 transition-all duration-300">
      {uiMode === 'chat' ? (
        <>
          <div className="bg-neutral-900/80 border border-white/5 rounded-2xl p-4 flex flex-col shadow-2xl transition-all duration-300 backdrop-blur-md">
            <div className="relative">
              <textarea 
                value={inputValue}
                onChange={handleInputChange}
                placeholder="Ask me anything..." 
                className="w-full bg-transparent text-white resize-none border-none focus:outline-none py-3 placeholder:text-neutral-500"
                rows={1}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
              />
              
              {isSearching && (
                <div className="absolute right-0 top-0 flex items-center gap-1.5 p-2 animate-pulse">
                  <div className="w-1.5 h-1.5 bg-cyan-500 rounded-full" />
                  <span className="text-[10px] text-neutral-500 uppercase tracking-widest font-bold">Analysing...</span>
                </div>
              )}

              <div className="flex items-center justify-between mt-2">
                <div className="flex items-center gap-2">
                  <button className="p-2 text-neutral-400 hover:text-white rounded-full hover:bg-neutral-800 transition-colors">
                    <Paperclip size={18} />
                  </button>
                  <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-neutral-400 bg-neutral-800 rounded-full hover:text-white hover:bg-neutral-700 transition-colors">
                    <Globe size={14} />
                    <span>Claude 3.5 Sonnet</span>
                    <ChevronDown size={14} />
                  </button>
                  
                  <div className="flex items-center gap-1 ml-2 bg-neutral-950 rounded-full p-0.5 border border-neutral-800">
                    <button 
                      onClick={() => setUiMode('chat')}
                      className={`px-3 py-1 text-[10px] font-bold uppercase tracking-wider rounded-full transition-all ${uiMode === 'chat' ? "bg-neutral-800 text-white shadow-sm" : "text-neutral-500 hover:text-neutral-300"}`}
                    >
                      Chat
                    </button>
                    <button 
                      onClick={() => setUiMode('voice')}
                      className="px-3 py-1 text-[10px] font-bold uppercase tracking-wider rounded-full transition-all text-neutral-500 hover:text-neutral-300"
                    >
                      Voice
                    </button>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button 
                    onClick={toggleListening}
                    className={`p-2 rounded-full transition-all ${
                      isListening 
                        ? "bg-pink-600/20 text-pink-500 shadow-[0_0_15px_rgba(219,39,119,0.2)]" 
                        : "bg-neutral-800/50 text-neutral-400 hover:text-white hover:bg-neutral-700"
                    }`}
                  >
                    <Mic size={16} />
                  </button>
                  <button 
                    disabled={isSending}
                    onClick={handleSendMessage}
                    className={`p-2 rounded-full transition-all ${isSending ? "bg-neutral-800 text-neutral-600" : "bg-white text-black hover:bg-neutral-200"}`}
                  >
                    <ArrowUp size={16} className={isSending ? "animate-pulse" : ""} />
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-3 mt-4 transition-all duration-300">
            <button className="flex items-center gap-2 px-4 py-2 text-sm text-neutral-400 bg-neutral-900 border border-neutral-800 rounded-full hover:text-white hover:border-neutral-600 transition-all">
              <FileText size={16} /> Summary
            </button>
            <button className="flex items-center gap-2 px-4 py-2 text-sm text-neutral-400 bg-neutral-900 border border-neutral-800 rounded-full hover:text-white hover:border-neutral-600 transition-all">
              <Code size={16} /> Code
            </button>
            <button className="flex items-center gap-2 px-4 py-2 text-sm text-neutral-400 bg-neutral-900 border border-neutral-800 rounded-full hover:text-white hover:border-neutral-600 transition-all">
              <Palette size={16} /> Design
            </button>
            <button className="flex items-center gap-2 px-4 py-2 text-sm text-neutral-400 bg-neutral-900 border border-neutral-800 rounded-full hover:text-white hover:border-neutral-600 transition-all">
              <Search size={16} /> Research
            </button>
          </div>
        </>
      ) : (
        <div className="flex flex-col items-center gap-10 transition-all duration-300">
          <div className="flex flex-col items-center gap-3">
            <button 
              onClick={toggleListening}
              className={`relative transition-all duration-300 ${
                isListening 
                  ? "text-pink-500 scale-110" 
                  : "text-neutral-500 hover:text-white scale-100"
              }`}
            >
              <Mic size={20} className={isListening ? 'animate-pulse' : ''} />
              {isListening && (
                <div className="absolute inset-0 -m-3 rounded-full border border-pink-500/20 animate-ping" />
              )}
            </button>
            <span className={`text-[9px] font-bold uppercase tracking-[0.4em] transition-opacity duration-300 ${isListening ? 'opacity-100 text-pink-500/60' : 'opacity-30 text-neutral-500'}`}>
              {isListening ? 'Listening' : 'Tap to Speak'}
            </span>
          </div>
          
          <button 
            onClick={() => setUiMode('chat')}
            className="group flex items-center gap-2 text-neutral-700 hover:text-neutral-400 transition-all duration-300"
          >
            <span className="text-[9px] font-bold uppercase tracking-[0.2em]">Switch to Chat</span>
            <ChevronDown size={12} className="rotate-180 group-hover:-translate-y-0.5 transition-transform" />
          </button>
        </div>
      )}
    </footer>
  );
}
