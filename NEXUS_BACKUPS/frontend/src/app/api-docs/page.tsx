'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { 
  Zap, 
  MessageSquare, 
  Mic, 
  Shield, 
  Code, 
  Globe, 
  Database,
  ArrowRight,
  ExternalLink,
  ChevronRight
} from 'lucide-react';

/**
 * Nexus API Documentation Page
 * Designed to be premium, readable, and technical.
 */
export default function ApiDocs() {
  const procedures = [
    {
      name: 'getSuggestions',
      type: 'Query',
      description: 'Fetch AI-powered search and chat suggestions based on user input.',
      input: '{ q: string }',
      output: 'string[]',
      icon: <Zap className="text-amber-400" size={20} />
    },
    {
      name: 'chat',
      type: 'Mutation',
      description: 'Core text-based AI interaction endpoint using Groq/OpenAI providers.',
      input: '{ content: string, userId?: string, model?: string }',
      output: '{ id: string, role: "assistant", content: string, timestamp: number }',
      icon: <MessageSquare className="text-blue-400" size={20} />
    },
    {
      name: 'getVoiceSession',
      type: 'Mutation',
      description: 'Initialize a WebRTC voice session with a Nexus AI Agent via Stream.io.',
      input: '{ userId: string, agentType: string }',
      output: '{ sessionId: string, callType: string, agentId: string }',
      icon: <Mic className="text-purple-400" size={20} />
    }
  ];

  return (
    <div className="min-h-screen bg-[#000000] text-white p-8 md:p-12 overflow-y-auto custom-scrollbar">
      {/* Header */}
      <header className="max-w-5xl mx-auto mb-16">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-3 mb-4"
        >
          <div className="px-3 py-1 bg-nexus-cyan/10 border border-nexus-cyan/20 rounded-full text-nexus-cyan text-xs font-mono uppercase tracking-widest">
            v1.0.0
          </div>
          <span className="text-neutral-500 text-xs font-mono">Nexus Core API</span>
        </motion.div>
        
        <motion.h1 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="text-5xl md:text-6xl font-bold mb-6 tracking-tight bg-gradient-to-r from-white to-neutral-500 bg-clip-text text-transparent"
        >
          Developer Documentation
        </motion.h1>
        
        <motion.p 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="text-xl text-neutral-400 max-w-2xl leading-relaxed"
        >
          Explore the Nexus AI ecosystem. Our tRPC-powered API provides type-safe access to multimodal intelligence, voice streaming, and knowledge graph operations.
        </motion.p>
      </header>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto space-y-24 pb-24">
        
        {/* Architecture Section */}
        <section>
          <div className="flex items-center gap-4 mb-8">
            <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center border border-white/10">
              <Shield className="text-emerald-400" size={20} />
            </div>
            <h2 className="text-2xl font-semibold">Core Architecture</h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-6 rounded-2xl bg-neutral-900/50 border border-white/5 hover:border-white/10 transition-colors">
              <Code className="text-blue-400 mb-4" size={24} />
              <h3 className="font-semibold mb-2">Type Safety</h3>
              <p className="text-sm text-neutral-400">End-to-end type safety powered by tRPC and Zod. No manual API contract synchronization needed.</p>
            </div>
            <div className="p-6 rounded-2xl bg-neutral-900/50 border border-white/5 hover:border-white/10 transition-colors">
              <Globe className="text-purple-400 mb-4" size={24} />
              <h3 className="font-semibold mb-2">Edge Ready</h3>
              <p className="text-sm text-neutral-400">Optimized for low-latency voice streaming and high-concurrency LLM interactions at the edge.</p>
            </div>
            <div className="p-6 rounded-2xl bg-neutral-900/50 border border-white/5 hover:border-white/10 transition-colors">
              <Database className="text-nexus-cyan mb-4" size={24} />
              <h3 className="font-semibold mb-2">Stateful AI</h3>
              <p className="text-sm text-neutral-400">Integrated persistence layer for chat history and real-time session synchronization.</p>
            </div>
          </div>
        </section>

        {/* Procedures List */}
        <section>
          <div className="flex items-center gap-4 mb-8">
            <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center border border-white/10">
              <Code className="text-nexus-cyan" size={20} />
            </div>
            <h2 className="text-2xl font-semibold">API Procedures</h2>
          </div>

          <div className="space-y-4">
            {procedures.map((proc, idx) => (
              <motion.div 
                key={proc.name}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + (idx * 0.1) }}
                className="group p-6 rounded-2xl bg-neutral-900/30 border border-white/5 hover:border-nexus-cyan/30 hover:bg-nexus-cyan/[0.02] transition-all"
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center group-hover:bg-nexus-cyan/10 transition-colors">
                      {proc.icon}
                    </div>
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="text-lg font-mono font-bold">{proc.name}</h3>
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-mono uppercase ${
                          proc.type === 'Query' ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' : 'bg-orange-500/10 text-orange-400 border border-orange-500/20'
                        }`}>
                          {proc.type}
                        </span>
                      </div>
                      <p className="text-sm text-neutral-400">{proc.description}</p>
                    </div>
                  </div>
                  <div className="flex flex-col gap-2 font-mono text-[11px] md:text-right">
                    <div className="text-neutral-500">
                      <span className="text-white/50">INPUT:</span> {proc.input}
                    </div>
                    <div className="text-neutral-500">
                      <span className="text-white/50">OUTPUT:</span> {proc.output}
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </section>

        {/* Event System Documentation */}
        <section>
          <div className="flex items-center gap-4 mb-8">
            <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center border border-white/10">
              <Zap className="text-amber-400" size={20} />
            </div>
            <h2 className="text-2xl font-semibold">Event System (SDK)</h2>
          </div>

          <div className="mb-12 p-8 rounded-3xl bg-gradient-to-r from-neutral-900 to-black border border-white/5">
            <div className="flex flex-col md:flex-row gap-8 items-start">
              <div className="flex-1">
                <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
                  <Shield className="text-nexus-cyan" size={18} />
                  The Truth Engine
                </h3>
                <p className="text-neutral-400 text-sm leading-relaxed mb-6">
                  Nexus AI utilizes a high-performance, priority-queued event system for internal state management. 
                  Developers can subscribe to specific event types to hook into the AI's cognitive, perceptual, and synthesis loops.
                </p>
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 rounded-xl bg-white/5 border border-white/5">
                    <div className="text-[10px] text-nexus-cyan font-mono mb-1 uppercase tracking-wider">Base Class</div>
                    <div className="text-sm font-mono font-semibold">BaseEvent</div>
                  </div>
                  <div className="p-4 rounded-xl bg-white/5 border border-white/5">
                    <div className="text-[10px] text-purple-400 font-mono mb-1 uppercase tracking-wider">Plugin Core</div>
                    <div className="text-sm font-mono font-semibold">PluginBaseEvent</div>
                  </div>
                </div>
              </div>
              <div className="w-full md:w-96 p-4 rounded-2xl bg-black border border-white/10 font-mono text-xs">
                <div className="flex items-center gap-2 mb-3 px-2">
                  <div className="w-2 h-2 rounded-full bg-red-500/50" />
                  <div className="w-2 h-2 rounded-full bg-amber-500/50" />
                  <div className="w-2 h-2 rounded-full bg-emerald-500/50" />
                  <span className="ml-2 text-neutral-600">subscription_example.py</span>
                </div>
                <div className="text-nexus-cyan">@event_manager.subscribe</div>
                <div>(LLMResponseCompletedEvent)</div>
                <div className="text-purple-400">def</div> <span>on_ai_finish(event):</span>
                <div className="pl-4 text-neutral-400"># Hook into final response</div>
                <div className="pl-4">nexus_log(f<span className="text-emerald-400">"Output: {'{event.text}'}"</span>)</div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* LLM Domain */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 px-2 pb-2 border-b border-white/5 mb-4">
                <MessageSquare className="text-blue-400" size={16} />
                <h4 className="text-sm font-bold uppercase tracking-widest text-neutral-400">LLM & Intelligence</h4>
              </div>
              <EventRow name="LLMRequestStartedEvent" type="llm.request_started" desc="Cognitive cycle initialization." />
              <EventRow name="LLMResponseChunkEvent" type="llm.response_chunk" desc="Streaming token delivery." />
              <EventRow name="ToolStartEvent" type="llm.tool_start" desc="External system tool execution." />
              <EventRow name="VLMInferenceStartEvent" type="vlm.inference_start" desc="Visual perception processing." />
            </div>

            {/* Voice Domain */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 px-2 pb-2 border-b border-white/5 mb-4">
                <Mic className="text-purple-400" size={16} />
                <h4 className="text-sm font-bold uppercase tracking-widest text-neutral-400">Acoustic & Turn Logic</h4>
              </div>
              <EventRow name="STTTranscriptEvent" type="stt.transcript" desc="Phonetic to text conversion." />
              <EventRow name="TurnStartedEvent" type="plugin.turn_started" desc="User speech activity detected." />
              <EventRow name="TTSAudioEvent" type="tts.audio" desc="Vocal synthesis buffer delivery." />
              <EventRow name="AgentSayStartedEvent" type="agent.say_started" desc="Agent vocalization initiated." />
            </div>
          </div>
        </section>

        {/* Community & Links */}
        <section className="p-12 rounded-3xl bg-gradient-to-br from-neutral-900 to-black border border-white/10 relative overflow-hidden">
          <div className="absolute top-0 right-0 p-8 opacity-10">
            <Zap size={120} />
          </div>
          <div className="relative z-10">
            <h2 className="text-3xl font-bold mb-4">Integrate Nexus AI</h2>
            <p className="text-neutral-400 mb-8 max-w-lg">
              Want to build on top of Nexus? Check out our community resources and official tRPC documentation for advanced usage.
            </p>
            <div className="flex flex-wrap gap-4">
              <a 
                href="https://trpc.io/docs" 
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-6 py-3 bg-white text-black rounded-xl font-semibold hover:bg-neutral-200 transition-colors"
              >
                Official tRPC Docs <ExternalLink size={16} />
              </a>
              <a 
                href="https://trpc.io/docs/community/awesome-trpc" 
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-6 py-3 bg-white/5 border border-white/10 rounded-xl font-semibold hover:bg-white/10 transition-colors"
              >
                Awesome tRPC <ChevronRight size={16} />
              </a>
            </div>
          </div>
        </section>

      </main>

      <footer className="max-w-5xl mx-auto pt-12 pb-8 border-t border-white/5 text-center text-neutral-600 text-xs font-mono">
        &copy; 2026 NEXUS AI SYSTEMS • PRODUCTION GRADE • TYPE-SAFE
      </footer>
    </div>
  );
}

function EventRow({ name, type, desc }: { name: string; type: string; desc: string }) {
  return (
    <div className="flex items-center justify-between p-4 rounded-xl bg-white/[0.02] border border-white/5 hover:bg-white/[0.04] transition-colors group">
      <div className="flex flex-col gap-1">
        <span className="text-sm font-mono font-bold text-white group-hover:text-nexus-cyan transition-colors">{name}</span>
        <span className="text-[10px] text-neutral-500 font-mono tracking-tight">{type}</span>
      </div>
      <span className="text-xs text-neutral-400 text-right max-w-[150px]">{desc}</span>
    </div>
  );
}
