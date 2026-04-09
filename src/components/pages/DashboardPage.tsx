import { motion, AnimatePresence } from "motion/react";
import React from "react";
import { controlSpotify } from "../../hooks/useBriefing";
import { HUB_URL } from "../../utils/apiConfig";

interface DashboardPageProps {
  today: string;
  energyLevel: number;
  systemStatus: any;
  stats: any;
  isVisionEnabled: boolean;
  visionType: 'camera' | 'screen';
  startVision: (type: 'camera' | 'screen') => void;
  stopVision: () => void;
  videoRef: React.RefObject<HTMLVideoElement | null>;
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  isConnected: boolean;
  isRecording: boolean;
  startRecording: () => void;
  stopRecording: () => void;
  isThinking: boolean;
  setIsThinking: (val: boolean) => void;
  messages: any[];
  reconnect: () => void;
  scrollRef: React.RefObject<HTMLDivElement | null>;
  sendTextMessage: (text: string, imageData?: string | null) => void;
  setActivePage?: (page: any) => void;
}

/**
 * JARVIS ProgressBar: Reusable, high-fidelity progress tracker
 * with animated width and dynamic colors.
 */
const ProgressBar = ({ label, current, total, colorClass, delay = 0 }: any) => {
  // Static mapping to avoid Tailwind purging dynamic color generation
  const bgColorMap: Record<string, string> = {
    'text-emerald-600': 'bg-emerald-600',
    'text-amber-600': 'bg-amber-600',
    'text-rose-600': 'bg-rose-600',
    'text-primary': 'bg-primary'
  };
  
  const bgColor = bgColorMap[colorClass] || 'bg-primary';

  return (
    <div>
      <div className="flex justify-between text-[10px] font-bold uppercase tracking-widest mb-1">
        <span className={colorClass}>{label}</span>
        <span className="opacity-70">{current}/{total}</span>
      </div>
      <div className="h-1.5 w-full bg-surface-container-low rounded-full overflow-hidden">
        <motion.div 
          initial={{ width: 0 }} 
          animate={{ width: `${Math.min((current / total) * 100, 100)}%` }} 
          transition={{ duration: 1.5, ease: "circOut", delay }}
          className={`h-full ${bgColor}`} 
        />
      </div>
    </div>
  );
};

