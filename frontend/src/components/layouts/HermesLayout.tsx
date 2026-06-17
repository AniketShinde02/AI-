import React from 'react';
import { DashboardLayoutProps } from './DashboardLayoutRenderer';

export function HermesLayout({ orbNode, chatNode, logsNode, traceNode, inputNode, statusNode, telemetryNode }: DashboardLayoutProps) {
  return (
    <div className="flex flex-col h-full bg-[#050505] text-[#00ff00] p-0 font-mono">
      {/* Top Status Bar - Minimal */}
      <div className="flex items-center justify-between bg-black p-2 border-b border-[#222222]">
        <div className="flex-1 font-bold tracking-widest uppercase">{statusNode}</div>
        <div className="flex-1 ml-4 text-xs opacity-70">{telemetryNode}</div>
      </div>

      <div className="flex-1 min-h-0 flex flex-col lg:flex-row">
        {/* Left Pane: Chat & Input */}
        <div className="flex-1 flex flex-col min-h-0 border-r border-[#222222] bg-[#0a0a0a]">
          <div className="flex-1 overflow-y-auto p-4 custom-scrollbar terminal-scroll">
            {chatNode}
          </div>
          <div className="p-2 border-t border-[#222222] bg-black">
            {inputNode}
          </div>
        </div>

        {/* Right Pane: Trace & Logs & Orb */}
        <div className="w-full lg:w-96 flex flex-col min-h-0 bg-[#080808]">
          <div className="h-48 border-b border-[#222222] flex items-center justify-center bg-black relative">
             <div className="absolute top-2 left-2 text-[10px] opacity-50 uppercase tracking-widest z-20">Voice Modulator</div>
             <div className="scale-75 origin-center z-10 w-full h-full flex items-center justify-center">
              {orbNode}
             </div>
          </div>
          <div className="flex-1 overflow-hidden border-b border-[#222222]">
            {traceNode}
          </div>
          <div className="h-64 bg-black overflow-hidden text-[10px]">
            {logsNode}
          </div>
        </div>
      </div>
    </div>
  );
}
