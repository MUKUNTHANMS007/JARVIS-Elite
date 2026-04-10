"use client"

import { motion, AnimatePresence } from "motion/react";
import React, { useEffect, useRef, useState } from "react";
import { FocusTimer } from "../shared/FocusTimer";
import { HUB_URL, API_ENDPOINTS } from "../../utils/apiConfig";

interface CorePageProps {
  today: string;
  isConnected: boolean;
  isRecording: boolean;
  isThinking: boolean;
  isSpeaking: boolean;
  messages: any[];
  stats?: any;
  startRecording: () => void;
  stopRecording: () => void;
  reconnect: () => void;
  scrollRef: React.RefObject<HTMLDivElement | null>;
  sendTextMessage: (text: string, imageData?: string | null) => void;
  setActivePage?: (page: any) => void;
  isVisionEnabled: boolean;
  videoRef: React.RefObject<HTMLVideoElement | null>;
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  focusData: any;
  timerEvent?: { event: string; duration?: number } | null;
  startVision: (type: 'camera' | 'screen') => Promise<boolean>;
  stopVision: () => void;
  visionType: 'camera' | 'screen' | null;
}

export function CorePage({ 
  today, isConnected, isRecording, isThinking, isSpeaking, messages, stats, 
  startRecording, stopRecording, reconnect, scrollRef,
  sendTextMessage, isVisionEnabled, videoRef, canvasRef, setActivePage,
  focusData, timerEvent,
  startVision, stopVision, visionType
}: CorePageProps) {
  const [isRecruiterView, setIsRecruiterView] = useState(false);
  const [showHint, setShowHint] = useState(false);
  const [isSpeakingHint, setIsSpeakingHint] = useState(false);
  const [commandText, setCommandText] = useState("");
  const [isGeneratingSchedule, setIsGeneratingSchedule] = useState(false);
  const [scheduleStatus, setScheduleStatus] = useState("");
  const [isMarkedSolved, setIsMarkedSolved] = useState(false);
  const [solveConfirmMode, setSolveConfirmMode] = useState(false);

  // Reset solved state when problem changes day-to-day
  useEffect(() => {
    if (focusData?.active_problem?.completed) {
      setIsMarkedSolved(true);
    } else {
      setIsMarkedSolved(false);
      setSolveConfirmMode(false);
    }
  }, [focusData?.active_problem?.db_id]);

  const handleCommand = (e: React.FormEvent) => {
    e.preventDefault();
    if (!commandText.trim()) return;
    sendTextMessage(commandText, null);
    setCommandText("");
  };

  const handleSpeakHint = async () => {
    if (!focusData?.active_problem?.hint) return;
    
    setShowHint(true);
    if (isSpeakingHint) return;

    try {
      setIsSpeakingHint(true);
      const response = await fetch(API_ENDPOINTS.VOICE_SPEAK, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: `Sir, here is a hint for ${focusData.active_problem.title}. ${focusData.active_problem.hint}` }),
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        audio.onended = () => {
            setIsSpeakingHint(false);
            URL.revokeObjectURL(url);
        };
        audio.play();
      } else {
        setIsSpeakingHint(false);
      }
    } catch (e) {
      console.error("[Neural Link] Voice hint failed.", e);
      setIsSpeakingHint(false);
    }
  };

  const handleGenerateSchedule = async () => {
    setIsGeneratingSchedule(true);
    setScheduleStatus("Analyzing profile...");
    try {
      const res = await fetch(`${HUB_URL}/api/schedule/generate`, { method: "POST" });
      if (res.ok) {
        setScheduleStatus("Schedule ready.");
        setTimeout(() => setScheduleStatus(""), 3000);
      } else {
        setScheduleStatus("Failed.");
        setTimeout(() => setScheduleStatus(""), 3000);
      }
    } catch (e) {
      setScheduleStatus("Error.");
      setTimeout(() => setScheduleStatus(""), 3000);
    } finally {
      setIsGeneratingSchedule(false);
    }
  };

  const handleMarkSolved = async () => {
    const dbId = focusData?.active_problem?.db_id;
    if (!dbId) return;
    try {
      const res = await fetch(`${HUB_URL}/api/schedule/complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ db_id: dbId }),
      });
      if (res.ok) {
        setIsMarkedSolved(true);
        setSolveConfirmMode(false);
        // JARVIS celebrates
        sendTextMessage("I just solved today's LeetCode problem!", null);
      }
    } catch (e) {
      console.error("[Neural Link] Mark solved failed.", e);
    }
  };

  return (
    <div className="space-y-16 animate-in fade-in slide-in-from-bottom-4 duration-1000 ease-out">
      
      {/* 1. Hero Display Section: Voice & Topic Focus */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
        <div className="lg:col-span-7 space-y-8">
          <div className="flex items-center justify-between">
            <p className="text-[10px] uppercase tracking-[0.2em] text-brand-accent font-bold">
              {isRecruiterView ? 'Interview Simulator' : 'Neural Link Session'}
            </p>
            <button 
                onClick={() => setIsRecruiterView(!isRecruiterView)}
                className="text-[10px] uppercase tracking-widest font-bold opacity-30 hover:opacity-100 transition-opacity"
            >
                {isRecruiterView ? 'Switch to War-Room' : 'Recruiter View'}
            </button>
          </div>
          
          <h1 className="text-5xl md:text-7xl font-semibold tracking-tight leading-none text-primary">
            {focusData?.topic || 'Dynamic'}<br/> 
            <span className="text-zinc-400">{focusData?.sub_topic || 'Programming.'}</span>
          </h1>
          
          <p className="text-on-surface-variant max-w-md text-lg leading-relaxed font-normal">
            Analyzing overlapping subproblems and optimal substructure for the current neural vector.
          </p>

          <div className="space-y-6">
            {/* Voice Visualization Plate */}
            <div 
                onClick={isRecording ? stopRecording : startRecording}
                className="bg-surface-container-lowest p-8 rounded-2xl flex items-center gap-6 h-28 overflow-hidden border border-black/5 cursor-pointer hover:border-brand-accent/30 transition-all group shadow-sm"
            >
                <div className="flex items-end h-full gap-1.5 pt-4">
                {[12, 16, 8, 24, 14, 32, 10, 20, 6, 14, 18].map((h, i) => (
                    <motion.div 
                    key={i}
                    animate={{ 
                        height: isRecording || isSpeakingHint ? [h, h*0.3, h*1.4, h] : h,
                        opacity: isRecording || isSpeakingHint ? [1, 0.4, 1] : 1
                    }}
                    transition={{ repeat: Infinity, duration: 0.6 + (i * 0.1), ease: "easeInOut" }}
                    className={`w-1 bg-black rounded-full transition-all duration-300 ${isRecording || isSpeakingHint ? 'bg-brand-accent' : ''}`}
                    style={{ height: `${h}px` }}
                    />
                ))}
                </div>
                <div className="flex-1 border-l border-zinc-100 pl-6">
                    <p className="text-[10px] uppercase tracking-widest text-zinc-400 font-bold mb-1">
                        {isRecording ? 'Capturing Vectors...' : isThinking ? 'Processing...' : isSpeakingHint ? 'JARVIS Speaking...' : 'Neural Link Active'}
                    </p>
                    <p className="text-black font-semibold tracking-tight line-clamp-1 italic">
                        {isSpeakingHint ? `"${focusData?.active_problem?.hint}"` : messages.length > 0 ? messages[messages.length-1].content : '"Ready for placement audit..."'}
                    </p>
                </div>
            </div>

            {/* Neural Optics Control */}
            <div className="flex gap-3">
                <button 
                    onClick={() => isVisionEnabled ? stopVision() : startVision('screen')}
                    className={`px-6 py-4 rounded-2xl text-[10px] uppercase font-black tracking-widest flex items-center gap-3 transition-all ${isVisionEnabled && visionType === 'screen' ? 'bg-brand-accent text-white shadow-lg shadow-brand-accent/30' : 'bg-surface-container-low text-zinc-400 hover:text-black hover:bg-surface-container'}`}
                >
                    <span className="material-symbols-outlined text-sm">{isVisionEnabled && visionType === 'screen' ? 'leak_add' : 'monitor'}</span>
                    <span>{isVisionEnabled && visionType === 'screen' ? 'Optics: Active' : 'Neural Optics: Screen Sync'}</span>
                </button>
                
                {!isVisionEnabled && (
                    <button 
                        onClick={() => startVision('camera')}
                        className="px-6 py-4 rounded-2xl text-[10px] uppercase font-black tracking-widest flex items-center gap-3 bg-surface-container-low text-zinc-400 hover:text-black hover:bg-surface-container transition-all"
                    >
                        <span className="material-symbols-outlined text-sm">videocam</span>
                        <span>Webcam</span>
                    </button>
                )}
            </div>
          </div>
        </div>

        {/* 2. Visual Synthesis: Video / Theme / Ripple Area */}
        <div className="lg:col-span-5 h-[420px] rounded-[32px] overflow-hidden relative shadow-2xl bg-black border border-white/5">
          {/* Neural Ripple Effect (Premium Perception layer) */}
          <AnimatePresence>
            {(isSpeaking || isSpeakingHint) && (
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
                <motion.div 
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ scale: [0.8, 1.4, 1.6], opacity: [0.4, 0.2, 0] }}
                  exit={{ opacity: 0 }}
                  transition={{ repeat: Infinity, duration: 2, ease: "easeOut" }}
                  className="absolute w-48 h-48 border-2 border-brand-accent/40 rounded-full"
                />
                <motion.div 
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ scale: [0.8, 1.2, 1.4], opacity: [0.5, 0.25, 0] }}
                  exit={{ opacity: 0 }}
                  transition={{ repeat: Infinity, duration: 2, ease: "easeOut", delay: 0.5 }}
                  className="absolute w-48 h-48 border border-white/30 rounded-full"
                />
              </div>
            )}
          </AnimatePresence>
          <AnimatePresence mode="wait">
            {!isVisionEnabled ? (
              <motion.img 
                key={focusData?.theme_img}
                initial={{ opacity: 0, scale: 1.1 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={{ duration: 0.8 }}
                className="w-full h-full object-cover grayscale-[0.2]" 
                src={focusData?.theme_img || "https://lh3.googleusercontent.com/aida-public/AB6AXuCIz2LIrHdzdsgIMauuLDWuR48sKMEdqV5h6E1GZWXIdPUj8Lu5XDZb0CHwC53zuuegsq90iNbQs0n0qWXVJGcLAI7ZIc_VWRpWC5Hv_OeYyqw7M0oIwez5K9sgqpSZyd12OBFl0xZ1mzeRi-l2wT1QNhJ8PYWkkR7SPU2iFdyUBC52_0a9mvlSXKCzInepRFtL0UXoNdTh-XqiC4_bWIguOULeUOx9-kV5QTKh3cdcpUlDo13E5Mt3UnO-aZJxP6SAIogwEZ3vsvQ"} 
                alt={focusData?.topic} 
              />
            ) : (
                <motion.div 
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="w-full h-full relative"
                >
                    <video 
                        ref={(el) => {
                          if (el && videoRef.current && el.srcObject !== videoRef.current.srcObject) {
                            el.srcObject = videoRef.current.srcObject;
                          }
                        }}
                        autoPlay 
                        playsInline 
                        muted 
                        className="w-full h-full object-contain bg-zinc-900"
                    />
                    <div className="absolute top-6 left-6 px-4 py-2 bg-black/50 backdrop-blur-md rounded-full border border-white/10 flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                        <span className="text-[9px] font-bold text-white uppercase tracking-widest">Neural Stream: {visionType === 'screen' ? 'Display' : 'Webcam'}</span>
                    </div>
                </motion.div>
            )}
          </AnimatePresence>
          <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent"></div>
          <div className="absolute bottom-10 left-10 text-white">
            <p className="text-[10px] uppercase tracking-[0.2em] font-bold opacity-60 mb-2">Neural Vector Analysis</p>
            <h4 className="text-2xl font-bold tracking-tight mb-2 uppercase">{focusData?.topic || "Recursive Engine"}</h4>
            {focusData?.complexity_analysis ? (
                <div className="flex items-center gap-4">
                    <div className="bg-white/10 backdrop-blur-md px-3 py-1.5 rounded-lg border border-white/10">
                        <p className="text-[8px] uppercase font-bold text-zinc-400 mb-0.5">Time</p>
                        <p className="font-mono text-sm font-bold text-brand-accent">{focusData.complexity_analysis.time}</p>
                    </div>
                    <div className="bg-white/10 backdrop-blur-md px-3 py-1.5 rounded-lg border border-white/10">
                        <p className="text-[8px] uppercase font-bold text-zinc-400 mb-0.5">Space</p>
                        <p className="font-mono text-sm font-bold text-emerald-400">{focusData.complexity_analysis.space}</p>
                    </div>
                </div>
            ) : (
                <div className="flex items-center gap-2 mt-1">
                    <span className="text-zinc-400 font-mono text-sm">O(2^N)</span>
                    <span className="material-symbols-outlined text-xs">arrow_forward</span>
                    <span className="text-brand-accent font-mono text-sm font-bold">O(N log N)</span>
                </div>
            )}
          </div>
        </div>
      </section>

      {/* 2. Bento Grid for Logic & Tools */}
      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        
        {/* LeetCode Assistant (Main Problem Plate) */}
        <div className="bg-surface-container-lowest p-8 rounded-3xl lg:col-span-2 space-y-10 flex flex-col justify-between border border-black/5 shadow-sm">
          <div className="flex justify-between items-start">
            <div className="space-y-1">
              <div className="flex items-center gap-2 mb-2">
                <span className="w-2 h-2 rounded-full bg-brand-accent animate-pulse"></span>
                <p className="text-[10px] uppercase tracking-[0.15em] font-bold text-zinc-400">
                    LeetCode Streak: {focusData?.streak || 0} Days
                </p>
              </div>
              <h3 className="text-4xl font-bold text-primary tracking-tighter">
                 {focusData?.active_problem?.difficulty || 'Medium'} Algorithm
              </h3>
              <p className="text-on-surface-variant font-medium opacity-60">
                {focusData?.active_problem?.title
                  ? `${focusData.active_problem.title}`
                  : 'Loading today\'s problem...'}
              </p>
            </div>
            <div className="flex flex-col items-end gap-2">
              <span className="px-5 py-2 bg-zinc-100 rounded-full text-[10px] uppercase font-bold tracking-widest">
                  {focusData?.active_problem?.tags?.[0] || 'Algorithm'}
              </span>
              <button
                onClick={handleGenerateSchedule}
                disabled={isGeneratingSchedule}
                title="JARVIS analyzes your profile and schedules 7 days of problems"
                className="flex items-center gap-1.5 px-4 py-2 bg-zinc-900 text-white rounded-full text-[9px] uppercase font-black tracking-widest hover:bg-brand-accent transition-all disabled:opacity-40"
              >
                <span className={`material-symbols-outlined text-xs ${isGeneratingSchedule ? 'animate-spin' : ''}`}>psychology</span>
                <span>{scheduleStatus || 'Generate Schedule'}</span>
              </button>
            </div>
          </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Hint Panel */}
              <div 
                onClick={handleSpeakHint}
                className={`p-6 rounded-2xl border transition-all cursor-pointer group ${showHint ? 'bg-brand-accent/5 border-brand-accent/30' : 'bg-zinc-50 border-black/5 hover:border-brand-accent/20'}`}
              >
                <p className="text-[10px] uppercase tracking-widest text-zinc-400 font-bold mb-3">Live Neural Hint</p>
                <div className="flex items-center gap-3">
                  <span className={`material-symbols-outlined ${showHint ? 'text-brand-accent animate-pulse' : 'text-zinc-300 group-hover:text-brand-accent'}`}>lightbulb</span>
                  <span className={`font-bold tracking-tight transition-all duration-500 ${showHint ? 'text-black opacity-100' : 'text-zinc-300 opacity-20'}`}>
                    {showHint ? focusData?.active_problem?.hint : 'Click to Reveal Hint'}
                  </span>
                </div>
              </div>

              {/* Action Panel — cycles: Continue → Confirm → Solved */}
              {isMarkedSolved ? (
                <div className="bg-green-50 border border-green-200 rounded-2xl flex flex-col items-center justify-center gap-2 text-center p-6">
                  <span className="material-symbols-outlined text-green-500 text-3xl">check_circle</span>
                  <p className="text-[10px] uppercase font-black tracking-widest text-green-600">Solved Today</p>
                  <p className="text-[9px] text-zinc-400 font-bold">Next problem loads tomorrow</p>
                </div>
              ) : solveConfirmMode ? (
                <div className="rounded-2xl border border-zinc-200 flex flex-col items-center justify-center gap-3 p-6 bg-white">
                  <p className="text-[10px] uppercase font-black tracking-widest text-zinc-600">Mark as Solved?</p>
                  <div className="flex gap-2 w-full">
                    <button
                      onClick={handleMarkSolved}
                      className="flex-1 py-3 bg-black text-white rounded-xl text-[9px] uppercase font-black tracking-widest hover:bg-green-600 transition-all"
                    >
                      ✓ Yes, Solved
                    </button>
                    <button
                      onClick={() => setSolveConfirmMode(false)}
                      className="flex-1 py-3 bg-zinc-100 rounded-xl text-[9px] uppercase font-black tracking-widest hover:bg-zinc-200 transition-all"
                    >
                      Not Yet
                    </button>
                  </div>
                </div>
              ) : (
                <div className="grid grid-rows-2 gap-2 h-full">
                  <button 
                    onClick={() => {
                      const link = focusData?.active_problem?.link;
                      if (link && link !== "#") {
                        window.open(link, "_blank");
                        // After opening LeetCode, prompt to mark solved
                        setTimeout(() => setSolveConfirmMode(true), 3000);
                      }
                    }}
                    className="bg-black text-white rounded-2xl flex items-center justify-center gap-4 font-bold text-[10px] uppercase tracking-[0.2em] hover:bg-brand-accent transition-all shadow-xl shadow-black/10"
                  >
                    <span>Continue Solution</span>
                    <span className="material-symbols-outlined text-sm">arrow_forward</span>
                  </button>
                  <button
                    onClick={() => setSolveConfirmMode(true)}
                    className="border border-black/10 rounded-2xl text-[9px] uppercase font-black tracking-widest hover:bg-zinc-50 transition-all"
                  >
                    Mark as Solved
                  </button>
                </div>
              )}
            </div>
        </div>

        {/* Live Neural Transcript */}
        <div className="bg-surface-container p-8 rounded-3xl flex flex-col gap-6 h-[450px]">
          <div className="flex justify-between items-center shrink-0">
            <p className="text-[10px] uppercase tracking-[0.15em] font-bold">Neural Transcript</p>
            <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'} shadow-lg`} />
          </div>
          
          <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-6 pr-2 scroll-smooth">
            {messages.length === 0 && (
                <p className="text-zinc-400 text-xs text-center font-bold mt-20 opacity-30 uppercase tracking-[0.3em]">Neural Standing By...</p>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'} animate-in slide-in-from-bottom-2 duration-300`}>
                <div className={`max-w-[95%] p-4 rounded-2xl ${
                  m.role === 'user' 
                    ? 'bg-black text-white rounded-br-sm' 
                    : 'bg-white text-black border border-black/5 rounded-bl-sm shadow-sm'
                }`}>
                  <p className="text-[13px] font-bold leading-relaxed">{m.content}</p>
                </div>
              </div>
            ))}
          </div>

          <form onSubmit={handleCommand} className="relative mt-2">
            <input 
              type="text"
              value={commandText}
              onChange={(e) => setCommandText(e.target.value)}
              placeholder="Inject command..."
              className="w-full bg-white border border-black/5 rounded-xl py-4 flex pl-5 pr-12 text-xs font-bold tracking-tight"
            />
            <button type="submit" className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-lg bg-zinc-100">
                <span className="material-symbols-outlined text-sm">arrow_upward</span>
            </button>
          </form>
        </div>

        {/* Strategic Exam Radar */}
        <div className="bg-[#f0f0f2] p-8 rounded-3xl space-y-8 border border-black/5 flex flex-col justify-between">
          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined">timer</span>
              <h3 className="text-xl font-bold tracking-tight uppercase tracking-widest">Focus Session</h3>
            </div>
            <FocusTimer externalEvent={timerEvent} />
          </div>
          <button onClick={() => setActivePage?.('calendar')} className="w-full py-4 text-[10px] uppercase font-black tracking-[0.2em] border border-black/10 rounded-2xl hover:bg-black hover:text-white transition-all mt-4">
            Open Roadmap
          </button>
        </div>

        {/* Focus Efficiency Metrics */}
        <div className="bg-white p-10 rounded-3xl border border-zinc-100 flex flex-col justify-between shadow-xs">
          <div>
            <p className="text-[10px] uppercase tracking-widest text-zinc-400 font-black mb-6">Deep Work Accumulation</p>
            <div className="text-7xl font-black tracking-tighter">
                {focusData?.deep_work_hours || '4.2'}<span className="text-2xl text-zinc-200 ml-1">H</span>
            </div>
          </div>
          <div className="mt-12 space-y-4">
            <div className="h-2 w-full bg-zinc-100 rounded-full overflow-hidden">
                <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: `${focusData?.goal_met || 84}%` }}
                    transition={{ duration: 1.5 }}
                    className="h-full bg-brand-accent shadow-[0_0_12px_rgba(74,143,255,0.4)]" 
                />
            </div>
            <p className="text-[10px] uppercase tracking-widest font-black text-zinc-500">
                {focusData?.goal_met || 84}% of daily Placement goal reached
            </p>
          </div>
        </div>

        {/* Subject Insights Card */}
        <div className="relative rounded-3xl overflow-hidden group cursor-pointer shadow-lg border border-black/5">
          <img className="w-full h-full object-cover transition-transform duration-1000 group-hover:scale-110" src="https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&q=80&w=1000" alt="Research" />
          <div className="absolute inset-0 bg-black/40 p-10 flex flex-col justify-end">
            <p className="text-[10px] uppercase tracking-widest text-white/70 font-bold">Research Project</p>
            <h4 className="text-white text-3xl font-black tracking-tight">Edge Computing</h4>
          </div>
        </div>

      </section>
    </div>
  );
}
