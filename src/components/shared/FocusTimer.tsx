import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'motion/react';

interface FocusTimerProps {
  initialMinutes?: number;
  onComplete?: () => void;
  // External control signals from WebSocket
  externalEvent?: { event: string; duration?: number } | null;
}

export function FocusTimer({ initialMinutes = 25, onComplete, externalEvent }: FocusTimerProps) {
  const [secondsLeft, setSecondsLeft] = useState(initialMinutes * 60);
  const [isActive, setIsActive] = useState(false);
  const [totalDuration, setTotalDuration] = useState(initialMinutes * 60);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (externalEvent) {
      if (externalEvent.event === 'start') {
        const mins = externalEvent.duration || initialMinutes;
        setSecondsLeft(mins * 60);
        setTotalDuration(mins * 60);
        setIsActive(true);
      } else if (externalEvent.event === 'stop') {
        setIsActive(false);
      } else if (externalEvent.event === 'reset') {
        setSecondsLeft(initialMinutes * 60);
        setTotalDuration(initialMinutes * 60);
        setIsActive(false);
      }
    }
  }, [externalEvent, initialMinutes]);

  useEffect(() => {
    if (isActive && secondsLeft > 0) {
      timerRef.current = setInterval(() => {
        setSecondsLeft((prev) => prev - 1);
      }, 1000);
    } else if (secondsLeft === 0) {
      setIsActive(false);
      if (onComplete) onComplete();
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isActive, secondsLeft, onComplete]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const progress = totalDuration > 0 ? (secondsLeft / totalDuration) * 502 : 502;

  const handleToggle = () => setIsActive(!isActive);
  const handleReset = () => {
    setIsActive(false);
    setSecondsLeft(initialMinutes * 60);
    setTotalDuration(initialMinutes * 60);
  };

  return (
    <div className="flex flex-col items-center justify-center text-center">
      <div className="relative mb-8 z-10">
        <svg className="w-44 h-44 transform -rotate-90">
          <circle className="text-zinc-800" cx="88" cy="88" fill="black" r="80" stroke="currentColor" strokeWidth="2" />
          <motion.circle 
            initial={{ strokeDashoffset: 502 }}
            animate={{ strokeDashoffset: isNaN(progress) ? 502 : progress }}
            transition={{ duration: 1, ease: "linear" }}
            className="text-brand-accent capitalize" cx="88" cy="88" fill="transparent" r="80" stroke="currentColor" strokeDasharray="502" strokeWidth="2" strokeLinecap="round" 
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-5xl font-light tracking-tighter text-white">{formatTime(secondsLeft)}</span>
        </div>
      </div>
      <div className="flex gap-4 relative z-10">
        <button 
          onClick={handleToggle}
          className={`w-14 h-14 rounded-full flex items-center justify-center hover:scale-105 transition-transform active:scale-95 shadow-xl shadow-brand-accent/20 ${isActive ? 'bg-zinc-800 text-white' : 'bg-brand-accent text-white'}`}
        >
          <span className="material-symbols-outlined text-2xl !text-white" style={{ fontVariationSettings: "'FILL' 1" }}>
            {isActive ? 'pause' : 'play_arrow'}
          </span>
        </button>
        <button 
          onClick={handleReset}
          className="w-14 h-14 rounded-full bg-zinc-800 flex items-center justify-center hover:scale-105 transition-transform active:scale-95 text-white"
        >
          <span className="material-symbols-outlined text-2xl">refresh</span>
        </button>
      </div>
    </div>
  );
}
