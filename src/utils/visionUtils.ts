/**
 * Captures a frame from a given video element.
 * Centralized to ensure consistent resolution and compression across the app.
 */
export const captureFrame = (videoElement: HTMLVideoElement | null): string | null => {
    if (!videoElement) {
        console.error("[Jarvis Core] Video element not found for frame capture.");
        return null;
    }

    // Neural Proximity Scaling: Maximize speed by capping resolution at 1024px
    const MAX_DIMENSION = 1024;
    let width = videoElement.videoWidth;
    let height = videoElement.videoHeight;

    if (width > MAX_DIMENSION || height > MAX_DIMENSION) {
        const ratio = Math.min(MAX_DIMENSION / width, MAX_DIMENSION / height);
        width = Math.round(width * ratio);
        height = Math.round(height * ratio);
    }

    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    
    const ctx = canvas.getContext('2d', { alpha: false });
    if (!ctx) {
        console.error("[Jarvis Core] Failed to get 2D context for frame capture.");
        return null;
    }

    ctx.drawImage(videoElement, 0, 0, width, height);
    
    // Captured as JPEG with 0.65 quality to balance speed and visual clarity.
    // Quality 0.65 is the 'Golden Ratio' for Vision LLMs over high-latency tunnels.
    return canvas.toDataURL('image/jpeg', 0.65).split(',')[1];
};
