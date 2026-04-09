import { motion } from "motion/react";
import { useState, useEffect } from "react";

export function SettingsPage() {
  const [settings, setSettings] = useState({
    wakeWord: true,
    vision: true,
    autoSpeak: true,
    sarcasm: 75,
    neuralNode: 'New York (Primary)',
    apiKey: 'sk-********************'
  });

  useEffect(() => {
    const saved = localStorage.getItem('jarvis_settings');
    if (saved) setSettings(JSON.parse(saved));
  }, []);

  useEffect(() => {
    localStorage.setItem('jarvis_settings', JSON.stringify(settings));
  }, [settings]);

  const toggle = (key: keyof typeof settings) => {
    setSettings(prev => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="space-y-16 animate-in fade-in slide-in-from-bottom-4 duration-1000 ease-out">
      <header className="space-y-6">
        <p className="text-[10px] font-bold uppercase tracking-[0.3em] text-accent">Neural Configuration</p>
        <h1 className="text-6xl md:text-8xl font-semibold tracking-tighter text-black leading-none">System.</h1>
        <p className="text-on-surface-variant text-lg max-w-md leading-relaxed font-medium">
          Fine-tune the autonomous intelligence shell, security protocols, and spatial vision parameters.
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-12 mt-16">
        
        {/* Operational Protocols */}
        <section className="md:col-span-12 lg:col-span-7 space-y-10">
          <div className="flex items-center gap-6">
            <h2 className="text-[10px] font-bold uppercase tracking-[0.5em] text-zinc-400 whitespace-nowrap">Operational Protocols</h2>
            <div className="h-px w-full bg-black/5" />
          </div>
          
          <div className="grid grid-cols-1 gap-4">
            {[
              { id: 'wakeWord', label: 'Wake Word Detection', desc: 'Active listening for "Hey Jarvis" trigger.', icon: 'hearing' },
              { id: 'vision', label: 'Spatial Vision System', desc: 'Real-time object categorization via CAM_NORTH_01.', icon: 'visibility' },
              { id: 'autoSpeak', label: 'Autonomous Voice Link', desc: 'Direct neural-to-speech synchronization.', icon: 'record_voice_over' }
            ].map((s) => (
              <div key={s.id} className="bg-surface-container-lowest p-10 rounded-[2.5rem] border border-outline-variant/10 flex items-center justify-between group shadow-sm transition-all hover:border-accent/20">
                <div className="flex items-center gap-8">
                  <div className="w-14 h-14 rounded-2xl bg-surface-container-low flex items-center justify-center text-black group-hover:bg-accent/10 group-hover:text-accent transition-all">
                    <span className="material-symbols-outlined text-2xl">{s.icon}</span>
                  </div>
                  <div className="space-y-1">
                    <p className="text-lg font-bold text-black tracking-tight">{s.label}</p>
                    <p className="text-[11px] text-zinc-400 font-bold uppercase tracking-widest leading-tight">{s.desc}</p>
                  </div>
                </div>
                <button 
                  onClick={() => toggle(s.id as any)}
                  className={`w-16 h-9 rounded-full transition-all duration-700 relative flex items-center px-1.5 border border-black/5 ${
                    settings[s.id as keyof typeof settings] ? 'bg-black' : 'bg-surface-container-high'
                  }`}
                >
                  <motion.div 
                    layout
                    className={`w-6 h-6 rounded-full shadow-lg ${
                      settings[s.id as keyof typeof settings] ? 'bg-accent' : 'bg-zinc-400'
                    }`}
                  />
                </button>
              </div>
            ))}
          </div>
        </section>

        {/* Personality Parameters */}
        <section className="md:col-span-12 lg:col-span-5 space-y-10">
          <div className="flex items-center gap-6">
            <h2 className="text-[10px] font-bold uppercase tracking-[0.5em] text-zinc-400 whitespace-nowrap">Neural Personality</h2>
            <div className="h-px w-full bg-black/5" />
          </div>
          
          <div className="bg-white p-12 rounded-[3rem] border border-zinc-100 space-y-12 shadow-2xl shadow-black/[0.02]">
             <div className="space-y-6">
               <div className="flex justify-between items-end">
                 <div>
                    <p className="text-[10px] font-bold tracking-[0.2em] uppercase text-zinc-400 mb-2">Personality Vector</p>
                    <h4 className="text-2xl font-bold tracking-tight">Sarcasm Coefficient</h4>
                 </div>
                 <span className="text-2xl font-bold tracking-tighter text-black">{settings.sarcasm}<span className="text-sm opacity-20 ml-1">%</span></span>
               </div>
               <div className="relative pt-4">
                 <input 
                   type="range" 
                   value={settings.sarcasm}
                   onChange={(e) => setSettings(prev => ({ ...prev, sarcasm: parseInt(e.target.value) }))}
                   className="w-full h-1 bg-zinc-100 rounded-full appearance-none accent-black cursor-pointer"
                 />
                 <div className="flex justify-between text-[8px] font-bold uppercase tracking-[0.3em] text-zinc-400 mt-6 px-1">
                   <span>Subservient</span>
                   <span>Neutral</span>
                   <span>Provocative</span>
                 </div>
               </div>
             </div>

             <div className="space-y-6 pt-6 border-t border-black/5">
                <p className="text-[10px] font-bold tracking-[0.3em] uppercase text-zinc-400">Local Node Relay</p>
                <div className="flex bg-surface-container-low p-6 rounded-2xl border border-black/5 items-center justify-between cursor-pointer group hover:bg-black hover:text-white transition-all duration-300">
                  <p className="text-sm font-bold tracking-tight">{settings.neuralNode}</p>
                  <span className="material-symbols-outlined text-sm group-hover:rotate-180 transition-transform">expand_more</span>
                </div>
             </div>
          </div>
        </section>

        {/* Security Matrix */}
        <section className="md:col-span-12 space-y-8 mt-8">
          <h2 className="text-[10px] font-bold uppercase tracking-[0.5em] text-zinc-400 mb-8 px-2">Security Architecture</h2>
          <div className="bg-black rounded-[3rem] p-12 flex flex-col md:flex-row items-center gap-12 shadow-2xl relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-tr from-accent/10 via-transparent to-transparent opacity-50" />
            
            <div className="w-20 h-20 bg-zinc-800 rounded-3xl flex items-center justify-center text-white relative z-10">
               <span className="material-symbols-outlined text-4xl">vpn_key</span>
            </div>
            
            <div className="flex-1 space-y-2 relative z-10">
               <p className="text-xl font-bold text-white tracking-tight">Core Signal Encryption</p>
               <p className="text-[11px] text-zinc-500 font-mono tracking-widest break-all select-all">{settings.apiKey}</p>
            </div>
            
            <button className="px-12 py-5 bg-white text-black rounded-full text-[10px] font-bold uppercase tracking-[0.3em] hover:scale-105 active:scale-95 transition-all shadow-xl relative z-10">
               Rotate Key Map
            </button>
          </div>
        </section>

      </div>
    </div>
  );
}
