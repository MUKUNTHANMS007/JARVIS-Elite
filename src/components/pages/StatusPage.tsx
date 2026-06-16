import React, { useEffect, useState } from "react";
import { motion } from "motion/react";
import { HUB_URL } from "../../utils/apiConfig";

interface StatusPageProps {
  systemStatus: {
    cpu: number, 
    ram: number, 
    disk: number, 
    energy: number, 
    temp: number, 
    uptime: string,
    services?: { name: string, status: string }[]
  } | null;
  timerEvent?: { event: string; duration?: number } | null;
}

export function StatusPage({ systemStatus, timerEvent }: StatusPageProps) {
  const [githubActivity, setGithubActivity] = useState<any[]>([]);
  const [leetcodeStats, setLeetcodeStats] = useState<any>(null);
  const [workStats, setWorkStats] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  // stats uses the global systemStatus or the locally fetched workStats as fallback
  const stats = systemStatus || workStats || { cpu: 12, ram: 45, disk: 22, energy: 88, temp: 42, uptime: "14d" };
  const uptime = stats.uptime || "0m";

  useEffect(() => {
    const fetchWorkData = async () => {
      try {
        const [ghRes, statsRes] = await Promise.all([
          fetch(`${HUB_URL}/api/work/github`),
          fetch(`${HUB_URL}/api/routine/stats`)
        ]);
        
        const [ghData, statsData] = await Promise.all([ghRes.json(), statsRes.json()]);
        setGithubActivity(ghData);
        setLeetcodeStats({ streak: statsData.leetcode_streak, gmail: statsData.gmail_count });
        setWorkStats(statsData); // Some stats like uptime might be here
      } catch (err) {
        console.error("Failed to fetch work data:", err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchWorkData();
    const interval = setInterval(fetchWorkData, 15000); // Update every 15s
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-12 animate-in fade-in slide-in-from-bottom-4 duration-1000 ease-out">
      
      {/* Page Header */}
      <div className="flex justify-between items-end px-1">
        <div>
          <label className="text-[10px] uppercase tracking-[0.3em] font-black text-zinc-400 mb-2 block">Platform Engine</label>
          <h1 className="text-5xl font-semibold tracking-tight text-black">SYSTEM STATUS</h1>
        </div>
        <div className="text-right">
          <label className="text-[10px] uppercase tracking-[0.2em] font-black text-zinc-400 block mb-1">Node Uptime</label>
          <p className="text-3xl font-light tracking-tighter text-black">{uptime}</p>
        </div>
      </div>

      {/* Core Metrics Bento Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        
        {/* CPU Usage Circular Gauge */}
        <div className="bg-surface-container-lowest p-10 rounded-3xl border border-black/5 flex flex-col items-center justify-center space-y-8 shadow-sm hover:shadow-xl transition-all duration-500 group">
          <div className="relative w-48 h-48 flex items-center justify-center">
            <svg className="w-full h-full transform -rotate-90">
              <circle 
                className="text-zinc-50" 
                cx="96" cy="96" fill="transparent" r="88" 
                stroke="currentColor" strokeWidth="4"
              />
              <motion.circle 
                initial={{ strokeDashoffset: 552 }}
                animate={{ strokeDashoffset: 552 - (552 * (stats.cpu / 100)) }}
                transition={{ duration: 1.5, ease: "easeOut" }}
                className="text-primary" 
                cx="96" cy="96" fill="transparent" r="88" 
                stroke="currentColor" strokeDasharray="552" strokeWidth="4" 
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <motion.span 
                initial={{ opacity: 0, scale: 0.5 }}
                animate={{ opacity: 1, scale: 1 }}
                className="text-4xl font-bold tracking-tighter"
              >
                {Math.round(stats.cpu)}%
              </motion.span>
              <label className="text-[10px] uppercase tracking-[0.2em] font-black text-zinc-400">CPU Usage</label>
            </div>
          </div>
          <div className="text-center group-hover:scale-105 transition-transform">
            <p className="text-sm font-black tracking-tight text-black">Neural Architecture</p>
            <p className="text-[10px] uppercase font-bold text-zinc-400 tracking-widest mt-1">Multi-Core Balanced</p>
          </div>
        </div>

        {/* Memory Load Progress Bar */}
        <div className="bg-surface-container-lowest p-10 rounded-3xl border border-black/5 flex flex-col justify-between shadow-sm hover:shadow-xl transition-all duration-500">
          <div className="space-y-1">
            <label className="text-[10px] uppercase tracking-[0.2em] font-black text-zinc-400">Memory Load</label>
            <h3 className="text-4xl font-bold tracking-tighter text-black">
              {((stats.ram / 100) * 16).toFixed(1)} <span className="text-sm font-black text-zinc-300 uppercase ml-2">/ 16 GB</span>
            </h3>
          </div>
          <div className="mt-12">
            <div className="h-2 w-full bg-zinc-50 rounded-full overflow-hidden shadow-inner border border-black/5">
              <motion.div 
                initial={{ width: 0 }}
                animate={{ width: `${stats.ram}%` }}
                transition={{ duration: 1.2, ease: "easeOut" }}
                className="h-full bg-primary" 
              />
            </div>
            <div className="flex justify-between items-center mt-6">
              <span className="text-[9px] uppercase font-black tracking-widest text-zinc-400">Active Buffer: {stats.ram}%</span>
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-[9px] font-black text-emerald-500 uppercase tracking-widest">Optimized</span>
              </div>
            </div>
          </div>
        </div>

        {/* Storage Capacity Bar Graph */}
        <div className="bg-surface-container-lowest p-10 rounded-3xl border border-black/5 flex flex-col justify-between shadow-sm hover:shadow-xl transition-all duration-500">
          <div className="space-y-1">
            <label className="text-[10px] uppercase tracking-[0.2em] font-black text-zinc-400">Storage Capacity</label>
            <h3 className="text-4xl font-bold tracking-tighter text-black">
              {Math.round(stats.disk)}% <span className="text-sm font-black text-zinc-300 uppercase ml-2">Space Occupied</span>
            </h3>
          </div>
          <div className="flex items-end gap-1.5 h-24 mt-12 px-2 overflow-hidden">
            {[40, 60, 35, 80, 95, 55, 70, 45, 90, 65, 85, 75].map((h, i) => (
              <motion.div 
                key={i}
                initial={{ height: 0 }}
                animate={{ height: `${h}%` }}
                transition={{ duration: 1, delay: i * 0.05, ease: "easeOut" }}
                className={`flex-1 rounded-t-sm transition-all duration-500 ${i === 4 ? 'bg-primary' : 'bg-zinc-100 hover:bg-zinc-200'}`}
              />
            ))}
          </div>
          <p className="text-[9px] uppercase tracking-[0.2em] font-black text-zinc-400 mt-6 pt-6 border-t border-black/5">NVMe Neural Storage Array</p>
        </div>
      </div>


      {/* Neural Core Temp & Network Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        
        {/* Temperature Card with Sparkline */}
        <div className="bg-surface-container-lowest p-10 rounded-3xl border border-black/5 shadow-sm hover:shadow-xl transition-all duration-500">
          <div className="flex justify-between items-start mb-8">
            <div>
              <label className="text-[10px] uppercase tracking-[0.2em] font-black text-zinc-400">Neural Core Temperature</label>
              <h3 className="text-3xl font-bold tracking-tighter text-black mt-2">{stats.temp}°C</h3>
            </div>
            <span className="px-4 py-1.5 bg-emerald-50 text-[9px] font-black uppercase tracking-widest text-emerald-600 rounded-full border border-emerald-100 flex items-center gap-2">
              <span className="w-1 h-1 rounded-full bg-emerald-500" />
              Thermal Stable
            </span>
          </div>
          <div className="h-24 w-full relative">
            <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 400 100">
              <defs>
                <linearGradient id="tempGradient" x1="0%" x2="0%" y1="0%" y2="100%">
                  <stop offset="0%" stopColor="black" stopOpacity="0.05" />
                  <stop offset="100%" stopColor="black" stopOpacity="0" />
                </linearGradient>
              </defs>
              <motion.path 
                initial={{ pathLength: 0, opacity: 0 }}
                animate={{ pathLength: 1, opacity: 1 }}
                transition={{ duration: 2, ease: "easeInOut" }}
                d="M0 70 Q 50 65, 100 68 T 200 60 T 300 62 T 400 65" 
                fill="none" 
                stroke="black" 
                strokeWidth="2" 
              />
              <path d="M0 70 Q 50 65, 100 68 T 200 60 T 300 62 T 400 65 V 100 H 0 Z" fill="url(#tempGradient)" />
            </svg>
          </div>
        </div>

        {/* Network Stats Card */}
        <div className="bg-surface-container-lowest p-10 rounded-3xl border border-black/5 flex flex-col justify-between shadow-sm hover:shadow-xl transition-all duration-500">
          <div>
            <label className="text-[10px] uppercase tracking-[0.2em] font-black text-zinc-400">Network Throughput</label>
            <div className="grid grid-cols-2 mt-8 gap-8">
              <div>
                <div className="flex items-center gap-2 text-zinc-400 mb-2">
                  <span className="material-symbols-outlined text-sm">download</span>
                  <span className="text-[9px] uppercase font-black tracking-widest">Downlink</span>
                </div>
                <p className="text-2xl font-bold tracking-tighter text-black truncate">854.2 Mbps</p>
              </div>
              <div>
                <div className="flex items-center gap-2 text-zinc-400 mb-2">
                  <span className="material-symbols-outlined text-sm">upload</span>
                  <span className="text-[9px] uppercase font-black tracking-widest">Uplink</span>
                </div>
                <p className="text-2xl font-bold tracking-tighter text-black truncate">120.5 Mbps</p>
              </div>
            </div>
          </div>
          <div className="pt-8 border-t border-black/5 mt-8 flex justify-between items-center group cursor-pointer">
            <span className="text-[9px] uppercase font-black text-zinc-400 tracking-[0.2em]">Global Mesh Connection</span>
            <div className="flex items-center gap-2">
              <span className="text-[9px] font-black text-zinc-900">ACTIVE</span>
              <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
            </div>
          </div>
        </div>
      </div>

      {/* Active Processes Section */}
      <div className="space-y-8">
        <div className="flex items-center gap-3 px-1">
          <label className="text-[10px] uppercase tracking-[0.3em] font-black text-zinc-400">Neural Tasking</label>
          <div className="h-px flex-1 bg-black/5" />
          <h2 className="text-xs font-black uppercase tracking-widest text-black">Active Processes</h2>
        </div>

        <div className="bg-surface-container-lowest rounded-[32px] overflow-hidden border border-black/5 shadow-sm">
          <div className="divide-y divide-black/5">
            {(stats.services || [
              { name: "Vision Engine", status: "Active", desc: "Object detection & spatial mapping", icon: "visibility" },
              { name: "Voice Synthesizer", status: "Active", desc: "Natural language audio processing", icon: "speech_to_text" },
              { name: "Language Model", status: "Active", desc: "Cognitive synthesis & reasoning", icon: "neurology" }
            ]).map((service: any, i: number) => (
              <motion.div 
                key={service.name}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1 }}
                className="flex items-center justify-between p-8 hover:bg-zinc-50/50 transition-colors group cursor-pointer"
              >
                <div className="flex items-center gap-6">
                  <div className="w-12 h-12 rounded-2xl bg-zinc-50 flex items-center justify-center group-hover:scale-110 transition-transform duration-500">
                    <span className="material-symbols-outlined text-black">{service.icon || 'settings_input_component'}</span>
                  </div>
                  <div>
                    <p className="text-base font-bold text-black tracking-tight">{service.name}</p>
                    <p className="text-[10px] uppercase text-zinc-400 font-bold tracking-widest mt-1">{service.desc || 'System Operational Module'}</p>
                  </div>
                </div>
                <div className="flex items-center gap-10">
                  <div className="text-right hidden sm:block">
                    <p className="text-[9px] uppercase text-zinc-400 font-black tracking-widest mb-1">Load</p>
                    <p className="text-sm font-bold text-black">{(Math.random() * 20 + 2).toFixed(1)}%</p>
                  </div>
                  <div className="flex items-center gap-3 px-5 py-2 bg-emerald-50 rounded-full border border-emerald-100">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="text-[10px] font-black text-emerald-600 tracking-wider uppercase">{service.status || 'ACTIVE'}</span>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>

    </div>
  );
}
