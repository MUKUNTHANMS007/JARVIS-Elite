import { useState, useRef, useCallback } from 'react';
import { captureFrame as captureFrameUtil } from '../utils/visionUtils';

/**
 * JARVIS Neural Vision Hook
 * Updated to support Screen Capture (getDisplayMedia) and Camera (getUserMedia).
 * Manages the media stream lifecycle and frame synchronization.
 */
export function useVision() {
    const [isVisionEnabled, setIsVisionEnabled] = useState(false);
    const [visionType, setVisionType] = useState<'camera' | 'screen' | null>(null);
    const videoRef = useRef<HTMLVideoElement | null>(null);
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const streamRef = useRef<MediaStream | null>(null);

    const startVision = useCallback(async (type: 'camera' | 'screen') => {
        try {
            let stream: MediaStream;
            if (type === 'screen') {
                stream = await navigator.mediaDevices.getDisplayMedia({ 
                    video: { cursor: 'always' } as any, 
                    audio: false 
                });
            } else {
                stream = await navigator.mediaDevices.getUserMedia({ 
                    video: { width: 1280, height: 720 }, 
                    audio: false 
                });
            }

            if (videoRef.current) {
                const video = videoRef.current;
                video.srcObject = stream;
                // Wait for real frame data (not just metadata) so captureFrame()
                // never fires against a zero-dimension video right after enabling vision.
                await new Promise<void>((resolve) => {
                    video.onloadedmetadata = () => {
                        video.play();
                    };
                    if (video.readyState >= video.HAVE_CURRENT_DATA) {
                        resolve();
                        return;
                    }
                    video.onloadeddata = () => resolve();
                });
            }

            streamRef.current = stream;
            setVisionType(type);
            setIsVisionEnabled(true);

            // Handle manual stream stop (e.g. user clicks "Stop Sharing" in browser)
            stream.getVideoTracks()[0].onended = () => {
                stopVision();
            };

            return true;
        } catch (err) {
            console.error("[Jarvis Vision] Failed to initialize stream:", err);
            return false;
        }
    }, []);

    const stopVision = useCallback(() => {
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop());
            streamRef.current = null;
        }
        if (videoRef.current) {
            videoRef.current.srcObject = null;
        }
        setIsVisionEnabled(false);
        setVisionType(null);
    }, []);

    const captureFrame = useCallback(() => {
        if (!isVisionEnabled || !videoRef.current) return null;
        return captureFrameUtil(videoRef.current);
    }, [isVisionEnabled]);

    return {
        isVisionEnabled,
        visionType,
        setIsVisionEnabled, // For manual overrides
        videoRef,
        canvasRef,
        startVision,
        stopVision,
        captureFrame
    };
}
