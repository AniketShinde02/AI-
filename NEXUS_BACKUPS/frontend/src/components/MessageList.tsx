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
      <div className="flex-1 flex flex-col items-center justify-center text-zinc-500 opacity-50">
        <Sparkles size={48} className="mb-4 text-indigo-400 animate-pulse" />
        <p className="text-[10px] font-bold tracking-widest uppercase">Start a conversation</p>
      </div>
    );
  }

  return (
    <div 
      ref={scrollRef}
      className="flex-1 min-h-0 overflow-y-auto p-4 space-y-6 scroll-hide"
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
              <div className="space-y-2 flex flex-col items-end">
                <div className="flex items-center gap-2">
                    <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-widest">Aniket</span>
                    <div className="w-5 h-5 rounded-lg bg-white/5 flex items-center justify-center border border-white/10">
                        <User size={10} className="text-zinc-400" />
                    </div>
                </div>
                <div className="px-4 py-2.5 rounded-2xl rounded-tr-none bg-indigo-600/10 border border-indigo-500/20 text-[13px] text-white leading-relaxed max-w-[90%]">
                    {message.content}
                </div>
              </div>
            ) : (
              message.content?.trim() ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                      <div className="w-5 h-5 rounded-lg bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20">
                          <Sparkles size={10} className="text-indigo-400" />
                      </div>
                      <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-widest">Nexus Core</span>
                  </div>
                  <div className="px-4 py-2.5 rounded-2xl rounded-tl-none bg-white/[0.03] border border-white/5 text-[13px] text-zinc-300 leading-relaxed max-w-[85%] whitespace-pre-wrap">
                      {message.content}
                  </div>
                </div>
              ) : null
            )}
          </motion.div>
        ))}
        
        {isSending && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex justify-start w-full"
          >
            <div className="space-y-2">
                <div className="flex items-center gap-2">
                    <div className="w-5 h-5 rounded-lg bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20">
                        <Sparkles size={10} className="text-indigo-400 animate-pulse" />
                    </div>
                    <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-widest">Nexus Core</span>
                </div>
                <div className="px-4 py-3 rounded-2xl rounded-tl-none bg-white/[0.03] border border-white/5 text-[13px] text-zinc-300 leading-relaxed flex gap-1">
                  {[0, 1, 2].map((i) => (
                    <motion.div
                      key={i}
                      animate={{ 
                        scale: [1, 1.2, 1],
                        opacity: [0.3, 1, 0.3] 
                      }}
                      transition={{ 
                        repeat: Infinity, 
                        duration: 1, 
                        delay: i * 0.2 
                      }}
                      className="w-1.5 h-1.5 bg-indigo-400 rounded-full"
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
