import { useState, useEffect, useRef } from 'react';

/**
 * JARVIS Neural Listener Hook
 * Decoupled from core IO to prevent 'God Object' bloat.
 * Handles the 'Always-On' SpeechRecognition loop for the JARVIS trigger.
 */
export function useWakeWord(onTrigger: (command: string) => void) {
    const [isWakeWordEnabled, setIsWakeWordEnabled] = useState(true);
    const recognitionRef = useRef<any>(null);
    const isWakeWordActiveRef = useRef(true);
    const onTriggerRef = useRef(onTrigger);

    useEffect(() => {
        onTriggerRef.current = onTrigger;
    }, [onTrigger]);

    useEffect(() => {
        isWakeWordActiveRef.current = isWakeWordEnabled;
    }, [isWakeWordEnabled]);

    useEffect(() => {
        const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        if (!SpeechRecognition) {
            console.warn("[Jarvis Core] SpeechRecognition API not supported in this browser.");
            return;
        }

        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;

        recognition.onresult = (event: any) => {
            if (!isWakeWordActiveRef.current) return;

            let interimTranscript = "";
            let finalTranscript = "";

            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript;
                } else {
                    interimTranscript += event.results[i][0].transcript;
                }
            }

            const lowerText = (finalTranscript + " " + interimTranscript).toLowerCase();
            const isWakeWordTrigger = /\b(jarvis|travis|garvis)\b/i.test(lowerText);

            if (isWakeWordTrigger) {
                if (finalTranscript) {
                    const command = (finalTranscript).replace(/\b(jarvis|travis|garvis)\b/gi, "JARVIS").trim();
                    onTriggerRef.current(command);
                    recognition.stop(); // Temporarily stop to let the main IO take over
                }
            }
        };

        recognition.onend = () => {
            if (isWakeWordActiveRef.current) {
                try { recognition.start(); } catch (e) {}
            }
        };

        recognition.onerror = (e: any) => {
            if (e.error === 'aborted') return;
            console.debug("[Jarvis Core] Neural Listener Error:", e.error);
        };

        recognitionRef.current = recognition;
        
        // Initial start delay to prevent race conditions with audio output
        const startTimer = setTimeout(() => {
            if (isWakeWordActiveRef.current) {
                try { recognition.start(); } catch (e) {}
            }
        }, 1000);

        return () => {
            clearTimeout(startTimer);
            isWakeWordActiveRef.current = false;
            try { recognition.stop(); } catch (e) {}
        };
    }, []);

    // Manual control for pausing wake word (e.g. during active recording)
    const pauseWakeWord = () => {
        isWakeWordActiveRef.current = false;
        try { recognitionRef.current?.stop(); } catch (e) {}
    };

    const resumeWakeWord = () => {
        isWakeWordActiveRef.current = isWakeWordEnabled;
        if (isWakeWordEnabled) {
            try { recognitionRef.current?.start(); } catch (e) {}
        }
    };

    return {
        isWakeWordEnabled,
        setIsWakeWordEnabled,
        pauseWakeWord,
        resumeWakeWord
    };
}
