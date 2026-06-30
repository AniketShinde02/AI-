"use client";

import React, { useEffect, useState } from "react";
import { useNexus } from "@/contexts/NexusContext";
import { Server, Activity, Database, GitMerge } from "lucide-react";

export function CoreSubsystemsWidget() {
  const { workspaceState } = useNexus();
  const [pulse, setPulse] = useState(false);

  useEffect(() => {
    setPulse(true);
    const timer = setTimeout(() => setPulse(false), 500);
    return () => clearTimeout(timer);
  }, [workspaceState?.status]);

  const subsystems = [
    { name: "MCP Router", status: "ONLINE", icon: Server, color: "#00FFFF" },
    { name: "Playwright Sandbox", status: workspaceState?.browser_screenshot ? "ACTIVE" : "IDLE", icon: Activity, color: workspaceState?.browser_screenshot ? "#10b981" : "#6137FF" },
    { name: "Knowledge Graph", status: "SYNCED", icon: Database, color: "#00FFFF" },
    { name: "Execution Engine", status: workspaceState?.status === 'running' ? "EXECUTING" : "IDLE", icon: GitMerge, color: workspaceState?.status === 'running' ? "#ff3366" : "#6137FF" },
  ];

  return (
    <div className="flex flex-col bg-[#06060c] border border-white/5 clip-cut h-full relative overflow-hidden group hover:border-[#6137FF]/30 transition-colors">
      <div className="absolute top-0 right-0 w-32 h-32 bg-[radial-gradient(circle_at_top_right,rgba(97,55,255,0.1)_0%,transparent_70%)] pointer-events-none z-0"></div>
      
      <div className="p-3 border-b border-white/10 flex items-center justify-between shrink-0 relative z-10 bg-black/50">
        <span className="text-[10px] font-quantico font-bold text-zinc-400 uppercase tracking-[0.2em]">Core Subsystems</span>
        <div className={`w-2 h-2 rounded-full ${pulse ? 'bg-[#00FFFF] shadow-[0_0_10px_#00FFFF]' : 'bg-[#6137FF] shadow-[0_0_8px_#6137FF]'}`}></div>
      </div>
      
      <div className="flex-1 overflow-y-auto scroll-hide p-3 space-y-2 relative z-10 flex flex-col justify-center">
        {subsystems.map((sys, idx) => {
          const Icon = sys.icon;
          return (
            <div key={idx} className="flex items-center justify-between bg-black/40 border border-white/5 p-2 clip-cut-sm hover:border-[#00FFFF]/20 transition-colors">
              <div className="flex items-center gap-3">
                <Icon size={14} color={sys.color} className="opacity-80 drop-shadow-[0_0_5px_currentColor]" />
                <span className="text-[10px] font-mono text-zinc-300">{sys.name}</span>
              </div>
              <span className={`text-[9px] font-bold tracking-wider px-1.5 py-0.5 rounded-sm bg-black/60 border border-white/5`} style={{ color: sys.color }}>
                {sys.status}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
