import React from 'react';
import { DashboardLayoutProps } from './DashboardLayoutRenderer';

export function MinimalLayout({ orbNode, chatNode, logsNode, traceNode, inputNode, statusNode, telemetryNode }: DashboardLayoutProps) {
  return (
    <div className="flex flex-col h-full bg-[var(--background)] text-[var(--foreground)] p-8 max-w-6xl mx-auto w-full">
      {/* Clean Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="text-xl font-medium tracking-tight">{statusNode}</div>
        <div className="text-sm opacity-60 flex gap-4">{telemetryNode}</div>
      </div>

      <div className="flex-1 min-h-0 flex flex-col lg:flex-row gap-8">
        {/* Left Column: Chat & Input */}
        <div className="flex-1 flex flex-col min-h-0 bg-[var(--card)] rounded-[var(--radius)] shadow-sm border border-[var(--border)]">
          <div className="flex-1 overflow-y-auto p-8">
            {chatNode}
          </div>
          <div className="p-4 border-t border-[var(--border)] bg-[var(--muted)]">
            {inputNode}
          </div>
        </div>

        {/* Right Column: Orb & Trace */}
        <div className="w-full lg:w-80 flex flex-col gap-8 min-h-0">
          <div className="h-64 bg-transparent rounded-[var(--radius)] flex items-center justify-center relative">
             <div className="absolute inset-0 bg-gradient-to-b from-transparent to-[var(--muted)] opacity-20 rounded-[var(--radius)]"></div>
             {orbNode}
          </div>
          <div className="flex-1 bg-[var(--card)] rounded-[var(--radius)] shadow-sm border border-[var(--border)] p-4 overflow-hidden">
            <h3 className="text-xs uppercase tracking-wider text-[var(--muted-foreground)] mb-4 font-semibold">System Trace</h3>
            {traceNode}
          </div>
        </div>
      </div>
    </div>
  );
}
