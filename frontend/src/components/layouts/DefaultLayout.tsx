import React from 'react';
import { DashboardLayoutProps } from './DashboardLayoutRenderer';

export function DefaultLayout({ orbNode, chatNode, logsNode, traceNode, inputNode, statusNode, telemetryNode }: DashboardLayoutProps) {
  return (
    <div className="flex flex-col h-full bg-[var(--background)] text-[var(--foreground)] p-4 pt-16 lg:pt-4">
      {/* Top Status Bar */}
      <div className="flex items-center justify-between mb-4 bg-[var(--card)] p-3 rounded-[var(--radius)] border border-[var(--border)] shadow-sm">
        <div className="flex-1">{statusNode}</div>
        <div className="flex-1 ml-4">{telemetryNode}</div>
      </div>

      <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left Column: Chat & Input */}
        <div className="col-span-1 lg:col-span-8 flex flex-col min-h-0 bg-[var(--card)] rounded-[var(--radius)] border border-[var(--border)] overflow-hidden shadow-md">
          <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
            {chatNode}
          </div>
          <div className="p-4 border-t border-[var(--border)] bg-[var(--muted)]">
            {inputNode}
          </div>
        </div>

        {/* Right Column: Orb, Trace, Logs */}
        <div className="col-span-1 lg:col-span-4 flex flex-col gap-4 min-h-0">
          <div className="h-64 bg-[var(--card)] rounded-[var(--radius)] border border-[var(--border)] flex items-center justify-center shadow-md relative overflow-hidden">
            <div className="absolute inset-0 bg-black/20 z-0"></div>
            <div className="relative z-10 w-full h-full flex items-center justify-center scale-75 origin-center">
              {orbNode}
            </div>
          </div>
          <div className="flex-1 bg-[var(--card)] rounded-[var(--radius)] border border-[var(--border)] overflow-hidden shadow-md">
            {traceNode}
          </div>
          <div className="h-48 bg-[#000000] rounded-[var(--radius)] border border-[var(--border)] overflow-hidden shadow-md font-mono text-xs">
            {logsNode}
          </div>
        </div>
      </div>
    </div>
  );
}
