import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { HUB_URL, API_ENDPOINTS } from '../../utils/apiConfig';

interface Challenge {
  title: string;
  difficulty: string;
  description: string;
  broken_code: string;
  hint: string;
  language: string;
  test_cases: any[];
  heatmap?: any[];
}

export function SkillEvolutionPage() {
  const [lang, setLang] = useState('python');
  const [challenge, setChallenge] = useState<Challenge | null>(null);
  const [userCode, setUserCode] = useState('');
  const [feedback, setFeedback] = useState<{valid?: boolean, msg?: string} | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [xp, setXp] = useState(840);
  const [isBenchmarksOpen, setIsBenchmarksOpen] = useState(false);
  const [heatmapData, setHeatmapData] = useState<Record<string, number>>({});
  const [isCompleted, setIsCompleted] = useState(false);
  const hasSpokenRef = useRef(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const fetchHeatmap = async () => {
    try {
      const res = await fetch(`${HUB_URL}/api/evolution/heatmap`);
      const data = await res.json();
      setHeatmapData(data);
    } catch (e) {
      console.error("Heatmap fetch drift", e);
    }
  };
  
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Tab') {
      e.preventDefault();
      const start = e.currentTarget.selectionStart;
      const end = e.currentTarget.selectionStart;
      
      const newVal = userCode.substring(0, start) + "    " + userCode.substring(end);
      setUserCode(newVal);
      
      setTimeout(() => {
        if (textareaRef.current) {
          textareaRef.current.selectionStart = textareaRef.current.selectionEnd = start + 4;
        }
      }, 0);
    }
  };
  
  useEffect(() => {
    fetchChallenge();
    fetchHeatmap();
    hasSpokenRef.current = false;
  }, [lang]);

  const fetchChallenge = async () => {
    setChallenge(null);
    setUserCode('');
    setFeedback(null);
    try {
      const res = await fetch(`${HUB_URL}/api/evolution/today?lang=${lang}`);
      const data = await res.json();
      setChallenge(data);
      setUserCode(data.broken_code);
      setHeatmapData(data.heatmap || {});
      
      const today = new Date().toLocaleDateString('en-CA'); // YYYY-MM-DD local
      if (data.heatmap && data.heatmap[today] > 0) {
        setIsCompleted(true);
      }
      
      if (!hasSpokenRef.current) {
        speakText(`Sir, today's evolution challenge is ${data.title}. Focus on the algorithmic efficiency.`);
        hasSpokenRef.current = true;
      }
    } catch (e) {
      console.error("Evolution fetch failed", e);
    }
  };

  const speakText = async (text: string) => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }

    try {
      const res = await fetch(API_ENDPOINTS.VOICE_SPEAK, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audioRef.current = audio;
      
      audio.onended = () => {
        URL.revokeObjectURL(url);
        audioRef.current = null;
      };

      audio.play().catch(e => console.debug("Audio play blocked:", e));
    } catch (e) {
      console.error("Voice synthesis failed", e);
    }
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setFeedback(null);
    try {
      const res = await fetch(`${HUB_URL}/api/evolution/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: userCode, language: lang, id: challenge?.title })
      });
      const data = await res.json();
      setFeedback({ valid: data.valid, msg: data.feedback });
      
      // Auto-vanish after 5 seconds
      setTimeout(() => setFeedback(null), 5000);

      if (data.valid) {
        setXp(prev => prev + 12);
        setIsCompleted(true);
        setTimeout(() => fetchHeatmap(), 1000);
        speakText("Evolution successful, Sir. Your logic is optimized.");
      } else {
        speakText("Logic drift detected, Sir.");
      }
    } catch (e) {
      setFeedback({ valid: false, msg: "Connection drift." });
      setTimeout(() => setFeedback(null), 5000);
    }
    setIsSubmitting(false);
  };

  const handleHint = async () => {
    if (!challenge) return;
    speakText(`Sir, consider this: ${challenge.hint}`);
  };

  const handleRun = async () => {
    setIsSubmitting(true);
    setFeedback(null);
    try {
      const res = await fetch(`${HUB_URL}/api/evolution/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          code: userCode, 
          language: lang, 
          id: challenge?.title,
          is_dry_run: true 
        })
      });
      const data = await res.json();
      
      if (challenge) {
        const updatedCases = challenge.test_cases?.map((t: any) => ({
          ...t,
          status: data.valid ? 'passed' : 'failed'
        }));
        setChallenge({ ...challenge, test_cases: updatedCases } as any);
      }
      
      setFeedback({ 
        valid: data.valid, 
        msg: data.valid ? "Simulation successful." : "Simulation failed." 
      });
      setTimeout(() => setFeedback(null), 5000);
      speakText(data.valid ? "Simulation successful, Sir." : "Logic drift in simulation.");
    } catch (e) {
      setFeedback({ valid: false, msg: "Simulation drift." });
      setTimeout(() => setFeedback(null), 5000);
    }
    setIsSubmitting(false);
  };

  const generateHeatmapDays = () => {
    const days = [];
    for (let i = 29; i >= 0; i--) {
      const d = new Date();
      d.setDate(d.getDate() - i);
      const dateStr = d.toLocaleDateString('en-CA');
      const intensity = heatmapData[dateStr] || 0;
      days.push({ date: dateStr, intensity });
    }
    return days;
  };

  const heatmapDays = generateHeatmapDays();

  return (
    <div className="max-w-[1550px] mx-auto px-6 sm:px-10 space-y-12 animate-in fade-in duration-700 relative">
      <section className="flex flex-col lg:flex-row lg:items-end justify-between gap-10">
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-4">
            <h2 className="text-5xl font-black tracking-tighter text-black">Skill Evolution</h2>
            <div className="px-4 py-1.5 bg-emerald-50 text-[10px] font-black text-emerald-600 uppercase tracking-widest rounded-xl border border-emerald-200">
              Neural Processing Active
            </div>
          </div>
          <p className="text-zinc-400 font-bold text-sm tracking-tight max-w-lg uppercase opacity-80 leading-relaxed">
            Maximizing recursive logic output via high-fidelity neural interface.
          </p>
        </div>

        <div className="bg-white/40 p-8 rounded-[40px] border border-black/5 flex flex-col gap-4 shadow-sm hover:shadow-xl transition-all duration-700 max-w-full lg:max-w-md xl:max-w-xl">
          <div className="flex justify-between items-center px-1">
            <label className="text-[10px] font-black uppercase tracking-[0.3em] text-zinc-400">Evolution Pulse (30D)</label>
            <span className="text-[9px] font-black text-emerald-500 uppercase tracking-widest animate-pulse">Live Persistence</span>
          </div>
          <div className="flex gap-2 pb-2 overflow-x-auto no-scrollbar scroll-smooth">
            {heatmapDays.map((d, i) => (
              <div 
                key={i} 
                className={`w-4 h-4 shrink-0 rounded-[4px] transition-all duration-500 hover:scale-[1.3] cursor-pointer ${
                  d.intensity === 0 ? 'bg-zinc-100 shadow-inner' :
                  d.intensity === 1 ? 'bg-[#c6f6d5]' :
                  d.intensity === 2 ? 'bg-[#48bb78]' : 
                  'bg-[#22c55e] animate-pulse'
                }`}
                title={`${d.date}: ${d.intensity} Evolutions`}
              />
            ))}
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-start">
        <div className="lg:col-span-3 space-y-8">
          <div className="bg-white p-10 rounded-[44px] border border-black/5 shadow-sm hover:shadow-2xl transition-all duration-500">
            <span className={`px-5 py-2 rounded-2xl text-[9px] font-black uppercase tracking-widest border ${
              challenge?.difficulty === 'Easy' ? 'bg-emerald-50 text-emerald-600 border-emerald-100' :
              challenge?.difficulty === 'Medium' ? 'bg-amber-50 text-amber-600 border-amber-100' :
              'bg-rose-50 text-rose-600 border-rose-100'
            }`}>
              {challenge?.difficulty || 'Analyzing'}
            </span>
            <h3 className="text-2xl font-black text-black tracking-tighter mb-6 mt-6">{challenge?.title || 'Synthesis...'}</h3>
            <p className="text-[14px] text-zinc-500 font-bold leading-relaxed mb-10 italic">
              "{challenge?.description || 'JARVIS is synthesizing your challenge data...'}"
            </p>
          </div>

          <button onClick={handleHint} className="w-full p-8 bg-zinc-900 rounded-[40px] text-left group hover:scale-[1.03] transition-all shadow-2xl">
            <div className="flex items-center gap-4 mb-3">
              <span className="material-symbols-outlined text-white text-sm">psychology</span>
              <span className="text-[10px] font-black text-zinc-400 uppercase tracking-[0.3em]">Neural Coach</span>
            </div>
            <p className="text-white text-lg font-black tracking-tighter uppercase italic">Access Hint Analysis</p>
          </button>
        </div>

        <div className="lg:col-span-9 space-y-8">
          <div className="bg-[#141517] rounded-[56px] overflow-hidden shadow-2xl border border-white/5 relative">
            <div className="flex items-center justify-between px-12 py-6 bg-white/[0.02] border-b border-white/5">
              <div className="flex gap-2 p-1.5 rounded-22xl">
                {['python', 'java'].map(l => (
                  <button key={l} onClick={() => setLang(l)} className={`text-[10px] uppercase font-black px-6 py-2 rounded-xl ${lang === l ? 'bg-white text-black' : 'text-zinc-500'}`}>{l}</button>
                ))}
              </div>
              <button onClick={() => setIsBenchmarksOpen(true)} className="px-6 py-2.5 bg-white/5 text-white rounded-2xl text-[10px] uppercase font-black tracking-widest">Benchmarks</button>
            </div>
            <div className="p-16 h-[500px] relative">
              <textarea 
                ref={textareaRef}
                value={userCode}
                onChange={(e) => setUserCode(e.target.value)}
                onKeyDown={handleKeyDown}
                spellCheck={false}
                className="w-full h-full bg-transparent text-[#dcdfe4] font-mono text-lg resize-none focus:outline-none leading-relaxed selection:bg-emerald-500/30"
              />
              <AnimatePresence>
                {feedback && (
                  <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 20 }} className={`absolute bottom-12 left-12 right-12 p-8 rounded-[32px] border ${feedback.valid ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' : 'bg-rose-500/10 border-rose-500/30 text-rose-400'}`}>
                    <p className="text-lg font-bold italic">"{feedback.msg}"</p>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>

          <div className="flex gap-8">
            <button onClick={handleRun} disabled={isSubmitting || isCompleted} className="px-12 py-8 bg-white border rounded-[40px] text-[10px] font-black uppercase tracking-widest disabled:opacity-40">{isCompleted ? 'Verified' : 'Simulation'}</button>
            <button onClick={handleSubmit} disabled={isSubmitting || isCompleted} className={`flex-1 py-8 rounded-[40px] text-[10px] font-black uppercase tracking-widest ${isCompleted ? 'bg-emerald-500 text-white' : 'bg-black text-white'}`}>
              {isCompleted ? 'Linked' : isSubmitting ? 'Processing...' : 'Commit Evolution'}
            </button>
          </div>
        </div>
      </div>
      
      <AnimatePresence>
        {isBenchmarksOpen && (
          <>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setIsBenchmarksOpen(false)} className="fixed inset-0 bg-black/60 z-[100]" />
            <motion.div initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }} className="fixed right-0 top-0 bottom-0 w-full max-w-[500px] bg-white z-[101] p-12 overflow-y-auto">
              <h3 className="text-3xl font-black mb-8">Benchmarks</h3>
              <div className="space-y-6">
                {(challenge as any)?.test_cases?.map((t: any, i: number) => (
                  <div key={i} className="p-6 bg-zinc-50 rounded-3xl border">
                    <p className="text-[10px] font-black uppercase text-zinc-400 mb-2">Test Case {i+1}</p>
                    <p className="font-mono text-sm">Input: {t.input}</p>
                    <p className="font-mono text-sm text-emerald-600">Target: {t.expected}</p>
                    <p className="mt-2 text-xs font-bold uppercase">{t.status || 'Pending'}</p>
                  </div>
                ))}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      <section className="bg-white p-12 rounded-[56px] border flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div className="w-16 h-16 rounded-3xl bg-black flex items-center justify-center"><span className="material-symbols-outlined text-white text-3xl">neurology</span></div>
            <h4 className="text-2xl font-black uppercase">Logical Proficiency</h4>
          </div>
          <div className="flex gap-12">
            <div className="text-right"><p className="text-[10px] font-black text-zinc-400 uppercase">Status</p><p className="text-2xl font-black">MASTER CLASS</p></div>
            <div className="text-right"><p className="text-[10px] font-black text-zinc-400 uppercase">Synergy</p><p className="text-3xl font-black text-emerald-500">84%</p></div>
          </div>
      </section>
    </div>
  );
}
