"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { Sidebar } from "@/components/Sidebar";
import { InputArea } from "@/components/InputArea";
import { useNexusVoice } from "@/hooks/useNexusVoice";
import { PanelRight } from "lucide-react";

import { Skeleton } from 'boneyard-js/react';
const NexusOrb = dynamic(() => import("@/components/NexusOrb").then(mod => ({ default: mod.NexusOrb })), { ssr: false });

const getGreeting = () => {
  const hour = new Date().getHours();
  if (hour < 12) return "Good Morning";
  if (hour < 18) return "Good Afternoon";
  return "Good Evening";
};

export default function Home() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [uiMode, setUiMode] = useState<'voice' | 'chat'>('voice');
  const { isListening, isMuted, volume, toggleListening, toggleMute } = useNexusVoice();

  const greeting = getGreeting();

  return (
    <div className="flex h-screen bg-neutral-950 text-white overflow-hidden font-sans">
      <Sidebar isOpen={isSidebarOpen} toggle={() => setIsSidebarOpen(!isSidebarOpen)} />
      
      <main className="flex-1 flex flex-col relative z-0 h-full overflow-hidden">
        {!isSidebarOpen && (
          <button 
            onClick={() => setIsSidebarOpen(true)}
            className="absolute top-4 left-4 z-50 p-2 text-neutral-400 hover:text-white bg-neutral-900/50 hover:bg-neutral-800 rounded-lg transition-colors backdrop-blur-md border border-white/5"
          >
            <PanelRight size={20} />
          </button>
        )}

        <div className="flex-1 flex flex-col relative overflow-hidden">
          <section className="flex-1 flex flex-col items-center justify-center relative min-h-0 px-4 transition-all duration-300 ease-in-out -translate-y-12">
            
            {/* Orb Container - Only visible in Voice Mode */}
            <div className={`w-full max-w-[380px] aspect-square pointer-events-none shrink-0 flex items-center justify-center relative transition-all duration-300 ${uiMode === 'voice' ? 'opacity-100 scale-100' : 'opacity-0 scale-95 h-0 pointer-events-none overflow-hidden'}`}>
              {/* Radial glow background */}
              <div className="absolute inset-0 bg-blue-500/5 rounded-full blur-[100px] pointer-events-none" />
              <NexusOrb isListening={isListening} volume={volume} />
            </div>

            {/* Greeting Text - Adjusted for Vertical Balance */}
            <Skeleton name="greeting" loading={false}>
              <div className={`relative z-10 text-center pointer-events-none max-w-2xl transition-all duration-300 ${uiMode === 'voice' ? 'mt-10 opacity-100' : 'opacity-0 h-0 overflow-hidden translate-y-4'}`}>
                <h1 className="text-4xl md:text-5xl font-bold mb-3 tracking-tight bg-clip-text text-transparent bg-gradient-to-b from-white to-white/50">
                  {greeting}
                </h1>
                <h2 className="text-lg md:text-xl text-neutral-400 font-light tracking-wide">
                  How can I <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-purple-400 to-pink-400 font-medium">assist you today?</span>
                </h2>
              </div>
            </Skeleton>

            {/* Voice Action Bar - Mic Controls */}
            {isListening && (
              <div className="mt-8 flex items-center gap-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
                <button 
                  onClick={toggleMute}
                  className={`p-4 rounded-full transition-all duration-300 backdrop-blur-xl border ${
                    isMuted 
                      ? "bg-red-500/20 border-red-500/30 text-red-400" 
                      : "bg-white/5 border-white/10 text-white hover:bg-white/10"
                  }`}
                >
                  <div className="relative">
                    {isMuted ? (
                      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="1" y1="1" x2="23" y2="23"></line><path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6"></path><path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2a7 7 0 0 1-1.14 3.73"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>
                    ) : (
                      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>
                    )}
                  </div>
                </button>
                <button 
                  onClick={toggleListening}
                  className="px-6 py-3 bg-red-500 hover:bg-red-600 text-white rounded-full font-bold text-xs uppercase tracking-widest transition-all hover:shadow-[0_0_20px_rgba(239,68,68,0.4)] active:scale-95"
                >
                  End Session
                </button>
              </div>
            )}
            
          </section>

          <InputArea 
            isListening={isListening} 
            toggleListening={toggleListening} 
            uiMode={uiMode} 
            setUiMode={setUiMode}
          />
        </div>
      </main>
    </div>
  );
}