export function DashboardPage(props: DashboardPageProps) {
  const { 
    today, energyLevel, systemStatus, stats, isVisionEnabled, visionType, 
    videoRef, canvasRef, isConnected, isRecording, isThinking, setIsThinking, 
    messages, reconnect, scrollRef, sendTextMessage, setActivePage,
    startRecording, stopRecording, startVision, stopVision
  } = props;
  
  const leetcode = stats?.leetcode || { total_solved: 250, ranking: 5000, easy: 138, medium: 102, hard: 10 };
  const inboxCount = stats?.unread_mail || 0;
  const spotifyStatus = stats?.spotify_track || "Inactive";
  const spotifyImage = stats?.spotify_image || null;
  const reminderCount = stats?.reminder_count || 0;

  // --- 2026 FOCUS MODE PROTOCOL ---
  const handleInitiateRoutine = async () => {
    if (isThinking) return;
    
    // 1. Neural Handshake: Trigger Brain Animation
    setIsThinking(true);
    
    try {
      // 2. Dispatch Multi-Tool Routine (Parallel Spotify + LeetCode)
      const res = await fetch(`${HUB_URL}/api/routine/focus`, { method: "POST" });
      const data = await res.json();
      
      // 3. Neural Briefing: Inject response into TTS stream
      if (data.audio_briefing) {
        sendTextMessage(data.audio_briefing);
      }
      
      console.log("[Jarvis Protocol] Focus topic identified:", data.suggested_tag);
    } catch (err) {
      console.error("[Jarvis Routine] Focus handshake failed:", err);
    } finally {
      // 4. Resolve Handshake
      setIsThinking(false);
    }
  };

  // Dynamic Energy Theming Logic
  const energyColor = energyLevel > 50 ? 'text-primary' : energyLevel > 20 ? 'text-amber-500' : 'text-rose-500';
  const energyBg = energyLevel > 50 ? 'bg-primary' : energyLevel > 20 ? 'bg-amber-500' : 'bg-rose-500';
  const energyStroke = energyLevel > 50 ? 'text-primary' : energyLevel > 20 ? 'text-amber-500' : 'text-rose-500';

  return (
    <div className="space-y-16 animate-in fade-in slide-in-from-bottom-4 duration-1000 ease-out">
      
      {/* Hero Section */}
      <header className="grid grid-cols-1 md:grid-cols-2 gap-8 items-end">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-secondary mb-4">{today}</p>
          <motion.h1 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className={`text-5xl md:text-6xl font-semibold tracking-tight ${energyColor} transition-colors duration-700`}
          >
            {(() => {
              const hour = new Date().getHours();
              if (hour >= 5 && hour < 12) return "Good Morning, Sir.";
              if (hour >= 12 && hour < 17) return "Good Afternoon, Sir.";
              if (hour >= 17 && hour < 22) return "Good Evening, Sir.";
              return "Night Owl Protocol, Sir?";
            })()}
          </motion.h1>
          <p className="mt-4 text-on-surface-variant text-lg max-w-md leading-relaxed opacity-80">
            The residence is operating at optimal efficiency. Security protocols are active and energy reserves are at {energyLevel}%.
          </p>
        </div>
        <div className="flex md:justify-end">
          <div className="bg-surface-container-lowest p-8 rounded-xl flex items-center gap-6 w-full md:w-auto shadow-sm">
            <div className="relative w-20 h-20">
              <svg className="ring-progress w-full h-full" viewBox="0 0 36 36">
                <path className="text-surface-container-highest stroke-current" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" strokeWidth="2"></path>
                <motion.path 
                  initial={{ strokeDasharray: "0, 100" }}
                  animate={{ strokeDasharray: `${energyLevel}, 100` }}
                  className={`${energyStroke} stroke-current transition-colors duration-700`} d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" strokeLinecap="round" strokeWidth="2"
                ></motion.path>
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-lg font-semibold">{energyLevel}%</span>
              </div>
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.1em] text-secondary mb-1">Energy Reserve</p>
              <p className="text-sm text-on-surface-variant leading-tight font-medium">Solar storage active.<br/>Grid bypass enabled.</p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Bento Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        
        {/* GitHub Pulse - Real-time Repository Tracking */}
        <div className="md:col-span-2 bg-surface-container-lowest p-8 rounded-2xl flex flex-col justify-between group cursor-pointer shadow-sm border border-black/5 relative overflow-hidden transition-all hover:shadow-md">
          {/* Animated Gradient Background for Synced Status */}
          <div className="absolute inset-0 bg-linear-to-br from-emerald-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
          
          <div className="flex justify-between items-start relative z-10">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-emerald-50 rounded-xl">
                <span className="material-symbols-outlined text-emerald-600">hub</span>
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-xl font-bold tracking-tight text-zinc-900">GitHub Pulse</h3>
                  <div className="px-2 py-0.5 rounded-full bg-emerald-100 flex items-center gap-1">
                    <div className="w-1 h-1 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="text-[8px] font-bold text-emerald-700 uppercase tracking-tighter">Live</span>
                  </div>
                </div>
                <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-zinc-400">Collaborative Intelligence</p>
              </div>
            </div>
          </div>

          <div className="mt-8 space-y-4 relative z-10">
            {stats?.github && stats.github.length > 0 ? (
              stats.github.map((repo: any, idx: number) => (
                <div key={repo.name} className="flex items-center justify-between p-3 bg-zinc-50 rounded-xl hover:bg-zinc-100 transition-colors">
                  <div className="flex flex-col">
                    <span className="text-sm font-bold text-zinc-800">{repo.name}</span>
                    <span className="text-[10px] text-zinc-500 font-medium truncate max-w-[200px]">
                      {repo.last_commit}
                    </span>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-1">
                      <span className="material-symbols-outlined text-[14px] text-amber-500">star</span>
                      <span className="text-xs font-bold">{repo.stars}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <span className="material-symbols-outlined text-[14px] text-rose-500">error</span>
                      <span className="text-xs font-bold">{repo.issues}</span>
                    </div>
                    <span className="text-[9px] font-mono bg-zinc-200 px-1.5 py-0.5 rounded text-zinc-600">
                      {repo.sha}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="flex flex-col items-center justify-center py-4 opacity-50">
                <span className="material-symbols-outlined animate-spin text-zinc-400">sync</span>
                <p className="text-[10px] font-bold uppercase tracking-widest mt-2">Connecting to GitHub...</p>
              </div>
            )}
          </div>
        </div>

        {/* LeetCode Mastery - Neural Sync Enabled */}
        <div className="md:col-span-2 bg-surface-container-lowest p-8 rounded-2xl shadow-sm border border-black/5 group relative overflow-hidden transition-all hover:shadow-md cursor-pointer">
          {/* Animated Gradient Background */}
          <div className="absolute inset-0 bg-linear-to-br from-amber-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
          
          <div className="flex justify-between items-start mb-6 relative z-10">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-surface-container-low rounded-xl">
                <span className={`material-symbols-outlined ${energyColor}`}>terminal</span>
              </div>
              <div>
                <div className="flex items-center gap-2">
                   <h3 className="text-lg font-semibold tracking-tight">LeetCode Mastery</h3>
                   {leetcode.total_solved > 0 && (
                     <div className="px-2 py-0.5 rounded-full bg-emerald-100 flex items-center gap-1">
                        <div className="w-1 h-1 rounded-full bg-emerald-500 animate-pulse" />
                        <span className="text-[8px] font-bold text-emerald-700 uppercase tracking-tighter">Synced</span>
                     </div>
                   )}
                </div>
                <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-secondary">Placement Intelligence 2.0</p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-2xl font-light tracking-tighter">{leetcode.streak}</p>
              <p className="text-[10px] font-bold uppercase tracking-widest text-secondary">Day Streak</p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.1em] text-secondary mb-1">Total Solved</p>
              <motion.p 
                key={leetcode.total_solved}
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                className="text-5xl font-light tracking-tighter"
              >
                {leetcode.total_solved}
              </motion.p>
              <p className="text-[10px] font-medium text-secondary/60 mt-2 italic">Refreshed from official profile.</p>
            </div>
            <div className="space-y-4">
              <ProgressBar label="Easy" current={leetcode.easy} total={300} colorClass="text-emerald-600" delay={0.1} />
              <ProgressBar label="Medium" current={leetcode.medium} total={200} colorClass="text-amber-600" delay={0.2} />
              <ProgressBar label="Hard" current={leetcode.hard} total={50} colorClass="text-rose-600" delay={0.3} />
            </div>
          </div>
        </div>

        {/* Gemini Intelligence Hub */}
        <div 
          onClick={() => setActivePage?.('history')}
          className="md:col-span-2 bg-surface-container-lowest p-8 rounded-2xl flex flex-col justify-between shadow-sm cursor-pointer group relative overflow-hidden border border-black/5 transition-all hover:shadow-md"
        >
          {/* Animated Gradient Background */}
          <div className="absolute inset-0 bg-linear-to-br from-indigo-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
          
          <div className="flex justify-between items-start relative z-10">
            <div className="p-3 bg-surface-container-low rounded-xl w-fit">
              <span className={`material-symbols-outlined ${energyColor}`}>psychology</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1 bg-surface-container-low rounded-full">
               <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></div>
               <span className="text-[10px] font-bold uppercase tracking-widest opacity-60">Neural Sync</span>
            </div>
          </div>
          <div className="mt-8">
            <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-secondary mb-4">GMAIL EXECUTIVE BRIEFING</h3>
            <AnimatePresence mode="wait">
              <motion.p 
                key={stats?.intelligence_briefing}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-lg font-medium tracking-tight leading-relaxed text-balance"
              >
                {stats?.intelligence_briefing || "Scanning your PSG iTech intelligence layer..."}
              </motion.p>
            </AnimatePresence>
          </div>
          <div className="mt-6 pt-6 border-t border-black/5 flex justify-between items-center opacity-60 group-hover:opacity-100 transition-opacity">
            <span className="text-[10px] font-bold uppercase tracking-widest">Confidence: 98%</span>
            <span className="material-symbols-outlined text-sm">arrow_right_alt</span>
          </div>
        </div>

        {/* Neural Reminder Pulse */}
        <div 
          onClick={() => setActivePage?.('calendar')}
          className="bg-surface-container-lowest p-8 rounded-2xl flex flex-col justify-between shadow-sm cursor-pointer group relative overflow-hidden border border-black/5 transition-all hover:shadow-md"
        >
          {/* Animated Gradient Background */}
          <div className="absolute inset-0 bg-linear-to-br from-rose-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
          
          <div className="p-3 bg-rose-50 rounded-xl w-fit relative z-10">
            <span className="material-symbols-outlined text-rose-600">event_note</span>
          </div>
          <div className="mt-8 relative z-10">
            <p className="text-5xl font-light tracking-tighter">{reminderCount}</p>
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-zinc-400 mt-2">Active Reminders</p>
          </div>
        </div>

        {/* Network Card */}
        <div className="bg-surface-container-lowest p-8 rounded-2xl flex flex-col justify-between shadow-sm group relative overflow-hidden border border-black/5 transition-all hover:shadow-md">
          {/* Animated Gradient Background */}
          <div className="absolute inset-0 bg-linear-to-br from-sky-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
          
          <div className="flex justify-between items-center mb-8 relative z-10">
            <div className="p-3 bg-sky-50 rounded-xl">
              <span className="material-symbols-outlined text-sky-600">router</span>
            </div>
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
          </div>
          <div className="relative z-10">
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-zinc-400">System Link</p>
            <h4 className="text-xl font-bold mt-1 tracking-tight">Uptime: {systemStatus?.uptime || "14d"}</h4>
          </div>
        </div>

        {/* Quick Action Card (Zero-Latency Focus Mode) */}
        <div 
          onClick={handleInitiateRoutine}
          className={`${energyBg} p-8 rounded-2xl flex flex-col justify-between cursor-pointer group shadow-xl transition-all duration-700 hover:scale-[1.02] relative overflow-hidden`}
        >
          {/* Subtle Shimmer for Focus Mode */}
          <div className="absolute inset-0 bg-linear-to-tr from-white/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700" />
          
          <div className="flex justify-between items-start text-on-primary relative z-10">
            <span className={`material-symbols-outlined ${isThinking ? 'animate-spin-slow' : ''}`}>{isThinking ? 'sync' : 'auto_awesome'}</span>
            <span className="material-symbols-outlined text-sm opacity-50 group-hover:translate-x-1 transition-transform">arrow_forward</span>
          </div>
          <div className="mt-8 text-on-primary relative z-10">
            <h3 className="text-xl font-bold tracking-tight">Core Routine</h3>
            <p className="text-[10px] font-bold opacity-80 mt-1 uppercase tracking-[0.2em] text-primary-container">Initialize Focus Protocol</p>
          </div>
        </div>

        {/* Live Neural Transcript Section - High Fidelity Thinking Animation */}
        <div className="md:col-span-2 bg-white p-8 rounded-2xl shadow-sm border border-black/5 flex flex-col h-[360px] group relative overflow-hidden transition-all hover:shadow-md">
          {/* Animated Gradient Background */}
          <div className="absolute inset-0 bg-linear-to-br from-emerald-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
          
          <div className="flex justify-between items-center mb-6 shrink-0 relative z-10">
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined text-emerald-400">forum</span>
              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-zinc-400">Live Session Hub</p>
            </div>
            {isThinking && (
              <div className="flex gap-1.5 items-center px-3 py-1 bg-surface-container-low rounded-full">
                {[0, 1, 2].map((i) => (
                  <motion.div
                    key={i}
                    animate={{ scale: [1, 1.4, 1], opacity: [0.3, 1, 0.3] }}
                    transition={{ repeat: Infinity, duration: 1.2, delay: i * 0.2 }}
                    className={`w-1.5 h-1.5 rounded-full ${energyBg}`}
                  />
                ))}
              </div>
            )}
            <div className={`w-1.5 h-1.5 rounded-full ${isConnected ? (isRecording ? 'bg-black animate-pulse' : 'bg-green-500') : 'bg-red-500'}`} />
          </div>
          
          <div ref={scrollRef} className="flex-1 overflow-y-auto pr-2 space-y-4 scroll-smooth no-scrollbar">
            {messages.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center opacity-10">
                <span className="material-symbols-outlined text-6xl mb-4">graphic_eq</span>
                <p className="text-[10px] uppercase font-bold tracking-widest">Awaiting acoustic input...</p>
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
                <div className={`max-w-[85%] p-4 rounded-xl ${
                  m.role === 'user' 
                    ? 'bg-surface-container-low text-black rounded-br-none' 
                    : 'bg-white text-black border border-black/5 rounded-bl-none shadow-sm'
                }`}>
                  <p className="text-[12px] font-medium leading-relaxed tracking-tight">{m.content}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Music Feed Integration - Smooth Background Transitions */}
        <div className="md:col-span-2 rounded-2xl overflow-hidden relative shadow-sm border border-black/5 bg-white flex flex-col group transition-all hover:shadow-md">
          {/* Subtle Spotify Indigo Overlay on Hover (Only if no image) */}
          {!spotifyImage && <div className="absolute inset-0 bg-linear-to-br from-indigo-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />}
          
          <AnimatePresence mode="wait">
             <motion.div
               key={spotifyImage}
               initial={{ opacity: 0 }}
               animate={{ opacity: 1 }}
               exit={{ opacity: 0 }}
               transition={{ duration: 0.8 }}
               className="absolute inset-0 bg-cover bg-center"
               style={{ backgroundImage: spotifyImage ? `url(${spotifyImage})` : 'none' }}
             />
          </AnimatePresence>
          
          <div className={`relative p-10 h-full flex flex-col justify-between transition-colors duration-700 flex-1 ${spotifyImage ? 'bg-black/40 backdrop-blur-[4px]' : 'bg-white'}`}>
            <div className={spotifyImage ? 'text-white' : 'text-black'}>
              <p className={`text-[8px] font-bold uppercase tracking-[0.4em] mb-4 opacity-70 ${spotifyImage ? 'text-white' : 'text-zinc-400'}`}>AUDIO_LINK_ACTIVE</p>
              <h3 className="text-3xl font-semibold tracking-tighter leading-none line-clamp-1">
                {spotifyStatus === "Premium Required" ? "Neural Block" : (spotifyStatus !== "Inactive" && spotifyStatus !== "Standby" ? spotifyStatus : 'Vibes Offline')}
              </h3>
              <p className={`text-xs font-bold uppercase tracking-widest mt-2 ${spotifyImage ? 'text-white/80' : energyColor}`}>
                {spotifyStatus === "Premium Required" ? "Premium API Required" : (spotifyStatus !== "Inactive" && spotifyStatus !== "Standby" ? "Streaming Now" : 'Select a frequency')}
              </p>
            </div>
            
            <div className="flex items-center gap-4">
              <button 
                onClick={() => controlSpotify('prev')}
                className={`w-10 h-10 rounded-full flex items-center justify-center shadow-xl transition-all hover:scale-110 active:scale-95 ${spotifyImage ? 'bg-white/20 text-white backdrop-blur-md' : 'bg-surface-container text-zinc-600'}`}
              >
                <span className="material-symbols-outlined text-xl">skip_previous</span>
              </button>
              
              <button 
                onClick={() => controlSpotify(spotifyStatus !== "Inactive" && spotifyStatus !== "Standby" ? 'pause' : 'play')}
                className={`w-14 h-14 rounded-full flex items-center justify-center shadow-2xl transition-transform hover:scale-110 active:scale-95 ${spotifyImage ? 'bg-white text-black' : `${energyBg} text-on-primary`}`}
              >
                <span className="material-symbols-outlined text-2xl font-bold">
                  {spotifyStatus !== "Inactive" && spotifyStatus !== "Standby" ? 'pause' : 'play_arrow'}
                </span>
              </button>

              <button 
                onClick={() => controlSpotify('next')}
                className={`w-10 h-10 rounded-full flex items-center justify-center shadow-xl transition-all hover:scale-110 active:scale-95 ${spotifyImage ? 'bg-white/20 text-white backdrop-blur-md' : 'bg-surface-container text-zinc-600'}`}
              >
                <span className="material-symbols-outlined text-xl">skip_next</span>
              </button>
              <div className="flex-1">
                 <p className={`text-[10px] font-bold uppercase tracking-widest ${spotifyImage ? 'text-white/60' : 'text-zinc-400'}`}>Direct Link Activated</p>
                 <div className={`h-1 w-full mt-2 rounded-full overflow-hidden ${spotifyImage ? 'bg-white/20' : 'bg-surface-container'}`}>
                   <motion.div 
                     initial={{ width: 0 }}
                     animate={{ width: (spotifyStatus !== "Inactive" && spotifyStatus !== "Standby") ? "100%" : "0%" }}
                     className={`h-full ${spotifyImage ? 'bg-white' : energyBg} opacity-50`} 
                     transition={{ duration: 1.5 }}
                   />
                 </div>
              </div>
            </div>
          </div>
        </div>

      </div>

      {/* System Logs */}
      <section className="mt-24 pb-32">
        <div className="flex justify-between items-end mb-8">
          <h2 className="text-xs font-bold uppercase tracking-[0.2em] text-secondary">System Logs & Activity</h2>
        </div>
        <div className="bg-surface-container-lowest rounded-2xl divide-y divide-surface-container border border-black/5 shadow-sm overflow-hidden">
          {[
            { icon: 'lock', title: 'Main Entrance Locked', desc: 'Confirmed by Jarvis Protocol A-1', time: '08:42 AM', color: 'text-zinc-600', bg: 'bg-zinc-50' },
            { icon: 'mail', title: `Inbox Scan: ${inboxCount} items`, desc: 'Gmail Sync complete', time: 'Just Now', color: 'text-indigo-600', bg: 'bg-indigo-50' },
            { icon: 'event', title: `${reminderCount} Reminders Active`, desc: 'Neural Sync active', time: 'Just Now', color: 'text-rose-600', bg: 'bg-rose-50' }
          ].map((log, i) => (
            <div key={i} className="p-6 flex items-center gap-6 group cursor-pointer relative overflow-hidden transition-all duration-300">
               {/* Hover Accent */}
              <div className="absolute inset-0 bg-zinc-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
              
              <div className={`w-10 h-10 rounded-xl ${log.bg} flex items-center justify-center ${log.color} relative z-10 transition-transform group-hover:scale-110`}>
                <span className="material-symbols-outlined text-lg">{log.icon}</span>
              </div>
              <div className="flex-1 relative z-10">
                <p className="text-sm font-bold text-zinc-800">{log.title}</p>
                <p className="text-xs text-zinc-500 font-medium">{log.desc}</p>
              </div>
              <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-400 relative z-10">{log.time}</span>
            </div>
          ))}
        </div>
      </section>

    </div>
  );
}
