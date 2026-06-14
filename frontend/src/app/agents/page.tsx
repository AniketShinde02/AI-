"use client";

import { Bot, Zap, Clock, Activity, ChevronRight, Shield } from "lucide-react";

const AGENTS = [
  {
    id: "parent_delegate",
    name: "parent_delegate_task",
    status: "active",
    description: "Top-level orchestrator. Decomposes complex instructions into sub-tasks and delegates.",
    color: "#00FFFF",
    runtime: "0.0s",
    calls: 3,
  },
  {
    id: "web_search",
    name: "web_search",
    status: "active",
    description: "Real-time web intelligence. Executes Tavily queries and synthesizes results.",
    color: "#6137FF",
    runtime: "0.8s",
    calls: 12,
  },
  {
    id: "query_memory",
    name: "query_memory",
    status: "idle",
    description: "Retrieves relevant context from persistent memory store.",
    color: "#10b981",
    runtime: "0.2s",
    calls: 7,
  },
  {
    id: "run_command",
    name: "run_command",
    status: "standby",
    description: "System automation agent. Executes shell commands with sandboxing.",
    color: "#f59e0b",
    runtime: "—",
    calls: 0,
  },
  {
    id: "rag_oracle",
    name: "rag_oracle",
    status: "standby",
    description: "Semantic retrieval from indexed knowledge base using vector similarity.",
    color: "#ec4899",
    runtime: "—",
    calls: 0,
  },
];

const statusConfig: Record<string, { label: string; glow: string }> = {
  active: { label: "ACTIVE", glow: "#00FFFF" },
  idle: { label: "IDLE", glow: "#10b981" },
  standby: { label: "STANDBY", glow: "#6137FF" },
  error: { label: "ERROR", glow: "#ff3366" },
};

export default function AgentsPage() {
  return (
    <div className="h-full flex flex-col overflow-hidden p-4 gap-4">
      {/* Header */}
      <div className="flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-[#6137FF]/20 border border-[#6137FF]/40 flex items-center justify-center clip-cut">
            <Bot size={16} className="text-[#6137FF]" />
          </div>
          <div>
            <h1 className="text-[11px] font-quantico font-bold uppercase tracking-[0.3em] text-white">Agent Registry</h1>
            <p className="text-[9px] font-mono text-zinc-500 uppercase tracking-widest">Deployable Intelligence Modules</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="px-3 py-1 bg-[#00FFFF]/10 border border-[#00FFFF]/30 clip-cut-sm">
            <span className="text-[9px] font-bold uppercase tracking-widest text-[#00FFFF]">
              {AGENTS.filter((a) => a.status === "active").length} Active
            </span>
          </div>
          <div className="px-3 py-1 bg-white/5 border border-white/10 clip-cut-sm">
            <span className="text-[9px] font-bold uppercase tracking-widest text-zinc-400">
              {AGENTS.length} Total
            </span>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3 shrink-0">
        {[
          { label: "Total Calls", value: AGENTS.reduce((a, b) => a + b.calls, 0), icon: Activity, color: "#6137FF" },
          { label: "Active Agents", value: AGENTS.filter((a) => a.status === "active").length, icon: Zap, color: "#00FFFF" },
          { label: "Avg Runtime", value: "0.3s", icon: Clock, color: "#10b981" },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-[#06060c] border clip-cut p-4 flex items-center gap-3" style={{ borderColor: `${color}20` }}>
            <div className="w-8 h-8 flex items-center justify-center border clip-cut-sm" style={{ background: `${color}15`, borderColor: `${color}30` }}>
              <Icon size={14} style={{ color }} />
            </div>
            <div>
              <p className="text-[9px] font-mono text-zinc-500 uppercase tracking-widest">{label}</p>
              <p className="text-xl font-bold font-quantico" style={{ color }}>{value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Agent Cards */}
      <div className="flex-1 overflow-y-auto scroll-hide">
        <div className="grid grid-cols-1 gap-3">
          {AGENTS.map((agent) => {
            const sc = statusConfig[agent.status] || statusConfig.standby;
            return (
              <div
                key={agent.id}
                className="bg-[#06060c] border border-white/5 hover:border-white/15 clip-cut p-5 group transition-all cursor-pointer"
                style={{ borderColor: agent.status === "active" ? `${agent.color}20` : undefined }}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-4 flex-1 min-w-0">
                    {/* Status indicator */}
                    <div
                      className="w-10 h-10 border flex items-center justify-center clip-cut shrink-0"
                      style={{ background: `${agent.color}15`, borderColor: `${agent.color}40` }}
                    >
                      <Shield size={16} style={{ color: agent.color }} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-1">
                        <span className="text-[12px] font-mono font-bold text-white">{agent.name}</span>
                        <span
                          className="text-[8px] font-bold uppercase tracking-widest px-2 py-0.5 border clip-cut-sm"
                          style={{ color: sc.glow, borderColor: `${sc.glow}40`, background: `${sc.glow}10` }}
                        >
                          <span
                            className="inline-block w-1 h-1 rounded-full mr-1.5 animate-pulse"
                            style={{ background: sc.glow }}
                          />
                          {sc.label}
                        </span>
                      </div>
                      <p className="text-[11px] text-zinc-400 font-sans leading-relaxed">{agent.description}</p>
                      <div className="flex items-center gap-4 mt-3">
                        <span className="text-[9px] font-mono text-zinc-600">
                          Runtime: <span className="text-zinc-400">{agent.runtime}</span>
                        </span>
                        <span className="text-[9px] font-mono text-zinc-600">
                          Calls: <span style={{ color: agent.color }}>{agent.calls}</span>
                        </span>
                      </div>
                    </div>
                  </div>
                  <ChevronRight size={16} className="text-zinc-700 group-hover:text-zinc-400 transition-colors shrink-0 mt-3" />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
