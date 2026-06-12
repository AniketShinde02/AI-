"use client";

import React from "react";
import { cn } from "@/lib/utils";

export type LightOrbConfig = {
  volume?: number;
};

export function LightOrb({ volume = 0, className }: LightOrbConfig & { className?: string }) {
  // Scale the orb dynamically based on volume (0 to 1)
  const scale = 1 + volume * 0.2;
  
  return (
    <div className={cn("relative w-full h-full flex items-center justify-center overflow-hidden", className)}>
      <div 
        className="relative flex items-center justify-center transition-transform duration-75 ease-out"
        style={{ transform: `scale(${scale})` }}
      >
        {/* Ambient Glow */}
        <div className="absolute w-56 h-56 bg-indigo-500/20 rounded-full blur-3xl animate-pulse" />
        
        {/* Outer Shell (Simulating Icosahedron Outer) */}
        <div className="absolute w-48 h-48 rounded-full border border-indigo-500/20 animate-[spin_12s_linear_infinite]" />
        <div className="absolute w-48 h-48 rounded-full border border-indigo-500/10" style={{ transform: 'rotateX(60deg)', animation: 'spin 15s linear infinite reverse' }} />
        <div className="absolute w-48 h-48 rounded-full border border-indigo-500/10" style={{ transform: 'rotateY(60deg)', animation: 'spin 18s linear infinite' }} />

        {/* Inner Core (Simulating Icosahedron Inner) */}
        <div className="absolute w-28 h-28 rounded-full border border-indigo-400/40 animate-[spin_6s_linear_infinite]" style={{ borderStyle: 'dashed' }} />
        <div className="absolute w-28 h-28 rounded-full border border-indigo-400/30" style={{ transform: 'rotateX(45deg)', animation: 'spin 8s linear infinite reverse' }} />
        <div className="absolute w-28 h-28 rounded-full border border-indigo-400/30" style={{ transform: 'rotateY(45deg)', animation: 'spin 10s linear infinite' }} />

        {/* Center Node */}
        <div className="w-10 h-10 bg-indigo-500/50 backdrop-blur-md rounded-full shadow-[0_0_30px_rgba(99,102,241,0.8)]" />
      </div>
    </div>
  );
}
