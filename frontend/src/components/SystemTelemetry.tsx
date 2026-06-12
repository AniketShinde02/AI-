"use client";

import React from "react";
import { useNexus } from "@/contexts/NexusContext";

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
    <div className="flex flex-col gap-3">
      {/* CORE METRICS */}
      <div className="glass p-4 space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-zinc-500">
            Core System
          </span>
          <div className={`status-dot ${systemMetrics ? "animate-pulse bg-indigo-500" : "bg-zinc-600"}`}></div>
        </div>
        
        <div className="grid grid-cols-2 gap-2">
          {/* CPU Load */}
          <div className="bg-black/60 border border-white/10 p-3 rounded-lg flex flex-col justify-between relative overflow-hidden group hover:border-indigo-500/30 transition-colors cursor-default">
            <div className="absolute inset-0 bg-indigo-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
            <span className="text-[8px] text-zinc-500 uppercase tracking-widest font-mono mb-1">CPU_LOAD</span>
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-black text-indigo-400 font-mono tracking-tighter drop-shadow-[0_0_8px_rgba(99,102,241,0.3)]">
                {cpu.toFixed(1)}
              </span>
              <span className="text-[8px] font-bold text-indigo-500/50">%</span>
            </div>
          </div>

          {/* Memory Allocation */}
          <div className="bg-black/60 border border-white/10 p-3 rounded-lg flex flex-col justify-between relative overflow-hidden group hover:border-purple-500/30 transition-colors cursor-default">
            <div className="absolute inset-0 bg-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
            <span className="text-[8px] text-zinc-500 uppercase tracking-widest font-mono mb-1">MEM_ALLOC</span>
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-black text-purple-400 font-mono tracking-tighter drop-shadow-[0_0_8px_rgba(168,85,247,0.3)]">
                {mem.toFixed(1)}
              </span>
              <span className="text-[8px] font-bold text-purple-500/50">%</span>
            </div>
          </div>

          {/* Thermal State (Spans full width at the bottom) */}
          <div className="col-span-2 bg-black/60 border border-white/10 p-3 rounded-lg flex items-center justify-between relative overflow-hidden group hover:border-fuchsia-500/30 transition-colors cursor-default">
            <div className="absolute inset-0 bg-fuchsia-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
            <div className="flex flex-col">
              <span className="text-[8px] text-zinc-500 uppercase tracking-widest font-mono mb-1">THERMAL_STATE</span>
              <span className="text-[9px] font-bold tracking-widest text-emerald-400">
                {temp > 80 ? <span className="text-red-500 animate-pulse">CRITICAL</span> : 'STABLE'}
              </span>
            </div>
            <div className="flex items-baseline gap-1">
              <span className={`text-3xl font-black font-mono tracking-tighter ${temp > 80 ? 'text-red-500 drop-shadow-[0_0_8px_rgba(239,68,68,0.8)]' : 'text-fuchsia-400 drop-shadow-[0_0_8px_rgba(217,70,239,0.5)]'}`}>
                {temp.toFixed(1)}
              </span>
              <span className="text-xs font-bold text-fuchsia-500/50">°C</span>
            </div>
          </div>
        </div>
      </div>

      {/* NETWORK TELEMETRY */}
      <div className="glass p-4 space-y-4">
        <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-zinc-500">
          Network Telemetry
        </span>
        
        <div className="grid grid-cols-2 gap-2">
          <div className="bg-black/40 border border-white/5 p-2 rounded-lg flex flex-col gap-1">
            <span className="text-[8px] text-zinc-500 uppercase tracking-widest font-mono">LATENCY</span>
            <span className="text-xs font-bold text-indigo-400 font-mono">{ping}ms</span>
          </div>
          <div className="bg-black/40 border border-white/5 p-2 rounded-lg flex flex-col gap-1">
            <span className="text-[8px] text-zinc-500 uppercase tracking-widest font-mono">RATE</span>
            <span className="text-xs font-bold text-purple-400 font-mono">{rate.toFixed(1)}Mb/s</span>
          </div>
          <div className="bg-black/40 border border-white/5 p-2 rounded-lg flex flex-col gap-1">
            <span className="text-[8px] text-zinc-500 uppercase tracking-widest font-mono">PACKETS_TX</span>
            <span className="text-xs font-bold text-zinc-300 font-mono">{tx}</span>
          </div>
          <div className="bg-black/40 border border-white/5 p-2 rounded-lg flex flex-col gap-1">
            <span className="text-[8px] text-zinc-500 uppercase tracking-widest font-mono">PACKETS_RX</span>
            <span className="text-xs font-bold text-zinc-300 font-mono">{rx}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
