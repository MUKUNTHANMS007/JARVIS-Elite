import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { DateTimePicker } from "@/components/calendar-with-time-piker";
import { HUB_URL } from "../../utils/apiConfig";

interface CalendarEvent {
  id: string;
  title: string;
  description?: string;
  event_date: string;
  event_time?: string;
  category: string;
}

export function CalendarPage() {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(new Date());
  const [startTime, setStartTime] = useState("10:30:00");
  const [endTime, setEndTime] = useState("11:30:00");
  const [newEvent, setNewEvent] = useState({
    title: "",
    category: "Task"
  });

  const fetchEvents = async () => {
    try {
      const res = await fetch(`${HUB_URL}/api/calendar`);
      const data = await res.json();
      setEvents(data);
    } catch (err) {
      console.error("Failed to sync calendar:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents();
  }, []);

  const handleAddEvent = async (e: React.FormEvent) => {
    e.preventDefault();
    const formattedDate = selectedDate ? selectedDate.toLocaleDateString('en-CA') : new Date().toLocaleDateString('en-CA');
    try {
      await fetch(`${HUB_URL}/api/calendar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: newEvent.title,
          event_date: formattedDate,
          event_time: startTime && endTime ? `${startTime} - ${endTime}` : (startTime || null),
          category: newEvent.category
        })
      });
      setIsModalOpen(false);
      setNewEvent({ title: "", category: "Task" });
      setSelectedDate(new Date());
      setStartTime("10:30:00");
      setEndTime("11:30:00");
      fetchEvents();
    } catch (err) {
      console.error("Failed to add event:", err);
    }
  };

  const deleteEvent = async (id: string) => {
    if (!confirm("Remove this entry from Neural Core?")) return;
    try {
      await fetch(`${HUB_URL}/api/calendar/${id}`, { method: "DELETE" });
      fetchEvents();
    } catch (err) {
      console.error("Failed to delete event:", err);
    }
  };

  const groupedEvents = events.reduce((groups: any, event) => {
    const date = event.event_date;
    if (!groups[date]) groups[date] = [];
    groups[date].push(event);
    return groups;
  }, {});

  const categoryStyles: any = {
    'Exam': { bg: 'bg-rose-500/10', text: 'text-rose-500', border: 'border-rose-500/20', dot: 'bg-rose-500' },
    'Meeting': { bg: 'bg-sky-500/10', text: 'text-sky-500', border: 'border-sky-500/20', dot: 'bg-sky-500' },
    'Task': { bg: 'bg-zinc-500/10', text: 'text-zinc-600', border: 'border-zinc-500/20', dot: 'bg-zinc-900' },
    'Personal': { bg: 'bg-emerald-500/10', text: 'text-emerald-500', border: 'border-emerald-500/20', dot: 'bg-emerald-500' }
  };


  return (
    <div className="relative min-h-[calc(100vh-12rem)] animate-in fade-in duration-1000 overflow-hidden rounded-[48px]">
      
      {/* High-Fidelity Neural Background */}
      <div className="absolute inset-0 pointer-events-none mesh-gradient -z-10" />
      <div className="absolute inset-0 pointer-events-none dot-matrix opacity-30 -z-10" />

      <div className="space-y-16 relative z-10">
        {/* Futuristic Header Section */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 px-4">
          <div>
            <motion.div 
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center gap-3 mb-4 bg-white/40 backdrop-blur-md px-4 py-1.5 rounded-full border border-white/40 shadow-sm w-fit"
            >
              <div className="w-2 h-2 rounded-full bg-accent animate-pulse shadow-[0_0_12px_rgba(74,143,255,1)]" />
              <label className="text-[9px] uppercase tracking-[0.3em] font-black text-zinc-600">Neural Sync Active</label>
            </motion.div>
            <h2 className="text-7xl font-extralight tracking-tighter text-zinc-900 leading-none">
              Neural <span className="font-black text-primary drop-shadow-sm">Calendar</span>
            </h2>
          </div>
          <button 
            onClick={() => setIsModalOpen(true)}
            className="group relative px-10 py-5 bg-zinc-900 text-white rounded-[24px] text-[10px] font-black uppercase tracking-[0.2em] transition-premium hover:scale-105 active:scale-95 shadow-[0_20px_40px_rgba(0,0,0,0.2)] overflow-hidden"
          >
            <div className="absolute inset-0 bg-accent/30 opacity-0 group-hover:opacity-100 transition-opacity blur-2xl" />
            <span className="relative z-10 flex items-center gap-3">
              <span className="material-symbols-outlined text-lg">add_circle</span>
              Add Operational Entry
            </span>
          </button>
        </div>


      {isLoading ? (
        <div className="h-96 flex flex-col items-center justify-center gap-6">
          <div className="relative">
            <div className="w-16 h-16 border-4 border-black/5 border-t-accent rounded-full animate-spin" />
            <div className="absolute inset-0 w-16 h-16 border-4 border-accent/20 rounded-full blur-sm" />
          </div>
          <p className="text-[10px] uppercase tracking-[0.4em] font-black text-zinc-500 animate-pulse">Syncing Neural Core Architecture...</p>
        </div>
      ) : events.length === 0 ? (
        <motion.div 
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="mx-4 glass-panel rounded-[48px] p-32 text-center border-dashed border-2 border-black/10 group overflow-hidden"
        >
          <div className="absolute inset-0 mesh-gradient opacity-10 group-hover:opacity-20 transition-opacity" />
          <div className="relative z-10">
            <div className="w-24 h-24 bg-white/80 backdrop-blur-md rounded-full flex items-center justify-center mx-auto mb-8 shadow-2xl border border-white/50">
              <span className="material-symbols-outlined text-5xl text-zinc-400 group-hover:text-accent transition-colors">biotech</span>
            </div>
            <h3 className="text-3xl font-black text-zinc-900 mb-3 tracking-tighter italic">Neural Void Detected</h3>
            <p className="text-zinc-500 font-bold tracking-tight max-w-sm mx-auto italic opacity-70">"Operational schedule is empty. Requesting task injection from Neural Core..."</p>
          </div>
        </motion.div>
      ) : (
        <div className="space-y-32 px-4 relative">
          {/* Enhanced Vertical Neural Line */}
          <div className="absolute left-[47px] top-4 bottom-4 w-[2px] bg-gradient-to-b from-transparent via-black/10 to-transparent z-0 opacity-50" />

          {Object.keys(groupedEvents).sort().map((date, dateIdx) => (
            <motion.div 
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ type: "spring", stiffness: 100, damping: 20, delay: dateIdx * 0.1 }}
              key={date} 
              className="relative pl-32"
            >
              {/* Enhanced Neural Node */}
              <div className="absolute left-[38px] top-2 w-5 h-5 rounded-full border-2 border-white bg-white shadow-[0_4px_12px_rgba(0,0,0,0.1)] flex items-center justify-center z-10 transition-premium hover:scale-150 cursor-pointer group">
                <div className="w-2 h-2 bg-black rounded-full animate-pulse shadow-[0_0_8px_rgba(0,0,0,0.5)]" />
                <div className="absolute inset-0 bg-accent rounded-full opacity-0 group-hover:opacity-20 transition-opacity blur-md" />
              </div>

              <div className="mb-12">
                <h3 className="text-xs font-black tracking-[0.3em] text-accent uppercase mb-2">
                  {new Date(date).toLocaleDateString('en-US', { weekday: 'long' })}
                </h3>
                <h4 className="text-5xl font-black tracking-tighter text-zinc-900 drop-shadow-sm">
                  {new Date(date).toLocaleDateString('en-US', { month: 'long', day: 'numeric' })}
                </h4>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">

                {groupedEvents[date].map((event: CalendarEvent, eventIdx: number) => {
                  const style = categoryStyles[event.category] || categoryStyles['Task'];
                  return (
                    <motion.div 
                      layoutId={event.id}
                      initial={{ opacity: 0, scale: 0.95 }}
                      whileInView={{ opacity: 1, scale: 1 }}
                      viewport={{ once: true }}
                      transition={{ delay: (dateIdx * 0.1) + (eventIdx * 0.05) }}
                      key={event.id}
                      className="group glass-panel hover:bg-white/90 p-8 rounded-[32px] border border-black/5 transition-premium hover:shadow-2xl hover:shadow-black/10 relative overflow-hidden active:scale-[0.98]"
                    >
                      {/* Interactive Accent */}
                      <div className={`absolute left-0 top-0 bottom-0 w-1 transition-all group-hover:w-2 ${style.dot} opacity-40`} />
                      
                      <div className="flex justify-between items-start mb-6">
                        <div className={`flex items-center gap-2 px-4 py-1.5 rounded-full border ${style.border} ${style.bg}`}>
                          <div className={`w-1.5 h-1.5 rounded-full ${style.dot} animate-pulse`} />
                          <span className={`text-[10px] font-black uppercase tracking-widest ${style.text}`}>
                            {event.category}
                          </span>
                        </div>
                        
                        <div className="flex items-center gap-2">
                          <button 
                            onClick={() => deleteEvent(event.id)}
                            className="opacity-0 group-hover:opacity-100 p-2 rounded-full hover:bg-rose-50 text-zinc-400 hover:text-rose-500 transition-all font-bold"
                          >
                            <span className="material-symbols-outlined text-sm">delete_sweep</span>
                          </button>
                        </div>
                      </div>

                      <div className="space-y-4">
                        <div>
                          <h4 className="text-2xl font-black tracking-tighter text-zinc-900 mb-2 group-hover:text-primary transition-colors">{event.title}</h4>
                          {event.event_time && (
                            <div className="flex items-center gap-2 text-zinc-400">
                              <span className="material-symbols-outlined text-[14px]">schedule</span>
                              <p className="text-[10px] font-bold tracking-widest uppercase">{event.event_time}</p>
                            </div>
                          )}
                        </div>
                        
                        {event.description && (
                          <p className="text-zinc-500 text-sm leading-relaxed font-medium line-clamp-2 group-hover:line-clamp-none transition-all">
                            {event.description}
                          </p>
                        )}
                      </div>

                      {/* Subtle hover pattern */}
                      <div className="absolute -right-4 -bottom-4 w-24 h-24 bg-black/[0.02] rounded-full blur-3xl group-hover:bg-accent/10 transition-premium" />
                    </motion.div>
                  );
                })}
              </div>
            </motion.div>
          ))}
        </div>
      )}
      {/* Manual Entry Modal - Redesigned */}
      <AnimatePresence>
        {isModalOpen && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 md:p-6">
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsModalOpen(false)}
              className="absolute inset-0 bg-black/60 backdrop-blur-xl"
            />
            <motion.div 
              initial={{ scale: 0.9, opacity: 0, y: 40 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.9, opacity: 0, y: 40 }}
              className="glass-panel w-full max-w-xl rounded-[48px] p-8 md:p-12 relative shadow-[0_32px_64px_rgba(0,0,0,0.4)] border border-white/20"
            >
              <div className="flex justify-between items-start mb-10">
                <div>
                  <label className="text-[10px] font-black uppercase tracking-[0.3em] text-accent mb-2 block">System Command</label>
                  <h3 className="text-4xl font-black tracking-tighter text-zinc-900">Schedule <span className="text-primary">Event</span></h3>
                  {selectedDate && (
                    <div className="mt-2 flex items-center gap-2 text-[10px] font-bold text-zinc-400 uppercase tracking-widest bg-black/5 px-3 py-1 rounded-lg w-fit">
                      <span className="material-symbols-outlined text-[12px]">calendar_today</span>
                      Establishing entry for {selectedDate.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
                    </div>
                  )}
                </div>
                <button 
                  onClick={() => setIsModalOpen(false)}
                  className="p-2 hover:bg-black/5 rounded-full transition-colors"
                >
                  <span className="material-symbols-outlined text-zinc-400">close</span>
                </button>
              </div>

              <form onSubmit={handleAddEvent} className="space-y-8">
                <div className="space-y-3">
                  <label className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-400 ml-4">Event Designation</label>
                  <input 
                    required
                    type="text"
                    value={newEvent.title}
                    onChange={e => setNewEvent({...newEvent, title: e.target.value})}
                    placeholder="Project Phoenix Briefing"
                    className="w-full bg-black/[0.03] border-2 border-transparent rounded-[24px] px-8 py-5 text-zinc-900 font-bold placeholder:text-zinc-300 focus:border-accent focus:bg-white transition-all outline-none text-lg shadow-inner"
                  />
                </div>

                <div className="bg-black/[0.02] rounded-[32px] p-6 border border-black/5">
                  <DateTimePicker 
                    date={selectedDate}
                    setDate={setSelectedDate}
                    startTime={startTime}
                    setStartTime={setStartTime}
                    endTime={endTime}
                    setEndTime={setEndTime}
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-3">
                    <label className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-400 ml-4">Priority Class</label>
                    <div className="relative">
                      <select 
                        value={newEvent.category}
                        onChange={e => setNewEvent({...newEvent, category: e.target.value})}
                        className="w-full bg-black/[0.03] border-2 border-transparent rounded-[20px] px-8 py-4 text-zinc-900 font-bold appearance-none hover:bg-black/10 transition-all cursor-pointer outline-none"
                      >
                        <option>Task</option>
                        <option>Exam</option>
                        <option>Meeting</option>
                        <option>Personal</option>
                      </select>
                      <span className="material-symbols-outlined absolute right-6 top-1/2 -translate-y-1/2 pointer-events-none text-zinc-400">expand_more</span>
                    </div>
                  </div>
                  
                  <div className="flex items-end">
                    <button 
                      type="submit"
                      className="w-full bg-zinc-900 text-white py-4 rounded-[20px] text-[11px] font-black uppercase tracking-[0.2em] hover:bg-accent hover:scale-[1.02] active:scale-[0.98] transition-all shadow-xl shadow-black/20"
                    >
                      Initialize Event
                    </button>
                  </div>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  </div>
);
}


