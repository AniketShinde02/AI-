"use client";

import { useEffect, useState } from "react";
import { BrainCircuit, Lock, Search, Trash2, RefreshCw } from "lucide-react";

interface MemoryData {
  preferences?: Record<string, any>;
  facts?: string[];
  [key: string]: any;
}

export default function MemoryPage() {
  const [memory, setMemory] = useState<MemoryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  const fetchMemory = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/memory");
      const data = await res.json();
      setMemory(data);
    } catch {
      setMemory(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMemory();
  }, []);

  const entries = memory
    ? Object.entries(memory).flatMap(([key, value]) => {
        if (typeof value === "object" && value !== null) {
          return Object.entries(value).map(([k, v]) => ({
            category: key,
            key: k,
            value: String(v),
          }));
        }
        return [{ category: "core", key, value: String(value) }];
      })
    : [];

  const filtered = entries.filter(
    (e) =>
      !search ||
      e.key.toLowerCase().includes(search.toLowerCase()) ||
      e.value.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="h-full flex flex-col overflow-hidden p-4 gap-4">
      {/* Header */}
      <div className="flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-[#6137FF]/20 border border-[#6137FF]/40 flex items-center justify-center clip-cut">
            <BrainCircuit size={16} className="text-[#6137FF]" />
          </div>
          <div>
            <h1 className="text-[11px] font-quantico font-bold uppercase tracking-[0.3em] text-white">Memory Vault</h1>
            <p className="text-[9px] font-mono text-zinc-500 uppercase tracking-widest">Persistent Knowledge Store</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchMemory}
            className="w-8 h-8 flex items-center justify-center border border-white/10 text-zinc-400 hover:text-[#00FFFF] hover:border-[#00FFFF]/30 clip-cut-sm transition-all"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
          <div className="flex items-center gap-2 px-3 py-1 bg-[#6137FF]/10 border border-[#6137FF]/30 clip-cut-sm">
            <Lock size={10} className="text-[#6137FF]" />
            <span className="text-[9px] font-bold uppercase tracking-widest text-[#6137FF]">
              {filtered.length} Entries
            </span>
          </div>
        </div>
      </div>

      {/* Search */}
      <div className="relative shrink-0">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-600" />
        <input
          type="text"
          placeholder="Search memory..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full bg-[#06060c] border border-white/10 text-white text-[12px] pl-9 pr-4 py-2 font-mono focus:outline-none focus:border-[#6137FF]/50 clip-cut placeholder:text-zinc-600"
        />
      </div>

      {/* Memory Grid */}
      <div className="flex-1 overflow-y-auto scroll-hide">
        {loading ? (
          <div className="flex items-center justify-center h-full opacity-50">
            <RefreshCw size={24} className="animate-spin text-[#6137FF]" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-4 opacity-40">
            <BrainCircuit size={40} className="text-[#6137FF]" />
            <p className="text-[11px] font-quantico uppercase tracking-widest text-zinc-500">
              {search ? "No Results Found" : "Memory Vault Empty"}
            </p>
            <p className="text-[9px] font-mono text-zinc-600">
              Interact with Nexus to populate the vault
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-2">
            {filtered.map((entry, i) => (
              <div
                key={i}
                className="bg-[#06060c] border border-white/5 hover:border-[#6137FF]/30 clip-cut p-4 flex items-start justify-between gap-4 group transition-all"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[8px] font-bold uppercase tracking-widest text-[#6137FF]/60 px-1.5 py-0.5 border border-[#6137FF]/20 bg-[#6137FF]/5 clip-cut-sm">
                      {entry.category}
                    </span>
                    <span className="text-[10px] font-mono font-bold text-[#00FFFF]">{entry.key}</span>
                  </div>
                  <p className="text-[12px] text-zinc-300 font-sans leading-relaxed truncate">{entry.value}</p>
                </div>
                <button className="opacity-0 group-hover:opacity-100 transition-opacity text-zinc-600 hover:text-[#ff3366] p-1">
                  <Trash2 size={12} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
