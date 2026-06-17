import React from 'react';
import { DashboardLayoutProps } from './DashboardLayoutRenderer';

export function AnimeLayout({ orbNode, chatNode, logsNode, traceNode, inputNode, statusNode, telemetryNode }: DashboardLayoutProps) {
  return (
    <div className="flex flex-col h-full bg-[var(--background)] text-[var(--foreground)] p-4 md:p-8 relative overflow-hidden">
      {/* Soft overlay patterns could go here */}
      
      {/* Top Header - Bubbly */}
      <div className="flex items-center justify-between mb-6 bg-[var(--card)]/80 backdrop-blur-md p-4 rounded-full border border-[var(--border)] shadow-sm">
        <div className="flex-1 font-medium pl-4">{statusNode}</div>
        <div className="flex-1 pr-4 text-right opacity-80">{telemetryNode}</div>
      </div>

      <div className="flex-1 min-h-0 flex flex-col lg:flex-row gap-6 relative z-10">
        {/* Left Column: Chat & Input */}
        <div className="flex-1 flex flex-col min-h-0 bg-[var(--card)]/90 backdrop-blur-md rounded-[2rem] border border-[var(--border)] overflow-hidden shadow-lg">
          <div className="flex-1 overflow-y-auto p-6">
            {chatNode}
          </div>
          <div className="p-4 m-4 mt-0 bg-[var(--background)] rounded-3xl border border-[var(--border)]">
            {inputNode}
          </div>
        </div>

        {/* Right Column: Character/Orb & Stats */}
        <div className="w-full lg:w-80 flex flex-col gap-6 min-h-0">
          <div className="flex-1 bg-[var(--card)]/90 backdrop-blur-md rounded-[2rem] border border-[var(--border)] flex items-center justify-center relative overflow-hidden shadow-lg">
             <div className="absolute inset-0 bg-gradient-to-t from-[var(--primary)]/10 to-transparent"></div>
             {orbNode}
          </div>
          <div className="h-1/3 bg-[var(--card)]/90 backdrop-blur-md rounded-[2rem] border border-[var(--border)] p-6 overflow-hidden shadow-lg">
            {traceNode}
          </div>
        </div>
      </div>
    </div>
  );
}
