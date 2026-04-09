"use client"

import { motion } from "motion/react";

interface ActiveTaskProps {
  data: {
    active_problem: {
      id: number;
      title: string;
      difficulty: string;
      tags: string[];
      hint: string;
    };
    streak: number;
  };
}

export const ActiveTask = ({ data }: ActiveTaskProps) => {
  if (!data?.active_problem) return null;

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative p-0.5 rounded-[2rem] bg-gradient-to-br from-emerald-500/20 via-white/5 to-transparent overflow-hidden group hover:from-emerald-500/40 transition-all duration-700 shadow-2xl"
    >
      <div className="bg-[#0a0a0a]/90 backdrop-blur-3xl p-10 rounded-[1.95rem] border border-white/5 relative z-10">
        
        {/* Header Logic */}
        <div className="flex flex-col md:flex-row justify-between items-start gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.8)]" />
              <p className="text-[10px] font-black text-emerald-500 tracking-[0.4em] uppercase">
                Neural Streak: {data.streak} Days
              </p>
            </div>
            <h2 className="text-5xl font-extrabold tracking-[-0.03em] text-white leading-tight">
              {data.active_problem.difficulty} <br/>
              <span className="text-zinc-600 group-hover:text-white transition-colors duration-500">
                {data.active_problem.tags[1]} Problem
              </span>
            </h2>
            <p className="text-zinc-500 font-medium text-lg tracking-tight pt-2">
              Problem #{data.active_problem.id}: {data.active_problem.title}
            </p>
          </div>
          
          <div className="flex flex-wrap gap-2 pt-2">
            {data.active_problem.tags.map((tag, i) => (
              <span 
                key={i}
                className="px-6 py-2 bg-white text-black text-[10px] font-black uppercase rounded-full tracking-widest shadow-lg"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>

        {/* Action & Hint Layer */}
        <div className="mt-16 grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="p-8 bg-white/[0.03] rounded-2xl border border-white/5 hover:border-emerald-500/30 transition-all duration-500 group/hint">
            <div className="flex items-center gap-3 mb-4">
              <span className="material-symbols-outlined text-emerald-500 text-sm">lightbulb</span>
              <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Neural Sync Hint</p>
            </div>
            <p className="text-xl font-medium tracking-tight text-zinc-200 group-hover/hint:text-white leading-relaxed">
              {data.active_problem.hint}
            </p>
          </div>

          <button className="h-full bg-white text-black rounded-2xl font-black text-xs uppercase tracking-[0.3em] flex items-center justify-center gap-4 hover:bg-emerald-400 hover:scale-[1.02] active:scale-[0.98] transition-all duration-500 shadow-[0_0_30px_rgba(255,255,255,0.1)]">
            <span>Continue Neural Session</span>
            <span className="material-symbols-outlined font-black">arrow_forward</span>
          </button>
        </div>
      </div>
      
      {/* Decorative Glow */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/5 blur-[100px] rounded-full group-hover:bg-emerald-500/10 transition-all" />
    </motion.div>
  );
};
