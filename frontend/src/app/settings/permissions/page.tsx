"use client";

import { useEffect, useState } from "react";
import { Shield, CheckCircle, XCircle, RefreshCw, Loader2, Clock } from "lucide-react";

interface Capability {
  id: string;
  name: string;
  description: string;
  category: string;
  enabled: boolean;
}

interface AuditEntry {
  tool: string;
  params: Record<string, unknown>;
  status: string;
  permission: string;
  timestamp: string;
}

const BACKEND = "http://localhost:8001";

const CATEGORY_LABELS: Record<string, string> = {
  applications: "Applications",
  screenshots: "Screenshots",
  keyboard: "Keyboard & Mouse",
  filesystem: "Filesystem",
  browser: "Browser",
  terminal: "Terminal",
};

export default function PermissionsPage() {
  const [caps, setCaps] = useState<Capability[]>([]);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const [cRes, aRes] = await Promise.all([
        fetch(`${BACKEND}/api/capabilities`),
        fetch(`${BACKEND}/api/audit-log?limit=20`),
      ]);
      if (cRes.ok) setCaps(await cRes.json());
      if (aRes.ok) setAudit(await aRes.json());
    } catch { /* offline */ }
    setLoading(false);
  }

  async function toggle(id: string, current: boolean) {
    setToggling(id);
    try {
      const r = await fetch(`${BACKEND}/api/capabilities/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: !current }),
      });
      if (r.ok) {
        setCaps(prev => prev.map(c => c.id === id ? { ...c, enabled: !current } : c));
      }
    } catch { /* offline */ }
    setToggling(null);
  }

  useEffect(() => { load(); }, []);

  const grouped = caps.reduce<Record<string, Capability[]>>((acc, cap) => {
    const cat = cap.category || "system";
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(cap);
    return acc;
  }, {});

  return (
    <div className="min-h-screen bg-[#06060c] text-white font-mono p-6 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 border border-[#6137FF]/60 flex items-center justify-center clip-cut shadow-[0_0_15px_rgba(97,55,255,0.3)]">
            <Shield size={14} className="text-[#6137FF]" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-white tracking-[0.2em] uppercase">Permissions</h1>
            <p className="text-[10px] text-zinc-500 tracking-widest uppercase">Capability Access Control</p>
          </div>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-2 px-3 py-1.5 border border-white/10 hover:border-[#6137FF]/50 text-[10px] text-zinc-400 hover:text-white transition-colors"
        >
          <RefreshCw size={10} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-40 gap-3 text-zinc-500">
          <Loader2 size={16} className="animate-spin" />
          <span className="text-[11px]">Loading capabilities...</span>
        </div>
      ) : (
        <>
          {/* Capability Groups */}
          {Object.keys(grouped).length === 0 ? (
            <div className="text-center text-zinc-500 text-[11px] py-12">
              No capabilities registered yet. Start the backend to initialize.
            </div>
          ) : (
            Object.entries(grouped).map(([cat, items]) => (
              <div key={cat} className="space-y-2">
                <div className="flex items-center gap-2 mb-3">
                  <div className="h-px flex-1 bg-white/5" />
                  <span className="text-[9px] font-bold uppercase tracking-[0.3em] text-zinc-500">
                    {CATEGORY_LABELS[cat] || cat}
                  </span>
                  <div className="h-px flex-1 bg-white/5" />
                </div>
                {items.map(cap => (
                  <div
                    key={cap.id}
                    className={`flex items-center justify-between px-4 py-3 border transition-colors ${
                      cap.enabled
                        ? "border-[#6137FF]/30 bg-[#6137FF]/5 hover:border-[#6137FF]/50"
                        : "border-white/5 bg-black/20 hover:border-white/15"
                    }`}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      {cap.enabled ? (
                        <CheckCircle size={12} className="text-[#00FFFF] shrink-0" />
                      ) : (
                        <XCircle size={12} className="text-zinc-600 shrink-0" />
                      )}
                      <div className="min-w-0">
                        <div className="text-[11px] font-bold text-white">{cap.name}</div>
                        <div className="text-[9px] text-zinc-500 truncate">{cap.description}</div>
                        <div className="text-[8px] text-zinc-700 font-mono mt-0.5">{cap.id}</div>
                      </div>
                    </div>
                    <button
                      onClick={() => toggle(cap.id, cap.enabled)}
                      disabled={toggling === cap.id}
                      className={`relative w-10 h-5 rounded-none border shrink-0 transition-all ${
                        cap.enabled
                          ? "border-[#6137FF] bg-[#6137FF]/20"
                          : "border-white/20 bg-black"
                      }`}
                      aria-label={`Toggle ${cap.name}`}
                    >
                      {toggling === cap.id ? (
                        <Loader2 size={8} className="animate-spin absolute inset-0 m-auto text-zinc-400" />
                      ) : (
                        <div
                          className={`absolute top-0.5 w-4 h-4 transition-all duration-200 ${
                            cap.enabled ? "left-5 bg-[#6137FF]" : "left-0.5 bg-zinc-600"
                          }`}
                        />
                      )}
                    </button>
                  </div>
                ))}
              </div>
            ))
          )}

          {/* Audit Log */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 mb-3">
              <div className="h-px flex-1 bg-white/5" />
              <span className="text-[9px] font-bold uppercase tracking-[0.3em] text-zinc-500">
                Execution Audit Log
              </span>
              <div className="h-px flex-1 bg-white/5" />
            </div>
            {audit.length === 0 ? (
              <div className="text-center text-zinc-600 text-[10px] py-6">No executions logged yet.</div>
            ) : (
              <div className="border border-white/5 divide-y divide-white/5">
                {audit.map((entry, i) => (
                  <div key={i} className="flex items-center gap-3 px-4 py-2.5">
                    <div className={`w-1.5 h-1.5 shrink-0 ${entry.status === "success" ? "bg-[#00FFFF]" : "bg-red-500"}`} />
                    <div className="flex-1 min-w-0">
                      <div className="text-[10px] font-bold text-white">{entry.tool}</div>
                      <div className="text-[9px] text-zinc-600 truncate">
                        {JSON.stringify(entry.params)}
                      </div>
                    </div>
                    <div className="flex items-center gap-1 text-[8px] text-zinc-600 shrink-0">
                      <Clock size={8} />
                      {new Date(entry.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
