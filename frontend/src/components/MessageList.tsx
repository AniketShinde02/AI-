"use client";

import { useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useNexus } from "@/contexts/NexusContext";
import { User, Sparkles } from "lucide-react";

export function MessageList() {
  const { messages, isSending } = useNexus();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isSending]);

  if (messages.length === 0 && !isSending) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center relative z-10 opacity-60">
        <div className="relative flex flex-col items-center">
          <div className="w-12 h-12 border border-[#6137FF]/40 rotate-45 flex items-center justify-center shadow-[inset_0_0_20px_rgba(97,55,255,0.2)] mb-8 clip-cut-sm relative">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(97,55,255,0.2)_0%,transparent_100%)]"></div>
            <div className="w-4 h-4 border border-[#00FFFF]/50 -rotate-45 flex items-center justify-center bg-black/50 shadow-[0_0_15px_rgba(0,255,255,0.2)]">
              <div className="w-1.5 h-1.5 bg-[#00FFFF] animate-pulse shadow-[0_0_10px_#00FFFF]"></div>
            </div>
          </div>
          <p className="text-[10px] font-quantico font-bold text-zinc-500 tracking-[0.4em] uppercase drop-shadow-md">Awaiting Directive</p>
        </div>
      </div>
    );
  }

  return (
    <div 
      ref={scrollRef}
      className="flex-1 min-h-0 overflow-y-auto p-4 space-y-6 scroll-hide relative z-10"
    >
      <AnimatePresence initial={false}>
        {messages.map((message, index) => (
          <motion.div
            key={message.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className={`w-full flex flex-col ${message.role === "user" ? "items-end" : "items-start"}`}
          >
            {message.role === "user" ? (
              <div className="space-y-2 flex flex-col items-end max-w-[90%]">
                <div className="flex items-center gap-2">
                    <span className="text-[9px] font-quantico font-bold text-[#6137FF] uppercase tracking-[0.2em] drop-shadow-[0_0_5px_#6137FF]">Aniket</span>
                    <div className="w-5 h-5 bg-black border border-[#6137FF]/40 flex items-center justify-center clip-cut-sm shadow-[inset_0_0_10px_rgba(97,55,255,0.2)]">
                        <User size={10} className="text-white" />
                    </div>
                </div>
                <div className="px-4 py-3 bg-[#6137FF]/10 border border-[#6137FF]/30 text-[12px] font-mono text-white leading-relaxed clip-cut shadow-[0_0_15px_rgba(97,55,255,0.15)] relative">
                    <div className="absolute top-0 right-0 w-2 h-2 border-t border-r border-[#6137FF]"></div>
                    <div className="absolute bottom-0 left-0 w-2 h-2 border-b border-l border-[#6137FF]"></div>
                    {message.content}
                </div>
              </div>
            ) : (
              message.content?.trim() ? (() => {
                const displayContent = message.content
                  .replace(/<think>[\s\S]*?<\/think>/gi, '') // Remove completed think blocks
                  .replace(/<think>[\s\S]*$/gi, '')          // Remove incomplete think blocks
                  .replace(/\*\*[\s\S]*?\*\*/g, '')          // Remove completed asterisk blocks
                  .replace(/\*\*[\s\S]*$/, '')               // Remove incomplete asterisk blocks at the end
                  .trim();
                
                if (!displayContent) return null; // Don't show empty bubbles if it's currently just thinking
                
                return (
                <div className="space-y-2 max-w-[90%]">
                  <div className="flex items-center gap-2">
                      <div className="w-5 h-5 bg-black border border-[#6137FF]/40 flex items-center justify-center clip-cut-sm shadow-[inset_0_0_10px_rgba(97,55,255,0.2)]">
                          <div className="w-1.5 h-1.5 bg-[#6137FF] transform rotate-45 shadow-[0_0_8px_#6137FF]"></div>
                      </div>
                      <span className="text-[9px] font-quantico font-bold text-[#6137FF] uppercase tracking-[0.2em] drop-shadow-[0_0_5px_#6137FF]">System</span>
                  </div>
                  <div className="px-4 py-3 bg-[#06060c] border border-white/10 hover:border-[#00FFFF]/30 transition-colors text-[12px] font-mono text-zinc-300 leading-relaxed whitespace-pre-wrap clip-cut shadow-[0_0_15px_rgba(0,0,0,0.5)] relative">
                      <div className="absolute top-0 left-0 w-2 h-2 border-t border-l border-[#00FFFF]/50"></div>
                      <div className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-[#00FFFF]/50"></div>
                      {displayContent}
                  </div>
                </div>
              );
              })() : null
            )}
          </motion.div>
        ))}
        
        {isSending && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex justify-start w-full max-w-[90%]"
          >
            <div className="space-y-2">
                <div className="flex items-center gap-2">
                    <div className="w-5 h-5 bg-black border border-[#6137FF]/40 flex items-center justify-center clip-cut-sm shadow-[inset_0_0_10px_rgba(97,55,255,0.2)]">
                        <div className="w-1.5 h-1.5 bg-[#6137FF] animate-pulse transform rotate-45 shadow-[0_0_8px_#6137FF]"></div>
                    </div>
                    <span className="text-[9px] font-quantico font-bold text-[#6137FF] uppercase tracking-[0.2em] drop-shadow-[0_0_5px_#6137FF]">System</span>
                </div>
                <div className="px-4 py-4 bg-[#06060c] border border-white/10 text-[12px] text-zinc-300 flex gap-2 clip-cut shadow-[0_0_15px_rgba(0,0,0,0.5)]">
                  {[0, 1, 2].map((i) => (
                    <motion.div
                      key={i}
                      animate={{ 
                        scale: [1, 1.5, 1],
                        opacity: [0.3, 1, 0.3],
                        backgroundColor: ["#6137FF", "#00FFFF", "#6137FF"]
                      }}
                      transition={{ 
                        repeat: Infinity, 
                        duration: 1.5, 
                        delay: i * 0.2 
                      }}
                      className="w-1.5 h-1.5 transform rotate-45 shadow-[0_0_5px_currentColor]"
                    />
                  ))}
                </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
