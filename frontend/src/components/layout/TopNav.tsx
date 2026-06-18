"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useNexus } from "@/contexts/NexusContext";
import { useVoice } from "@/contexts/VoiceContext";
import {
  ShieldAlert,
  LayoutDashboard,
  MessageSquare,
  Activity,
  BrainCircuit,
  Bot,
  Workflow,
  Settings,
  Wifi,
  WifiOff,
  Mic,
  MicOff,
} from "lucide-react";

// Engine mode display config — sourced from backend engine_mode WebSocket message
const ENGINE_CONFIG: Record<string, { label: string; color: string }> = {
  gemini_live: { label: "Gemini Live", color: "#00d4ff" },
  groq:        { label: "Groq",        color: "#f59e0b" },
  text:        { label: "Text Mode",   color: "#a78bfa" },
  unknown:     { label: "---",         color: "#52525b" },
};

export function TopNav() {
  const pathname = usePathname();
  const { voiceState, uiMode, setUiMode } = useNexus();
  const { isConnected, isListening, micCaptured, activeEngine } = useVoice();

  // Real mic state: only active if both VAD is listening AND browser mic stream is held
  const micActive = isListening && micCaptured;
  const engineCfg = ENGINE_CONFIG[activeEngine] ?? ENGINE_CONFIG.unknown;

  const navItems = [
    { name: "Dashboard", href: "/",           icon: LayoutDashboard },
    { name: "Chat",      href: "/chat",       icon: MessageSquare },
    { name: "Trace",     href: "/trace",      icon: Activity },
    { name: "Memory",    href: "/memory",     icon: BrainCircuit },
    { name: "Agents",    href: "/agents",     icon: Bot },
    { name: "Automation",href: "/automation", icon: Workflow },
    { name: "Settings",  href: "/settings",   icon: Settings },
  ];

  const stateColors: Record<string, string> = {
    idle:      "#10b981",
    listening: "#00FFFF",
    speaking:  "#6137FF",
    thinking:  "#f59e0b",
  };
  const stateColor = stateColors[voiceState] || stateColors.idle;

  return (
    <header className="flex items-center justify-between bg-[#06060c] border-b border-white/[0.06] px-4 h-12 shrink-0 shadow-[0_0_20px_rgba(0,0,0,0.8)] z-20 relative">
      {/* Subtle top accent line */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-[#6137FF]/40 to-transparent" />

      <div className="flex items-center gap-5">
        {/* Logo */}
        <div className="flex items-center gap-2 pr-5 border-r border-white/[0.06]">
          <ShieldAlert className="text-[#ff3366]" size={18} />
          <span className="text-[13px] font-quantico font-bold tracking-[0.35em] text-white uppercase">NEXUS</span>
          <span className="text-[13px] font-quantico font-bold tracking-[0.35em] text-[#00FFFF] uppercase">OS</span>
        </div>

        {/* Nav Links */}
        <nav className="flex items-center gap-0.5">
          {navItems.map((item) => {
            let isActive = false;

            if (item.name === "Dashboard") {
              isActive = pathname === "/" && uiMode === "voice";
            } else if (item.name === "Chat") {
              isActive = pathname === "/" && uiMode === "chat";
            } else {
              isActive = pathname.startsWith(item.href);
            }

            const Icon = item.icon;
            const linkClass = `flex items-center gap-1.5 px-3 py-1.5 transition-all rounded-none border-b-2 text-[9px] font-bold uppercase tracking-[0.15em] ${
              isActive
                ? "border-[#00FFFF] text-white bg-[#00FFFF]/5"
                : "border-transparent text-zinc-500 hover:text-zinc-300 hover:border-zinc-700"
            }`;

            if (item.name === "Dashboard" || item.name === "Chat") {
              return (
                <Link
                  key={item.name}
                  href="/"
                  onClick={() => {
                    if (item.name === "Chat") {
                      setUiMode("chat");
                    } else {
                      setUiMode("voice");
                    }
                  }}
                  className={linkClass}
                >
                  <Icon size={13} className={isActive ? "text-[#00FFFF]" : "text-zinc-600"} />
                  {item.name}
                </Link>
              );
            }

            return (
              <Link
                key={item.name}
                href={item.href}
                className={linkClass}
              >
                <Icon size={13} className={isActive ? "text-[#00FFFF]" : "text-zinc-600"} />
                {item.name}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Right: Real Status Indicators */}
      <div className="flex items-center gap-3 pl-5 border-l border-white/[0.06]">

        {/* Mic State — reflects actual browser MediaStream + VAD state */}
        <div
          title={micActive ? "Microphone active" : "Microphone off"}
          className={`flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-widest transition-colors ${
            micActive ? "text-[#00FFFF]" : "text-zinc-600"
          }`}
        >
          {micActive ? <Mic size={12} /> : <MicOff size={12} />}
          <span>{micActive ? "🎤 On" : "🔇 Off"}</span>
        </div>

        <div className="w-px h-4 bg-white/[0.06]" />

        {/* Engine Mode — sourced from backend engine_mode WS message */}
        <div
          title={`Active engine: ${engineCfg.label}`}
          className="flex items-center gap-1.5"
        >
          <div
            className="w-1.5 h-1.5 rounded-full"
            style={{ background: engineCfg.color, boxShadow: `0 0 5px ${engineCfg.color}` }}
          />
          <span
            className="text-[9px] font-bold uppercase tracking-widest"
            style={{ color: engineCfg.color }}
          >
            {engineCfg.label}
          </span>
        </div>

        <div className="w-px h-4 bg-white/[0.06]" />

        {/* WS Connection */}
        <div className={`flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-widest ${isConnected ? "text-[#10b981]" : "text-[#ff3366]"}`}>
          {isConnected ? <Wifi size={12} /> : <WifiOff size={12} />}
          <span>{isConnected ? "Connected" : "Offline"}</span>
        </div>

        <div className="w-px h-4 bg-white/[0.06]" />

        {/* Voice State */}
        <div className="flex items-center gap-2">
          <span className="text-[8px] font-quantico font-bold uppercase tracking-[0.2em] text-zinc-500">State</span>
          <div className="flex items-center gap-1.5">
            <div
              className="w-1.5 h-1.5 rounded-full animate-pulse"
              style={{ background: stateColor, boxShadow: `0 0 6px ${stateColor}` }}
            />
            <span className="text-[10px] font-mono font-bold" style={{ color: stateColor }}>
              {voiceState.toUpperCase()}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
