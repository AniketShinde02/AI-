"use client";

import { useEffect, useState } from "react";
import { Workflow, Plus, Play, Pause, Trash2, ChevronRight, Zap, Clock, CheckCircle } from "lucide-react";

interface Mission {
  id: string;
  name: string;
  trigger: string;
  actions: string[];
  status: "active" | "paused" | "draft";
  runs: number;
  lastRun: string;
}

const statusColors: Record<string, string> = {
  active: "#00FFFF",
  paused: "#f59e0b",
  draft: "#6137FF",
};

export default function AutomationPage() {
  const [missions, setMissions] = useState<Mission[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchMissions = () => {
    fetch("http://localhost:8001/api/workflows")
      .then((res) => res.json())
      .then((data) => {
        setMissions(data);
        setIsLoading(false);
      })
      .catch((err) => {
        console.error("Failed to fetch workflows", err);
        setIsLoading(false);
      });
  };

  useEffect(() => {
    fetchMissions();
  }, []);

  const handleCreateMission = async () => {
    const id = `mission_${Math.random().toString(36).substr(2, 9)}`;
    const newMission = {
      id,
      name: `New Mission ${id.substr(0, 4)}`,
      trigger: "Manual",
      actions: ["Execute default task"],
      status: "draft",
      runs: 0,
      lastRun: "Never"
    };
    await fetch("http://localhost:8001/api/workflows", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(newMission)
    });
    fetchMissions();
  };

  const toggleMission = async (mission: Mission) => {
    const newStatus = mission.status === "active" ? "paused" : "active";
    await fetch(`http://localhost:8001/api/workflows/${mission.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...mission, status: newStatus })
    });
    fetchMissions();
  };

  const deleteMission = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    await fetch(`http://localhost:8001/api/workflows/${id}`, { method: "DELETE" });
    fetchMissions();
  };

  return (
    <div className="h-full flex flex-col overflow-hidden p-4 gap-4">
      {/* Header */}
      <div className="flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-[#6137FF]/20 border border-[#6137FF]/40 flex items-center justify-center clip-cut">
            <Workflow size={16} className="text-[#6137FF]" />
          </div>
          <div>
            <h1 className="text-[11px] font-quantico font-bold uppercase tracking-[0.3em] text-white">Automation Hub</h1>
            <p className="text-[9px] font-mono text-zinc-500 uppercase tracking-widest">Mission Builder & Pipeline Control</p>
          </div>
        </div>
        <button onClick={handleCreateMission} className="flex items-center gap-2 px-3 py-2 bg-[#6137FF] hover:bg-[#7b5cff] text-white text-[9px] font-bold uppercase tracking-widest clip-cut transition-all shadow-[0_0_15px_rgba(97,55,255,0.3)]">
          <Plus size={12} />
          New Mission
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3 shrink-0">
        {[
          { label: "Active Missions", value: missions.filter((m) => m.status === "active").length, icon: Zap, color: "#00FFFF" },
          { label: "Total Runs", value: missions.reduce((a, b) => a + b.runs, 0), icon: CheckCircle, color: "#6137FF" },
          { label: "Avg Cadence", value: "30m", icon: Clock, color: "#10b981" },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-[#06060c] border clip-cut p-4 flex items-center gap-3" style={{ borderColor: `${color}20` }}>
            <div className="w-8 h-8 flex items-center justify-center border clip-cut-sm" style={{ background: `${color}15`, borderColor: `${color}30` }}>
              <Icon size={14} style={{ color }} />
            </div>
            <div>
              <p className="text-[9px] font-mono text-zinc-500 uppercase tracking-widest">{label}</p>
              <p className="text-xl font-bold font-quantico" style={{ color }}>{value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Mission Cards */}
      <div className="flex-1 overflow-y-auto scroll-hide">
        <div className="flex flex-col gap-3">
          {missions.map((mission) => {
            const color = statusColors[mission.status];
            return (
              <div
                key={mission.id}
                className="bg-[#06060c] border border-white/5 hover:border-white/15 clip-cut p-5 group transition-all"
                style={{ borderColor: mission.status === "active" ? `${color}15` : undefined }}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-[13px] font-bold font-quantico text-white tracking-wide">{mission.name}</span>
                      <span
                        className="text-[8px] font-bold uppercase tracking-widest px-2 py-0.5 border clip-cut-sm"
                        style={{ color, borderColor: `${color}40`, background: `${color}10` }}
                      >
                        {mission.status}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 mb-3">
                      <Clock size={10} className="text-zinc-600" />
                      <span className="text-[10px] font-mono text-zinc-500">{mission.trigger}</span>
                    </div>

                    {/* Action chain */}
                    <div className="flex items-center gap-1 flex-wrap">
                      {mission.actions.map((action, i) => (
                        <div key={i} className="flex items-center gap-1">
                          <span className="text-[9px] font-mono text-zinc-400 bg-black/60 border border-white/5 px-2 py-0.5 clip-cut-sm">
                            {action}
                          </span>
                          {i < mission.actions.length - 1 && (
                            <ChevronRight size={10} className="text-zinc-700" />
                          )}
                        </div>
                      ))}
                    </div>

                    <div className="flex items-center gap-4 mt-3">
                      <span className="text-[9px] font-mono text-zinc-600">
                        Runs: <span className="text-zinc-400">{mission.runs}</span>
                      </span>
                      <span className="text-[9px] font-mono text-zinc-600">
                        Last: <span className="text-zinc-400">{mission.lastRun}</span>
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={(e) => { e.stopPropagation(); toggleMission(mission); }}
                      className="w-8 h-8 flex items-center justify-center border clip-cut-sm transition-all hover:border-[#00FFFF]/40"
                      style={{
                        background: mission.status === "active" ? "#ff336620" : "#00FFFF20",
                        borderColor: mission.status === "active" ? "#ff336640" : "#00FFFF40",
                        color: mission.status === "active" ? "#ff3366" : "#00FFFF",
                      }}
                      title={mission.status === "active" ? "Pause" : "Resume"}
                    >
                      {mission.status === "active" ? <Pause size={12} /> : <Play size={12} />}
                    </button>
                    <button onClick={(e) => deleteMission(e, mission.id)} className="w-8 h-8 flex items-center justify-center border border-white/5 text-zinc-600 hover:text-[#ff3366] hover:border-[#ff3366]/30 clip-cut-sm transition-all">
                      <Trash2 size={12} />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
