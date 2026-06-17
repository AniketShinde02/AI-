"use client";

import React, { useEffect, useRef } from "react";
import { useNexus } from "@/contexts/NexusContext";

export type VisionSource = 'camera' | 'screen' | 'off';

interface GeminiVisionProps {
  source: VisionSource;
}

export function GeminiVision({ source }: GeminiVisionProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  const { voiceEngine } = useNexus();
  const isGeminiLive = voiceEngine === 'gemini_live';

  const dispatchStatus = (message: string) => {
    window.dispatchEvent(new CustomEvent("nexus_status_event", { detail: { message } }));
  };

  useEffect(() => {
    let currentStream: MediaStream | null = null;

    const startStream = async () => {
      try {
        if (source === 'camera') {
          currentStream = await navigator.mediaDevices.getUserMedia({ video: { width: 1280, height: 720 } });
          dispatchStatus("Camera feed active");
        } else if (source === 'screen') {
          currentStream = await navigator.mediaDevices.getDisplayMedia({ video: { width: 1280, height: 720 } });
          dispatchStatus("Screen share active");
          
          currentStream.getVideoTracks()[0].onended = () => {
            dispatchStatus("Screen share ended natively");
            // Could dispatch an event to tell parent to reset to 'off'
            window.dispatchEvent(new CustomEvent("nexus_vision_stopped"));
          };
        }

        if (videoRef.current && currentStream) {
          videoRef.current.srcObject = currentStream;
        }
      } catch (error) {
        if (error instanceof Error && error.name === 'NotAllowedError') {
          console.warn("⚠️ Media permissions denied. Please allow microphone/camera access in your browser address bar.");
          dispatchStatus(`Media access denied: Check browser permissions.`);
        } else {
          console.error("Failed to start media:", error);
          dispatchStatus(`Media error: ${source}`);
        }
        window.dispatchEvent(new CustomEvent("nexus_vision_stopped"));
      }
    };

    if (source !== 'off') {
      startStream();
    }

    return () => {
      if (currentStream) {
        currentStream.getTracks().forEach(track => track.stop());
      }
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
    };
  }, [source]);

  // Extract frames every 1s if Gemini Live is active
  useEffect(() => {
    if (!isGeminiLive || source === 'off') return;
    
    const interval = setInterval(() => {
      const canvas = canvasRef.current;
      const video = videoRef.current;
      if (!canvas || !video) return;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      if (video.readyState === video.HAVE_ENOUGH_DATA) {
        canvas.width = 640;
        canvas.height = Math.floor((video.videoHeight / video.videoWidth) * 640);
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        const base64Jpeg = canvas.toDataURL("image/jpeg", 0.5).split(",")[1];
        window.dispatchEvent(new CustomEvent("nexus_vision_frame", { detail: { frame: base64Jpeg } }));
      }
    }, 1000); // 1 FPS

    return () => clearInterval(interval);
  }, [isGeminiLive, source]);

  if (source === 'off') return null;

  return (
    <div className="w-full h-full relative overflow-hidden bg-black flex items-center justify-center group/vision">
      <canvas ref={canvasRef} style={{ display: "none" }} />
      <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover opacity-90" />
      
      {/* Live Indicator overlay */}
      <div className="absolute top-4 right-4 flex items-center gap-2 z-20 px-3 py-1.5 bg-black/60 border border-[#ff3366]/40 clip-cut-sm backdrop-blur-md">
         <div className="w-2 h-2 rounded-full bg-[#ff3366] animate-pulse shadow-[0_0_10px_#ff3366]"></div>
         <span className="text-[10px] font-quantico font-bold text-white uppercase tracking-[0.2em]">
           {source === 'camera' ? 'Camera Live' : 'Screen Live'}
         </span>
      </div>
      
      {/* Corner Brackets */}
      <div className="absolute top-0 left-0 w-8 h-8 border-t-2 border-l-2 border-[#00FFFF]/50 pointer-events-none"></div>
      <div className="absolute top-0 right-0 w-8 h-8 border-t-2 border-r-2 border-[#00FFFF]/50 pointer-events-none"></div>
      <div className="absolute bottom-0 left-0 w-8 h-8 border-b-2 border-l-2 border-[#00FFFF]/50 pointer-events-none"></div>
      <div className="absolute bottom-0 right-0 w-8 h-8 border-b-2 border-r-2 border-[#00FFFF]/50 pointer-events-none"></div>
    </div>
  );
}
