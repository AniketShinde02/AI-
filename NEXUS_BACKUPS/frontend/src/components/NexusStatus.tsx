import React from 'react';
import { motion } from 'framer-motion';

export type NexusVoiceState = 'idle' | 'listening' | 'thinking' | 'speaking' | 'tool_running' | 'interrupted';

interface NexusStatusProps {
  state: NexusVoiceState;
  activeTool?: string;
}

export function NexusStatus({ state, activeTool }: NexusStatusProps) {
  // Determine color and animation based on state
  const getConfig = () => {
    switch (state) {
      case 'listening':
        return { color: 'bg-emerald-500', pulse: true, label: 'Listening...' };
      case 'thinking':
        return { color: 'bg-blue-500', pulse: true, label: 'Thinking...' };
      case 'speaking':
        return { color: 'bg-indigo-500', pulse: true, label: 'Speaking...' };
      case 'tool_running':
        return { color: 'bg-amber-500', pulse: true, label: `Running ${activeTool || 'tool'}...` };
      case 'interrupted':
        return { color: 'bg-rose-500', pulse: false, label: 'Interrupted' };
      case 'idle':
      default:
        return { color: 'bg-slate-400', pulse: false, label: 'Idle' };
    }
  };

  const config = getConfig();

  return (
    <div className="flex items-center space-x-3 bg-slate-900/50 rounded-full px-4 py-2 border border-slate-700/50 backdrop-blur-md">
      <div className="relative flex h-3 w-3">
        {config.pulse && (
          <motion.span 
            className={`absolute inline-flex h-full w-full rounded-full opacity-75 ${config.color}`}
            animate={{ scale: [1, 2, 1], opacity: [0.7, 0, 0.7] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
          />
        )}
        <span className={`relative inline-flex rounded-full h-3 w-3 ${config.color}`} />
      </div>
      <span className="text-sm font-medium text-slate-200 uppercase tracking-wider text-xs">
        {config.label}
      </span>
    </div>
  );
}
