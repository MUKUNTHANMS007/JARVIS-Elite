import { useEffect, useState, useRef, useCallback } from "react";
import { useAudioSocket } from "../hooks/useAudioSocket";
import { useVision } from "../hooks/useVision"; // Now using your updated version
import { useWakeWord } from "../hooks/useWakeWord";
// Removed useSystemSocket import, now passed as prop

// Page Components
import { DashboardPage } from "./pages/DashboardPage";
import { StatusPage } from "./pages/StatusPage";
import { HistoryPage } from "./pages/HistoryPage";
import { SettingsPage } from "./pages/SettingsPage";
import { CorePage } from "./pages/CorePage";
import { CalendarPage } from "./pages/CalendarPage";
import { SkillEvolutionPage } from "./pages/SkillEvolutionPage";

// Types
interface SystemStatus {
  cpu: number;
  ram: number;
  status: string;
  energy: number;
  disk: number;
  temp: number;
  uptime: string;
  services?: { name: string; status: string }[];
  timerEvent?: { event: string; duration?: number } | null;
}

interface TimerEvent {
  event: string;
  duration?: number;
}

import { NEURAL_WS, HUB_WS, API_ENDPOINTS } from "../utils/apiConfig";

interface JarvisInterfaceProps {
  activePage: string;
  setActivePage: (p: string) => void;
  systemData: any;
  isPulseConnected: boolean;
}

