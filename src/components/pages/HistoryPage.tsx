import { motion } from "motion/react";
import { useEffect, useState } from "react";
import { HUB_URL } from "../../utils/apiConfig";

interface Message {
  id: number;
  role: string;
  content: string;
  timestamp: string;
}

export function HistoryPage() {
  const [history, setHistory] = useState<Message[]>([]);
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetch(`${HUB_URL}/api/history`)
      .then(res => res.json())
      .then(data => setHistory(data))
      .catch(err => console.error("History fetch failed.", err));
  }, []);

  const filteredHistory = history.filter(m => 
    m.content.toLowerCase().includes(search.toLowerCase())
  );

  // Group by relative date
  const groups = [
    { label: 'Today', items: filteredHistory.slice(0, 5) },
    { label: 'Yesterday', items: filteredHistory.slice(5, 10) },
    { label: 'Recent Archive', items: filteredHistory.slice(10, 30) }
  ];

  return (
    <div className="space-y-16 animate-in fade-in slide-in-from-bottom-4 duration-1000 ease-out">
      <header className="flex flex-col md:flex-row justify-between items-end gap-12">
        <div className="space-y-6">
          <p className="text-[10px] font-bold uppercase tracking-[0.3em] text-accent">Neural Archive</p>
          <motion.h1 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="text-6xl md:text-8xl font-semibold tracking-tighter text-black leading-none"
          >
            Interactions.
          </motion.h1>
          <p className="text-on-surface-variant text-lg max-w-md leading-relaxed font-medium">
            A comprehensive record of every neural response and command processed by your local node.
          </p>
        </div>
        
        <div className="w-full md:w-96 relative group">
          <span className="material-symbols-outlined absolute left-6 top-1/2 -translate-y-1/2 text-black opacity-30 group-focus-within:text-accent transition-colors">search</span>
          <input 
            type="text" 
            placeholder="Filter archives..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full h-16 bg-surface-container-low rounded-2xl pl-16 pr-8 border border-outline-variant/10 focus:outline-none focus:ring-1 focus:ring-accent/40 transition-all font-bold text-black text-[12px] uppercase tracking-widest shadow-sm"
          />
        </div>
      </header>

      <div className="space-y-24">
        {groups.map((group, gi) => (
          group.items.length > 0 && (
            <section key={gi} className="space-y-12">
              <div className="flex items-center gap-8">
                <h2 className="text-[10px] font-bold uppercase tracking-[0.5em] text-zinc-400 whitespace-nowrap">{group.label}</h2>
                <div className="h-px w-full bg-black/5" />
              </div>
              
              <div className="grid grid-cols-1 gap-4">
                {group.items.map((m, i) => (
                  <motion.div 
                    key={m.id}
                    initial={{ opacity: 0, y: 10 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.03 }}
                    viewport={{ once: true }}
                    className="bg-surface-container-lowest p-10 rounded-[2.5rem] border border-outline-variant/10 hover:border-accent/30 transition-all duration-300 group cursor-pointer shadow-sm"
                  >
                    <div className="flex items-start gap-10">
                      <div className={`w-16 h-16 rounded-2xl flex items-center justify-center shrink-0 transition-all group-hover:scale-105 ${
                        m.role === 'user' ? 'bg-black text-white shadow-xl shadow-black/10' : 'bg-surface-container-low text-accent'
                      }`}>
                        <span className="material-symbols-outlined text-3xl">
                          {m.role === 'user' ? 'person' : 'smart_toy'}
                        </span>
                      </div>
                      <div className="flex-1 space-y-3">
                        <div className="flex justify-between items-center">
                          <p className={`text-[11px] font-bold uppercase tracking-widest ${m.role === 'user' ? 'text-black opacity-40' : 'text-accent'}`}>
                            {m.role === 'user' ? 'User Sequence' : 'Jarvis Core'}
                          </p>
                          <span className="text-[10px] font-bold text-zinc-400">
                            {new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                        <p className="text-[16px] text-on-surface-variant leading-relaxed font-bold tracking-tight opacity-90 group-hover:opacity-100 transition-opacity">
                          {m.content}
                        </p>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </section>
          )
        ))}
      </div>
    </div>
  );
}
