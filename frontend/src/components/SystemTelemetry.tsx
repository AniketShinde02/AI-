"use client";

import React from "react";
import { useNexus } from "@/contexts/NexusContext";
import { Activity, Wifi, Globe } from "lucide-react";

export function SystemTelemetry() {
  const { systemMetrics } = useNexus();

  // If no metrics yet, show a loading/placeholder state
  const cpu = systemMetrics?.cpu || 0;
  const mem = systemMetrics?.memory?.usedPercentage || 0;
  const temp = systemMetrics?.temperature || 0;
  const ping = systemMetrics?.network?.ping || 0;
  const rate = systemMetrics?.network?.rate || 0;
  const tx = systemMetrics?.network?.tx || 0;
  const rx = systemMetrics?.network?.rx || 0;

  return (
    <div className="flex flex-col gap-2">
      {/* CORE METRICS */}
      <div className="bg-[#06060c] border border-[#6137FF]/30 p-3 space-y-2 clip-cut shadow-[0_0_15px_rgba(97,55,255,0.1)] relative">
        <div className="absolute top-0 right-0 w-16 h-16 bg-[radial-gradient(circle_at_top_right,rgba(0,255,255,0.1)_0%,transparent_70%)] pointer-events-none"></div>
        
        <div className="flex items-center justify-between border-b border-white/5 pb-1.5">
          <span className="text-[9px] font-quantico font-bold uppercase tracking-[0.3em] text-[#00FFFF]">
            Core_Metrics
          </span>
          <div className={`w-1.5 h-1.5 rounded-sm transform rotate-45 ${systemMetrics ? "animate-pulse bg-[#00FFFF] shadow-[0_0_8px_#00FFFF]" : "bg-zinc-600"}`}></div>
        </div>
        
        <div className="grid grid-cols-2 gap-2">
          {/* CPU Load */}
          <div className="bg-black/80 border border-white/10 p-2 flex flex-col justify-between relative overflow-hidden group hover:border-[#00FFFF]/50 transition-colors cursor-default clip-cut-sm">
            <div className="absolute inset-0 bg-[#00FFFF]/5 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
            <span className="text-[7px] font-quantico text-[#00FFFF]/70 uppercase tracking-[0.2em] mb-1">CPU_LOAD</span>
            <div className="flex items-baseline gap-1">
              <span className="text-xl font-mono tracking-tighter text-white drop-shadow-[0_0_8px_rgba(0,255,255,0.5)]">
                {cpu.toFixed(1)}
              </span>
              <span className="text-[8px] font-bold text-[#00FFFF]/50">%</span>
            </div>
            {/* Minimal progress bar */}
            <div className="h-0.5 w-full bg-white/5 mt-1.5 overflow-hidden relative">
              <div className="absolute top-0 left-0 h-full bg-[#00FFFF]" style={{ width: `${cpu}%` }}></div>
            </div>
          </div>

          {/* Memory Allocation */}
          <div className="bg-black/80 border border-white/10 p-2 flex flex-col justify-between relative overflow-hidden group hover:border-[#6137FF]/50 transition-colors cursor-default clip-cut-sm">
            <div className="absolute inset-0 bg-[#6137FF]/5 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
            <span className="text-[7px] font-quantico text-[#6137FF]/70 uppercase tracking-[0.2em] mb-1">MEM_ALLOC</span>
            <div className="flex items-baseline gap-1">
              <span className="text-xl font-mono tracking-tighter text-white drop-shadow-[0_0_8px_rgba(97,55,255,0.5)]">
                {mem.toFixed(1)}
              </span>
              <span className="text-[8px] font-bold text-[#6137FF]/50">%</span>
            </div>
            {/* Minimal progress bar */}
            <div className="h-0.5 w-full bg-white/5 mt-1.5 overflow-hidden relative">
              <div className="absolute top-0 left-0 h-full bg-[#6137FF]" style={{ width: `${mem}%` }}></div>
            </div>
          </div>

          {/* Thermal State (Spans full width at the bottom) */}
          <div className="col-span-2 bg-black/80 border border-white/10 p-2 flex items-center justify-between relative overflow-hidden group hover:border-[#ff3366]/40 transition-colors cursor-default clip-cut-sm">
            <div className="absolute inset-0 bg-black opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
            <div className="flex flex-col">
              <span className="text-[7px] font-quantico text-zinc-500 uppercase tracking-[0.2em]">THERMAL_STATE</span>
              <span className={`text-[8px] font-bold tracking-widest ${temp > 80 ? 'text-[#ff3366] animate-pulse drop-shadow-[0_0_5px_#ff3366]' : 'text-zinc-400'}`}>
                {temp > 80 ? 'CRITICAL' : 'STABLE'}
              </span>
            </div>
            <div className="flex items-baseline gap-1">
              <span className={`text-2xl font-mono tracking-tighter text-white ${temp > 80 ? 'drop-shadow-[0_0_10px_#ff3366]' : ''}`}>
                {temp.toFixed(1)}
              </span>
              <span className="text-[9px] font-bold text-zinc-600">°C</span>
            </div>
          </div>
        </div>
      </div>

      {/* NETWORK TELEMETRY */}
      <div className="bg-[#06060c] border border-[#00FFFF]/20 p-3 clip-cut shadow-[0_0_15px_rgba(0,255,255,0.05)] relative overflow-hidden group">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(0,255,255,0.05)_0%,transparent_70%)] pointer-events-none"></div>

        <div className="flex items-center justify-between border-b border-white/5 pb-2 mb-2 relative z-10">
          <div className="flex items-center gap-2">
            <Activity size={10} className="text-[#00FFFF]" />
            <span className="text-[9px] font-quantico font-bold uppercase tracking-[0.2em] text-zinc-300">
              Network Telemetry
            </span>
          </div>
          <div className="px-2 py-0.5 border border-[#00FFFF]/30 rounded-full bg-[#00FFFF]/10 shadow-[0_0_10px_rgba(0,255,255,0.1)]">
            <span className="text-[7px] font-mono font-bold text-[#00FFFF] tracking-widest uppercase">Secure Uplink</span>
          </div>
        </div>
        
        <div className="grid grid-cols-3 gap-2 mb-3 relative z-10">
          <div className="flex flex-col gap-0.5">
            <span className="text-[6px] font-mono text-zinc-500 uppercase tracking-widest">WSS Latency</span>
            <div className="flex items-center gap-1.5 mt-0.5">
              <Wifi size={10} className="text-[#00FFFF]" />
              <span className="text-[10px] font-bold text-white font-mono">{ping}ms</span>
            </div>
          </div>
          <div className="flex flex-col gap-0.5">
            <span className="text-[6px] font-mono text-zinc-500 uppercase tracking-widest">Packet Rate</span>
            <span className="text-[10px] font-bold text-white font-mono mt-0.5">{rate.toFixed(2)} MB/s</span>
          </div>
          <div className="flex flex-col gap-0.5 items-end">
            <span className="text-[6px] font-mono text-zinc-500 uppercase tracking-widest">Routing</span>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="text-[10px] font-bold text-white font-mono uppercase">Global</span>
              <Globe size={10} className="text-[#00FFFF]" />
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-1.5 relative z-10">
          <div className="flex items-center gap-2">
            <span className="text-[6px] font-mono text-zinc-500 w-3">TX</span>
            <div className="flex-1 h-1 bg-black border border-white/5 overflow-hidden">
              <div className="h-full bg-[#00FFFF] shadow-[0_0_5px_#00FFFF]" style={{ width: `${Math.min((tx / 100) * 100, 100)}%` }}></div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[6px] font-mono text-zinc-500 w-3">RX</span>
            <div className="flex-1 h-1 bg-black border border-white/5 overflow-hidden">
              <div className="h-full bg-[#00FFFF]/60 shadow-[0_0_5px_#00FFFF]" style={{ width: `${Math.min((rx / 100) * 100, 100)}%` }}></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
