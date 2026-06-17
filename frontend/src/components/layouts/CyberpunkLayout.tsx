import React from 'react';
import { DashboardLayoutProps } from './DashboardLayoutRenderer';

export function CyberpunkLayout({ orbNode, chatNode, logsNode, traceNode, inputNode, statusNode, telemetryNode }: DashboardLayoutProps) {
  return (
    <div className="flex flex-col h-full bg-[var(--background)] text-[var(--foreground)] p-4 overflow-hidden relative">
      {/* Decorative Grid Background */}
      <div className="absolute inset-0 pointer-events-none" style={{ backgroundImage: 'linear-gradient(rgba(255, 0, 255, 0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 0, 255, 0.1) 1px, transparent 1px)', backgroundSize: '20px 20px', zIndex: 0 }}></div>
      
      {/* Top Status Bar */}
      <div className="flex items-center justify-between mb-4 bg-[var(--card)] p-3 border-2 border-[var(--border)] relative z-10" style={{ boxShadow: '0 0 10px var(--border)' }}>
        <div className="flex-1 uppercase font-bold text-lg" style={{ textShadow: '0 0 5px var(--primary)' }}>{statusNode}</div>
        <div className="flex-1 ml-4" style={{ textShadow: '0 0 5px var(--secondary)' }}>{telemetryNode}</div>
      </div>

      <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-12 gap-4 relative z-10">
        <div className="col-span-1 lg:col-span-3 flex flex-col gap-4 min-h-0">
          <div className="h-64 bg-[var(--card)] border border-[var(--border)] flex items-center justify-center relative overflow-hidden" style={{ boxShadow: '0 0 15px rgba(0, 255, 255, 0.2) inset' }}>
            {orbNode}
          </div>
          <div className="flex-1 bg-[var(--card)] border border-[var(--border)] overflow-hidden" style={{ boxShadow: '0 0 15px rgba(255, 0, 255, 0.2) inset' }}>
            {traceNode}
          </div>
        </div>

        <div className="col-span-1 lg:col-span-6 flex flex-col min-h-0 bg-[var(--card)] border border-[var(--border)] overflow-hidden relative">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-[var(--primary)] to-transparent opacity-50"></div>
          <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
            {chatNode}
          </div>
          <div className="p-4 border-t border-[var(--border)] bg-black/50 backdrop-blur-md">
            {inputNode}
          </div>
        </div>

        <div className="col-span-1 lg:col-span-3 flex flex-col min-h-0">
          <div className="flex-1 bg-black border border-[var(--border)] overflow-hidden font-mono text-[10px] text-[var(--secondary)]" style={{ boxShadow: '0 0 15px rgba(0, 255, 255, 0.2) inset' }}>
            <div className="p-2 border-b border-[var(--border)] uppercase tracking-widest bg-[var(--card)]">System Stream</div>
            {logsNode}
          </div>
        </div>
      </div>
    </div>
  );
}
