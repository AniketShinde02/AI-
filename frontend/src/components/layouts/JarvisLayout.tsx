import React from 'react';
import { DashboardLayoutProps } from './DashboardLayoutRenderer';

export function JarvisLayout({ orbNode, chatNode, logsNode, traceNode, inputNode, statusNode, telemetryNode }: DashboardLayoutProps) {
  return (
    <div className="flex flex-col h-full bg-[var(--background)] text-[var(--foreground)] p-6 gap-6">
      {/* Top HUD */}
      <div className="flex items-center justify-between bg-[var(--card)]/50 backdrop-blur-md p-4 rounded-2xl border border-[var(--border)]">
        <div className="flex-1 text-2xl font-light tracking-wide">{statusNode}</div>
        <div className="flex-1 ml-4 text-right flex justify-end">{telemetryNode}</div>
      </div>

      <div className="flex-1 min-h-0 flex flex-col lg:flex-row gap-6">
        {/* Left Info Pane */}
        <div className="w-full lg:w-64 flex flex-col gap-6 min-h-0">
          <div className="flex-1 bg-[var(--card)]/50 backdrop-blur-md rounded-2xl border border-[var(--border)] p-4 overflow-hidden shadow-[0_0_15px_rgba(0,136,255,0.1)]">
            <h3 className="text-xs uppercase tracking-widest text-[var(--primary)] mb-4">Diagnostics</h3>
            {traceNode}
          </div>
          <div className="h-64 bg-black/60 backdrop-blur-md rounded-2xl border border-[var(--border)] overflow-hidden font-mono text-[10px] p-2 text-[var(--primary)]">
            {logsNode}
          </div>
        </div>

        {/* Center Main View */}
        <div className="flex-1 flex flex-col min-h-0 bg-[var(--card)]/40 backdrop-blur-xl rounded-3xl border border-[var(--border)] overflow-hidden shadow-[0_0_30px_rgba(0,136,255,0.15)] relative">
          <div className="absolute inset-0 bg-gradient-to-b from-[var(--primary)]/5 to-transparent pointer-events-none"></div>
          <div className="flex-1 overflow-y-auto p-8 custom-scrollbar">
            {chatNode}
          </div>
          <div className="p-6 bg-[var(--background)]/80 backdrop-blur-md border-t border-[var(--border)]">
            {inputNode}
          </div>
        </div>

        {/* Right Core Pane */}
        <div className="w-full lg:w-80 flex flex-col min-h-0">
          <div className="flex-1 bg-[var(--card)]/50 backdrop-blur-md rounded-3xl border border-[var(--border)] flex items-center justify-center relative overflow-hidden shadow-[0_0_20px_rgba(0,136,255,0.2)]">
            <div className="absolute inset-0 bg-[url('/hologram-grid.png')] opacity-10 mix-blend-screen"></div>
            {orbNode}
          </div>
        </div>
      </div>
    </div>
  );
}
