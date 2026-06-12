"use client";

import { useEffect, useRef } from "react";
import gsap from "gsap";

export function NexusOrb({ isListening, volume }: { isListening: boolean; volume: number }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const coreRef = useRef<HTMLDivElement>(null);
  const shellRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!coreRef.current || !shellRef.current) return;
    
    // Entrance Animation
    gsap.fromTo([coreRef.current, shellRef.current], 
      { scale: 0, opacity: 0 }, 
      { scale: 1, opacity: 1, duration: 1.5, ease: "elastic.out(1, 0.5)", stagger: 0.1 }
    );

    // Continuous 3D rotation using GSAP
    gsap.to(coreRef.current, {
      rotationX: 360,
      rotationY: 360,
      duration: 20,
      repeat: -1,
      ease: "none"
    });

    gsap.to(shellRef.current, {
      rotationX: -360,
      rotationY: 360,
      duration: 30,
      repeat: -1,
      ease: "none"
    });
  }, []);

  useEffect(() => {
    if (!coreRef.current || !shellRef.current) return;
    
    const targetScale = isListening ? 1 + volume * 0.4 : 1;
    const targetOpacity = isListening ? 0.8 + volume * 0.2 : 0.5;

    gsap.to(coreRef.current, {
      scale: targetScale,
      opacity: targetOpacity,
      duration: 0.1,
      ease: "power2.out"
    });

    gsap.to(shellRef.current, {
      scale: targetScale * 1.2,
      duration: 0.15,
      ease: "power2.out"
    });
  }, [volume, isListening]);

  // Create rings for the wireframe effect
  const renderRings = (className: string) => {
    return Array.from({ length: 6 }).map((_, i) => (
      <div 
        key={`h-${i}`} 
        className={`absolute inset-0 rounded-full border ${className}`}
        style={{ transform: `rotateX(${i * 30}deg)` }}
      />
    ));
  };

  const renderVerticalRings = (className: string) => {
    return Array.from({ length: 6 }).map((_, i) => (
      <div 
        key={`v-${i}`} 
        className={`absolute inset-0 rounded-full border ${className}`}
        style={{ transform: `rotateY(${i * 30}deg)` }}
      />
    ));
  };

  return (
    <div 
      ref={containerRef} 
      className="w-full h-full flex items-center justify-center relative overflow-visible"
      style={{ perspective: "1000px" }}
    >
      {/* Outer Shell */}
      <div 
        ref={shellRef}
        className="absolute w-[80%] h-[80%]"
        style={{ transformStyle: "preserve-3d" }}
      >
        {renderRings("border-indigo-500/20")}
        {renderVerticalRings("border-indigo-500/20")}
      </div>

      {/* Inner Core */}
      <div 
        ref={coreRef}
        className="absolute w-[60%] h-[60%]"
        style={{ transformStyle: "preserve-3d" }}
      >
        {renderRings("border-indigo-400/40")}
        {renderVerticalRings("border-indigo-400/40")}
        {/* Core Glow */}
        <div className="absolute inset-0 rounded-full bg-indigo-500/20 blur-xl"></div>
      </div>
    </div>
  );
}