export function JarvisInterface({ 
  activePage, 
  setActivePage,
  systemData: data,
  isPulseConnected
}: JarvisInterfaceProps) {
  // --- 1. Core Audio & Communication ---
  const { 
    messages, 
    isConnected, 
    isRecording, 
    isThinking, 
    setIsThinking,
    isSpeaking,
    startRecording, 
    stopRecording,
    sendTextMessage,
    mood,
    reconnect: reconnectAudio
  } = useAudioSocket(API_ENDPOINTS.VOICE_WS);

  // useSystemSocket moved to App.tsx for shared 3D background sync

  // --- 2. Specialized Optical Feedback (Updated) ---
  const { 
    isVisionEnabled, 
    visionType,
    videoRef, 
    canvasRef, 
    startVision,
    stopVision,
    captureFrame 
  } = useVision();

  // --- 3. Data States ---
  const [stats, setStats] = useState<any>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [energyLevel, setEnergyLevel] = useState(88);
  const [focusData, setFocusData] = useState<any>(null);
  const [timerEvent, setTimerEvent] = useState<TimerEvent | null>(null);
  const [isFocusConnected, setIsFocusConnected] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const lastProactiveTimestamp = useRef<number>(0);

  // --- 4. Unified Recording Logic ---
  const handleStartRecording = useCallback(async () => {
    pauseWakeWord();
    const frame = isVisionEnabled ? captureFrame() : null;
    await startRecording(frame);
  }, [isVisionEnabled, captureFrame, startRecording]);

  const handleStopRecording = useCallback(() => {
    stopRecording();
    resumeWakeWord();
  }, [stopRecording]);

  // --- 5. Specialized Neural Listener ---
  const { 
    isWakeWordEnabled, 
    setIsWakeWordEnabled,
    pauseWakeWord,
    resumeWakeWord
  } = useWakeWord((command) => {
    const frame = isVisionEnabled ? captureFrame() : null;
    sendTextMessage(command, frame);
  });

  // --- 6. NEURAL PULSE SYNC (Unified Dashboard + Status + Focus) ---
  const fetchSync = useCallback(async () => {
    try {
      const resp = await fetch(API_ENDPOINTS.SYNC);
      const syncData = await resp.json();
      if (syncData.intelligence) {
        const intel = syncData.intelligence;
        // Normalize backend key names to the UI schema.
        const normalized = {
          ...intel,
          intelligence_briefing: intel.intelligence_briefing ?? intel.gmail_briefing
        };
        setStats(normalized);
      }
      if (syncData.system) setSystemStatus(syncData.system);
      if (syncData.focus) setFocusData(syncData.focus);
    } catch (e) {
      console.warn("[Neural Hub] Initial sync pulse failed. Falling back to WebSocket stream.");
    }
  }, []);

  useEffect(() => {
    fetchSync();
  }, [fetchSync]);

  useEffect(() => {
    if (data) {
      if (data.focus) setFocusData(data.focus);
      // Production Grade Packet Mapping
      if (data.dashboard) {
        setStats((prev: any) => {
          const next = { ...(prev || {}) };
          const d = data.dashboard;

          if (typeof d.unread_mail === 'number') next.unread_mail = d.unread_mail;
          if (typeof d.spotify_track === 'string') next.spotify_track = d.spotify_track;
          
          // Map to keys expected by DashboardPage
          if (d.leetcode != null) next.leetcode = d.leetcode;
          if (d.github != null) next.github = d.github;
          if (d.briefing != null) next.intelligence_briefing = d.briefing;
          
          return next;
        });

        // --- PROACTIVE SENTINEL HANDSHAKE ---
        if (data.dashboard.proactive_trigger) {
          const trigger = data.dashboard.proactive_trigger;
          if (trigger.timestamp > lastProactiveTimestamp.current) {
            lastProactiveTimestamp.current = trigger.timestamp;
            // Automate a "Morning Protocol" or "System Alert" handshake
            console.log("[Sentinel] Proactive Briefing Triggered:", trigger.title);
            sendTextMessage(`Summarize the alert: ${trigger.title} starting in ${trigger.diff} minutes.`);
          }
        }
      }

      if (data.status) {
        const s = data.status;
        setSystemStatus((prev: any) => ({
          ...prev,
          cpu: s.cpu,
          ram: s.ram,
          disk: s.disk,
          uptime: s.uptime,
          energy: s.energy
        }));
        
        if (typeof s.energy === 'number') {
          setEnergyLevel(Math.round(s.energy));
        }
      }
    }
  }, [data, sendTextMessage]);

  // --- 7. Legacy Focus Support Removed (Merged into /ws/system above) ---

  // Sync scroll on transcript updates
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, activePage]);

  const today = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });

  return (
    <div className="min-h-screen bg-surface text-on-surface font-sans selection:bg-primary/10">
      
      {/* Shadow Protocol Assets */}
      {data?.dashboard?.is_batman_mode && <div className="scanner-line h-screen fixed top-0 left-0" />}

      {/* Batman Mode Banner */}
      <div className="batman-mode-banner">
        🦇 &nbsp; SHADOW PROTOCOL: ACTIVE — ACCESS LEVEL SIGMA-9 &nbsp; 🦇
      </div>

      {/* Top Navigation Shell */}
      <nav className="fixed top-0 w-full z-50 glass-nav flex items-center justify-between px-6 py-4">
        <div className="flex items-center gap-4">
          <div className={`w-2 h-2 rounded-full ${isConnected && isPulseConnected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
          <span className="brand-title text-xs font-bold tracking-[0.2em] uppercase">
            {data?.dashboard?.is_batman_mode ? "ALFRED MODE: SHADOW PROTOCOL" : "JARVIS NEURAL CORE"}
          </span>
          <div className="h-4 w-px bg-black/5 mx-2" />
          <div className="flex items-center gap-2">
             <span className={`text-[8px] font-black uppercase tracking-[0.3em] px-2 py-0.5 rounded ${mood === 'stressed' ? 'bg-amber-100 text-amber-700 font-bold' : 'bg-emerald-50/50 text-emerald-600'}`}>
                {mood === 'stressed' ? 'Urgent' : 'Neutral'}
             </span>
          </div>
        </div>
        
        <div className="hidden md:flex items-center gap-8">
          {[
            { id: 'dashboard', label: 'Dashboard' },
            { id: 'core', label: 'Neural Link' },
            { id: 'calendar', label: 'Calendar' },
            { id: 'evolution', label: 'Evolution' },
            { id: 'work', label: 'System' },
            { id: 'history', label: 'History' },
            { id: 'settings', label: 'Settings' }
          ].map((p) => (
            <span 
              key={p.id}
              onClick={() => setActivePage(p.id)}
              className={`cursor-pointer text-xs uppercase tracking-widest transition-all duration-200 ${
                activePage === p.id 
                  ? 'text-zinc-900 font-semibold underline underline-offset-8 decoration-primary' 
                  : 'text-zinc-400 hover:opacity-70 font-medium'
              }`}
            >
              {p.label}
            </span>
          ))}
        </div>

        <div className="w-8 h-8 rounded-full bg-zinc-900 flex items-center justify-center cursor-pointer overflow-hidden border border-white/10" onClick={() => setActivePage('settings')}>
          <span className="text-white text-[10px] font-bold tracking-tighter">
            {data?.dashboard?.is_batman_mode ? "ALFRED" : "JARVIS"}
          </span>
        </div>
      </nav>

      <main className="pt-24 pb-32 px-6 max-w-7xl mx-auto">
        {(!isConnected) && (
          <div className="mb-6 p-3 bg-red-50 border border-red-100 rounded-xl flex items-center justify-center gap-2">
            <span className="material-symbols-outlined text-red-500 text-sm">cloud_off</span>
            <p className="text-xs font-bold text-red-600 uppercase tracking-tighter">Neural Link Offline - Attempting Reconnection</p>
          </div>
        )}

        {activePage === 'dashboard' && (
          <DashboardPage 
            today={today}
            energyLevel={energyLevel}
            systemStatus={systemStatus as any}
            stats={stats}
            isVisionEnabled={isVisionEnabled}
            visionType={visionType}
            startVision={startVision}
            stopVision={stopVision}
            videoRef={videoRef}
            canvasRef={canvasRef}
            isConnected={isConnected}
            isRecording={isRecording}
            isThinking={isThinking}
            setIsThinking={setIsThinking}
            startRecording={handleStartRecording}
            stopRecording={handleStopRecording}
            reconnect={reconnectAudio}
            messages={messages}
            scrollRef={scrollRef}
            sendTextMessage={sendTextMessage}
          />
        )}

        {activePage === 'work' && <StatusPage systemStatus={systemStatus} timerEvent={timerEvent} />}

        {activePage === 'core' && (
          <CorePage 
            today={today}
            isConnected={isConnected}
            isRecording={isRecording}
            isThinking={isThinking}
            isSpeaking={isSpeaking}
            messages={messages}
            stats={stats}
            focusData={focusData}
            timerEvent={timerEvent}
            startRecording={handleStartRecording}
            stopRecording={handleStopRecording}
            reconnect={reconnectAudio}
            scrollRef={scrollRef}
            sendTextMessage={sendTextMessage}
            setActivePage={setActivePage}
            isVisionEnabled={isVisionEnabled}
            visionType={visionType}
            startVision={startVision}
            stopVision={stopVision}
            videoRef={videoRef}
            canvasRef={canvasRef}
          />
        )}

        { activePage === 'history' && <HistoryPage />}
        { activePage === 'calendar' && <CalendarPage />}
        { activePage === 'evolution' && <SkillEvolutionPage />}

        {activePage === 'settings' && (
          <div className="p-8 bg-white/50 backdrop-blur-xl rounded-3xl border border-black/5">
            <h2 className="text-xl font-bold mb-6">Neural Link Settings</h2>
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-bold">Wake Word Listener</p>
                  <p className="text-xs text-zinc-500 italic">Always listening for "JARVIS"</p>
                </div>
                <input 
                  type="checkbox" 
                  checked={isWakeWordEnabled} 
                  onChange={(e) => setIsWakeWordEnabled(e.target.checked)}
                  className="w-5 h-5 accent-zinc-900"
                />
              </div>

              <div className="flex items-center justify-between border-t pt-6">
                <div>
                  <p className="font-bold">Vision Neural Link</p>
                  <p className="text-xs text-zinc-500 italic">Enable camera access for visual synthesis</p>
                </div>
                <button 
                  onClick={() => isVisionEnabled ? stopVision() : startVision('camera')}
                  className={`px-4 py-2 rounded-full text-xs font-bold transition-all ${
                    isVisionEnabled ? 'bg-red-500 text-white' : 'bg-zinc-900 text-white'
                  }`}
                >
                  {isVisionEnabled ? 'DISABLE VISION' : 'ENABLE CAMERA'}
                </button>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Mobile Nav */}
      <nav className="md:hidden fixed bottom-16 left-1/2 -translate-x-1/2 w-[90%] h-16 flex justify-around items-center px-4 bg-white/80 backdrop-blur-2xl z-50 rounded-full shadow-[0_8px_32px_rgba(0,0,0,0.1)] border border-black/5 pb-safe">
        {[
          { id: 'dashboard', icon: 'dashboard' },
          { id: 'core', icon: 'graphic_eq' },
          { id: 'calendar', icon: 'calendar_today' },
          { id: 'evolution', icon: 'psychology' },
          { id: 'work', icon: 'monitoring' },
          { id: 'history', icon: 'history' },
          { id: 'settings', icon: 'settings' }
        ].map((p) => (
          <div 
            key={p.id}
            onClick={() => setActivePage(p.id)}
            className={`flex flex-col items-center justify-center transition-transform ${
              activePage === p.id ? 'text-zinc-900 font-bold scale-110' : 'text-zinc-400'
            }`}
          >
            <span className="material-symbols-outlined" style={{ fontVariationSettings: activePage === p.id ? "'FILL' 1" : "'FILL' 0" }}>{p.icon}</span>
          </div>
        ))}
      </nav>
      
      {/* --- NEURAL OPTICS PERSISTENCE LAYER --- */}
      {/* Globally persistent, hidden video element ensures vision works across all pages. */}
      <div className="fixed -bottom-[1000px] -left-[1000px] w-1 h-1 overflow-hidden pointer-events-none opacity-0">
        <video 
          ref={videoRef} 
          autoPlay 
          playsInline 
          muted 
          className="w-full h-full"
        />
      </div>
    </div>
  );
}
