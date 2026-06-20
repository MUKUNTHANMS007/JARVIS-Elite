import React, { useState, useEffect, useRef } from "react";
import { AnimatePresence, motion } from "motion/react";
import { JarvisInterface } from "./components/JarvisInterface";
import { NeuralCore } from "./components/ui/NeuralCore";
import { useSystemSocket } from "./hooks/useSystemSocket";
import { HUB_WS } from "./utils/apiConfig";

export default function App() {
  const [view, setView] = useState<'landing' | 'interface'>('landing');
  const [activePage, setActivePage] = useState<string>('dashboard');

  const { data: packet, isConnected: isPulseConnected } = useSystemSocket(`${HUB_WS}/ws/system`);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [interfaceKey, setInterfaceKey] = useState(0);
  const lastMode = useRef<boolean | null>(null);

  useEffect(() => {
    const isBatman = packet?.dashboard?.is_batman_mode ?? false;
    
    // Trigger "Neural Reset" (Soft Refresh) if mode changes
    if (lastMode.current !== null && lastMode.current !== isBatman) {
        setIsTransitioning(true);
        setInterfaceKey(prev => prev + 1);
        
        // Reset overlay fades after 1sec
        setTimeout(() => {
            setIsTransitioning(false);
        }, 1000);
    }
    lastMode.current = isBatman;

    if (isBatman) {
        document.documentElement.classList.add("batman-theme");
        document.title = "BATCOMPUTER — NEURAL CORE";
        try {
          const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
          if (AudioContextClass) {
            const ctx = new AudioContextClass();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = "sine";
            osc.frequency.setValueAtTime(150, ctx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(600, ctx.currentTime + 0.4);
            gain.gain.setValueAtTime(0.15, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.4);
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start();
            osc.stop(ctx.currentTime + 0.45);
          } else {
            new Audio("/sounds/batman-activate.mp3").play().catch(() => {});
          }
        } catch (e) {
          new Audio("/sounds/batman-activate.mp3").play().catch(() => {});
        }
    } else {
        document.documentElement.classList.remove("batman-theme");
        document.title = "JARVIS — NEURAL CORE";
    }
  }, [packet?.dashboard?.is_batman_mode]);

  return (
    <div className="min-h-screen bg-black text-white font-sans selection:bg-primary/20 flex flex-col overflow-x-hidden relative">
      
      {/* Neural Reset Overlay (Soft Refresh) */}
      <AnimatePresence>
        {isTransitioning && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="reboot-overlay"
          >
            <div className="reboot-text">Neural Pulse Resynchronizing...</div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Dynamic Background Architecture (Local Three.js System) */}
      <NeuralCore nodeCount={250} className="opacity-60" packet={packet} />

      {/* Persistent Background Grid (Subtle Overlay) */}
      <div className="fixed inset-0 pointer-events-none opacity-[0.05] bg-[radial-gradient(#fff_1px,transparent_1px)] [background-size:32px_32px] z-[1]" />

      <AnimatePresence mode="wait">
        {view === 'landing' ? (
          <motion.main 
            key="landing"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, scale: 1.02, filter: "blur(20px)" }}
            transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
            className="flex-1 flex flex-col items-center justify-center pt-24 px-6 relative z-10"
          >
            <motion.div 
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
              className="text-center space-y-12"
            >
              <div className="inline-flex items-center gap-3 px-4 py-2 rounded-full bg-white/5 backdrop-blur-xl border border-white/10">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.8)]" />
                <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-zinc-400">Neural Link Active</span>
              </div>
              
              <h1 className="text-[12rem] font-bold tracking-[-0.05em] text-white uppercase leading-[0.8] drop-shadow-[0_0_25px_rgba(255,255,255,0.15)]">
                JARVIS
              </h1>
              
              <div className="max-w-md mx-auto space-y-4">
                <p className="text-zinc-400 text-lg font-medium leading-relaxed tracking-tight">
                  Autonomous Intelligence Shell V.2.0
                </p>
                <div className="h-px w-24 bg-white/10 mx-auto" />
              </div>

              <div className="pt-8">
                <button 
                  onClick={() => setView('interface')}
                  className="group relative px-16 py-6 bg-white text-black rounded-full font-bold uppercase text-[10px] tracking-[0.3em] overflow-hidden transition-all duration-500 hover:scale-[1.05] active:scale-[0.98] shadow-[0_0_40px_rgba(255,255,255,0.15)]"
                >
                  <span className="relative z-10">Initialize Session</span>
                  <div className="absolute inset-0 bg-gradient-to-tr from-primary/20 via-transparent to-primary/20 opacity-0 group-hover:opacity-100 transition-opacity" />
                </button>
              </div>
            </motion.div>

            {/* Bottom Info */}
            <div className="absolute bottom-12 flex justify-between w-full max-w-7xl px-12 opacity-20">
              <div className="text-[10px] font-bold uppercase tracking-[0.2em]">
                Network: LOCAL_STATION<br />
                Node: PK-7128
              </div>
              <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-right">
                Authorized Personnel Only<br />
                © 2026 JARVIS AI
              </div>
            </div>
          </motion.main>
        ) : (
          <JarvisInterface 
            key={`interface-${interfaceKey}`} 
            activePage={activePage} 
            setActivePage={setActivePage} 
            systemData={packet} 
            isPulseConnected={isPulseConnected}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
