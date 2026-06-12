import React from 'react';
import { motion } from 'framer-motion';

export type NexusVoiceState = string;

interface NexusStatusProps {
  state: NexusVoiceState;
  activeTool?: string;
}

export function NexusStatus({ state, activeTool }: NexusStatusProps) {
  // Determine color and animation based on state
  const getConfig = () => {
    switch (state) {
      case 'listening':
        return { color: 'bg-emerald-500', pulse: true, label: 'LISTENING' };
      case 'thinking':
        return { color: 'bg-blue-500', pulse: true, label: 'THINKING' };
      case 'speaking':
        return { color: 'bg-indigo-500', pulse: true, label: 'SPEAKING' };
      case 'interrupted':
        return { color: 'bg-rose-500', pulse: false, label: 'INTERRUPTED' };
      case 'idle':
        return { color: 'bg-slate-400', pulse: false, label: 'IDLE' };
      default:
        // For custom tool states like "SEARCHING WEB", "CONSULTING ORACLE"
        return { color: 'bg-amber-500', pulse: true, label: state };
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
