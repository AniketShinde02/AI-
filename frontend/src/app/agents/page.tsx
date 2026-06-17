"use client";

import { useEffect, useState } from "react";
import { Bot, Zap, Clock, Activity, ChevronRight, Shield, Plus } from "lucide-react";

interface Agent {
  id: string;
  name: string;
  status: string;
  description: string;
  color: string;
  runtime: string;
  calls: number;
}

const statusConfig: Record<string, { label: string; glow: string }> = {
  active: { label: "ACTIVE", glow: "#00FFFF" },
  idle: { label: "IDLE", glow: "#10b981" },
  standby: { label: "STANDBY", glow: "#6137FF" },
  error: { label: "ERROR", glow: "#ff3366" },
};

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchAgents = () => {
    fetch("http://localhost:8001/api/agents")
      .then((res) => res.json())
      .then((data) => {
        setAgents(data);
        setIsLoading(false);
      })
      .catch((err) => {
        console.error("Failed to fetch agents", err);
        setIsLoading(false);
      });
  };

  useEffect(() => {
    fetchAgents();
  }, []);

  const handleCreateAgent = async () => {
    const id = `agent_${Math.random().toString(36).substr(2, 9)}`;
    const newAgent = {
      id,
      name: `new_agent_${id.substr(0,4)}`,
      status: "idle",
      description: "A newly created agent instance.",
      color: "#ec4899",
      runtime: "0.0s",
      calls: 0
    };
    await fetch("http://localhost:8001/api/agents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(newAgent)
    });
    fetchAgents();
  };

  const handleToggleStatus = async (agent: Agent) => {
    const newStatus = agent.status === "active" ? "idle" : "active";
    await fetch(`http://localhost:8001/api/agents/${agent.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...agent, status: newStatus })
    });
    fetchAgents();
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    await fetch(`http://localhost:8001/api/agents/${id}`, { method: "DELETE" });
    fetchAgents();
  };

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
        <div className="flex items-center gap-4">
          <button onClick={handleCreateAgent} className="flex items-center gap-2 px-3 py-1.5 bg-[#6137FF]/20 hover:bg-[#6137FF]/40 border border-[#6137FF]/50 transition-colors clip-cut-sm">
            <Plus size={12} className="text-[#6137FF]" />
            <span className="text-[9px] font-bold uppercase tracking-widest text-[#6137FF]">New Agent</span>
          </button>
          <div className="flex items-center gap-2">
            <div className="px-3 py-1 bg-[#00FFFF]/10 border border-[#00FFFF]/30 clip-cut-sm">
              <span className="text-[9px] font-bold uppercase tracking-widest text-[#00FFFF]">
                {agents.filter((a) => a.status === "active").length} Active
              </span>
            </div>
            <div className="px-3 py-1 bg-white/5 border border-white/10 clip-cut-sm">
              <span className="text-[9px] font-bold uppercase tracking-widest text-zinc-400">
                {agents.length} Total
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3 shrink-0">
        {[
          { label: "Total Calls", value: agents.reduce((a, b) => a + b.calls, 0), icon: Activity, color: "#6137FF" },
          { label: "Active Agents", value: agents.filter((a) => a.status === "active").length, icon: Zap, color: "#00FFFF" },
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
          {agents.map((agent) => {
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
                  <div className="flex flex-col gap-2 shrink-0">
                    <button 
                      onClick={(e) => { e.stopPropagation(); handleToggleStatus(agent); }}
                      className="px-3 py-1.5 border hover:bg-white/5 transition-colors text-[9px] font-bold uppercase tracking-widest clip-cut-sm flex items-center justify-center min-w-[80px]"
                      style={{ color: agent.status === 'active' ? '#ff3366' : '#00FFFF', borderColor: agent.status === 'active' ? '#ff336640' : '#00FFFF40' }}
                    >
                      {agent.status === 'active' ? 'Stop' : 'Start'}
                    </button>
                    <button 
                      onClick={(e) => handleDelete(e, agent.id)}
                      className="px-3 py-1.5 border border-zinc-800 hover:border-zinc-500 hover:bg-white/5 transition-colors text-[9px] font-bold uppercase tracking-widest text-zinc-500 hover:text-white clip-cut-sm flex items-center justify-center"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
