"use client";

import React from "react";
import { useNexus } from "@/contexts/NexusContext";
import { 
  Command, Cpu, ShieldAlert, Monitor, Globe, CheckCircle2, AlertTriangle, Eye, Loader2
} from "lucide-react";

export function AgentWorkspace() {
  const { workspaceState } = useNexus();

  // Safeguard against missing state
  const state = workspaceState || {
    current_task: null,
    active_capability: null,
    status: "idle",
    verification_state: null,
    active_window: null,
    browser_screenshot: null
  };

  // Status-specific badges
  const getStatusConfig = (status: string) => {
    switch (status) {
      case "running":
        return { label: "Running", color: "text-[#00FFFF] border-[#00FFFF]/30 bg-[#00FFFF]/10", glow: "shadow-[0_0_10px_#00FFFF]" };
      case "verifying":
        return { label: "Verifying", color: "text-amber-400 border-amber-400/30 bg-amber-400/10", glow: "shadow-[0_0_10px_#f59e0b]" };
      case "completed":
        return { label: "Completed", color: "text-emerald-400 border-emerald-400/30 bg-emerald-400/10", glow: "shadow-[0_0_10px_#10b981]" };
      case "failed":
        return { label: "Failed", color: "text-[#ff3366] border-[#ff3366]/30 bg-[#ff3366]/10", glow: "shadow-[0_0_10px_#ff3366]" };
      default:
        return { label: "Standby", color: "text-zinc-500 border-white/5 bg-black/40", glow: "" };
    }
  };

  const getVerificationConfig = (vState: string | null) => {
    switch (vState) {
      case "passed":
        return { label: "VERIFIED", icon: <CheckCircle2 size={12} />, color: "text-emerald-400 border-emerald-400/30 bg-emerald-400/10" };
      case "failed":
        return { label: "FAILED", icon: <ShieldAlert size={12} />, color: "text-[#ff3366] border-[#ff3366]/30 bg-[#ff3366]/10" };
      case "pending":
        return { label: "PENDING", icon: <Loader2 size={12} className="animate-spin" />, color: "text-amber-400 border-amber-400/30 bg-amber-400/10" };
      default:
        return { label: "INACTIVE", icon: null, color: "text-zinc-600 border-white/5 bg-zinc-900/20" };
    }
  };

  const statusConfig = getStatusConfig(state.status);
  const verificationConfig = getVerificationConfig(state.verification_state);

  return (
    <div className="flex-1 w-full bg-[#06060c] border border-[#6137FF]/30 shadow-[0_0_30px_rgba(0,0,0,0.9)] z-10 flex flex-col clip-cut-sm relative overflow-hidden h-full">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(97,55,255,0.03)_0%,transparent_100%)]"></div>
      
      {/* Header */}
      <div className="h-9 bg-black flex items-center justify-between px-3 border-b border-[#6137FF]/20 relative z-10 shrink-0">
        <div className="flex items-center gap-2">
          <Cpu size={12} className="text-[#00FFFF]" />
          <span className="text-[9px] font-quantico font-bold text-[#00FFFF] uppercase tracking-[0.2em]">Agent_Workspace</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-[8px] font-mono border px-2 py-0.5 clip-cut-sm tracking-wider uppercase ${statusConfig.color} ${statusConfig.glow}`}>
            {statusConfig.label}
          </span>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 p-3 flex flex-col gap-3 overflow-y-auto scroll-hide relative z-10 min-h-0">
        
        {/* Current Task */}
        <div className="flex flex-col gap-1.5 bg-black/40 border border-white/5 p-2.5 clip-cut-sm">
          <span className="text-[7.5px] font-mono text-zinc-500 uppercase tracking-widest">Active Request</span>
          <p className="text-[11px] font-sans text-zinc-300 font-medium leading-relaxed">
            {state.current_task ? `"${state.current_task}"` : "Awaiting user voice/chat instruction..."}
          </p>
        </div>

        {/* Info Grid */}
        <div className="grid grid-cols-2 gap-2">
          {/* Active Window */}
          <div className="flex flex-col gap-1 bg-black/40 border border-white/5 p-2 clip-cut-sm">
            <span className="text-[7.5px] font-mono text-zinc-500 uppercase tracking-widest flex items-center gap-1">
              <Monitor size={10} className="text-zinc-600" /> Focus Window
            </span>
            <span className="text-[10px] font-mono text-zinc-300 font-semibold truncate" title={state.active_window || "None"}>
              {state.active_window || "Desktop"}
            </span>
          </div>

          {/* Active Capability */}
          <div className="flex flex-col gap-1 bg-black/40 border border-white/5 p-2 clip-cut-sm">
            <span className="text-[7.5px] font-mono text-zinc-500 uppercase tracking-widest flex items-center gap-1">
              <Command size={10} className="text-zinc-600" /> Capability
            </span>
            <span className="text-[10px] font-mono text-zinc-300 font-semibold truncate" title={state.active_capability || "None"}>
              {state.active_capability || "Idle"}
            </span>
          </div>
        </div>

        {/* Verification Matrix */}
        <div className="flex items-center justify-between bg-black/60 border border-white/5 p-2.5 clip-cut-sm">
          <span className="text-[8px] font-quantico font-bold text-zinc-400 uppercase tracking-wider">Verification State</span>
          <div className={`flex items-center gap-1 text-[8.5px] font-mono font-bold border px-2 py-0.5 clip-cut-sm ${verificationConfig.color}`}>
            {verificationConfig.icon}
            <span>{verificationConfig.label}</span>
          </div>
        </div>

        {/* Browser Screenshot Section */}
        <div className="flex-1 flex flex-col min-h-[140px] bg-black/60 border border-white/5 p-2.5 clip-cut-sm relative">
          <div className="flex items-center justify-between mb-1.5 shrink-0">
            <span className="text-[8px] font-quantico font-bold text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
              <Globe size={11} className="text-[#00FFFF]" /> Playwright Sandbox Frame
            </span>
            {state.browser_screenshot && (
              <span className="text-[7px] font-mono text-emerald-400 flex items-center gap-1 animate-pulse">
                <Eye size={8} /> LIVE
              </span>
            )}
          </div>

          {/* Frame Container */}
          <div className="flex-1 bg-black border border-white/10 relative overflow-hidden flex items-center justify-center min-h-0">
            {state.browser_screenshot ? (
              <div className="w-full h-full relative group/frame">
                <img 
                  src={`data:image/jpeg;base64,${state.browser_screenshot}`} 
                  alt="Browser Frame" 
                  className="w-full h-full object-contain"
                />
                {/* HUD Scanlines */}
                <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:100%_4px] pointer-events-none opacity-40"></div>
                {/* Glowing Corner Accents */}
                <div className="absolute top-0 left-0 w-3.5 h-3.5 border-t border-l border-[#00FFFF]/50 pointer-events-none"></div>
                <div className="absolute bottom-0 right-0 w-3.5 h-3.5 border-b border-r border-[#00FFFF]/50 pointer-events-none"></div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center gap-1.5 text-zinc-600">
                <Globe size={20} className="opacity-20" />
                <span className="text-[8.5px] font-mono uppercase tracking-widest opacity-40">Browser Session Inactive</span>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
