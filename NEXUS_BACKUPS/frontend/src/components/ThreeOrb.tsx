"use client";

import React, { useEffect, useRef } from "react";
import * as THREE from "three";
import gsap from "gsap";
import { logger } from "@/lib/logger";

export type OrbConfig = {
  scale?: number;
  speed?: number;
  noiseFreq?: number;
  noiseAmp?: number;
  color1?: string;
  color2?: string;
  volume?: number;
  isChecking?: boolean;
};

export function ThreeOrb({ config, className }: { config?: OrbConfig, className?: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sysRef = useRef<OrbSystem | null>(null);

  class OrbSystem {
    container: HTMLDivElement;
    options: Required<OrbConfig>;
    scene: THREE.Scene;
    camera: THREE.PerspectiveCamera;
    renderer: THREE.WebGLRenderer;
    meshGroup: THREE.Group;
    lightsGroup: THREE.Group;
    timer: THREE.Timer;
    animationId?: number;
    coreMesh?: THREE.Mesh;
    shellMesh?: THREE.Mesh;

    constructor(container: HTMLDivElement, opts: OrbConfig = {}) {
      this.container = container;
      this.options = {
        scale: opts.scale ?? 1,
        speed: opts.speed ?? 1,
        noiseFreq: opts.noiseFreq ?? 1,
        noiseAmp: opts.noiseAmp ?? 1,
        color1: opts.color1 ?? "#6366f1",
        color2: opts.color2 ?? "#4f46e5",
        volume: opts.volume ?? 0,
        isChecking: opts.isChecking ?? false,
      };

      this.scene = new THREE.Scene();
      this.camera = new THREE.PerspectiveCamera(
        75,
        this.container.clientWidth / this.container.clientHeight,
        0.1,
        1000
      );
      this.camera.position.z = 3;

      this.renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: true,
        powerPreference: "high-performance",
      });
      this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      this.container.appendChild(this.renderer.domElement);

      this.meshGroup = new THREE.Group();
      this.scene.add(this.meshGroup);

      this.lightsGroup = new THREE.Group();
      this.scene.add(this.lightsGroup);

      this.timer = new THREE.Timer();
      this.initContent();
      
      this.animate = this.animate.bind(this);
      this.animate();

      window.addEventListener("resize", this.handleResize);
      logger.info("OrbSystem initialized", { options: this.options });
    }

    handleResize = () => {
      if (!this.container || !this.renderer) return;
      const w = this.container.clientWidth;
      const h = this.container.clientHeight;
      this.camera.aspect = w / h;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(w, h);
    };

    initContent() {
      // Clear existing
      while (this.meshGroup.children.length > 0) {
        const child = this.meshGroup.children[0] as any;
        if (child.geometry) child.geometry.dispose();
        if (child.material) child.material.dispose();
        this.meshGroup.remove(child);
      }

      // Core
      const coreGeo = new THREE.IcosahedronGeometry(this.options.scale * 1.2, 15);
      const coreMat = new THREE.MeshPhongMaterial({
        color: new THREE.Color(this.options.color1),
        wireframe: true,
        transparent: true,
        opacity: 0.3,
      });
      this.coreMesh = new THREE.Mesh(coreGeo, coreMat);
      this.meshGroup.add(this.coreMesh);

      // Shell
      const shellGeo = new THREE.IcosahedronGeometry(this.options.scale * 1.5, 5);
      const shellMat = new THREE.MeshBasicMaterial({
        color: new THREE.Color(this.options.color2),
        wireframe: true,
        transparent: true,
        opacity: 0.1,
      });
      this.shellMesh = new THREE.Mesh(shellGeo, shellMat);
      this.meshGroup.add(this.shellMesh);

      // Lights
      const pLight = new THREE.PointLight(new THREE.Color(this.options.color1), 1, 10);
      pLight.position.set(2, 2, 2);
      this.lightsGroup.add(pLight);
      this.lightsGroup.add(new THREE.AmbientLight(0xffffff, 0.2));
    }

    updateConfig(newOpts: Partial<OrbConfig>) {
      const oldVolume = this.options.volume;
      this.options = { ...this.options, ...newOpts };

      if (newOpts.color1 && this.coreMesh) {
        (this.coreMesh.material as THREE.MeshPhongMaterial).color.set(newOpts.color1);
      }
      if (newOpts.color2 && this.shellMesh) {
        (this.shellMesh.material as THREE.MeshBasicMaterial).color.set(newOpts.color2);
      }

      if (this.options.volume !== oldVolume) {
        const targetScale = 1 + this.options.volume * 0.3;
        gsap.to(this.meshGroup.scale, {
          x: targetScale,
          y: targetScale,
          z: targetScale,
          duration: 0.15,
          ease: "power2.out",
        });
      }

      if (this.options.isChecking) {
        // Change colors during check
        if (this.coreMesh) (this.coreMesh.material as THREE.MeshPhongMaterial).color.set("#fbbf24"); // Amber
        if (this.shellMesh) (this.shellMesh.material as THREE.MeshBasicMaterial).color.set("#f59e0b");
      } else {
        // Reset colors
        if (this.coreMesh) (this.coreMesh.material as THREE.MeshPhongMaterial).color.set(this.options.color1);
        if (this.shellMesh) (this.shellMesh.material as THREE.MeshBasicMaterial).color.set(this.options.color2);
      }
    }

    animate() {
      if (!this.timer) return;
      this.animationId = requestAnimationFrame(this.animate);
      this.timer.update();
      const t = this.timer.getElapsed();

      if (this.meshGroup) {
        this.meshGroup.rotation.y += (this.options.isChecking ? 0.02 : 0.005) * this.options.speed;
        this.meshGroup.rotation.x += (this.options.isChecking ? 0.01 : 0.002) * this.options.speed;
        
        // Pulsing scale
        const pulse = Math.sin(t * 2) * 0.03;
        if (this.options.volume === 0) {
          this.meshGroup.scale.setScalar(1 + pulse);
        }
      }

      if (this.coreMesh) {
        this.coreMesh.rotation.z += 0.001;
      }

      if (this.shellMesh) {
        this.shellMesh.rotation.y -= 0.003;
      }

      this.renderer.render(this.scene, this.camera);
    }

    dispose() {
      if (this.animationId) cancelAnimationFrame(this.animationId);
      window.removeEventListener("resize", this.handleResize);
      this.renderer.dispose();
      if (this.container && this.renderer.domElement) {
        this.container.removeChild(this.renderer.domElement);
      }
      logger.info("OrbSystem disposed");
    }
  }

  useEffect(() => {
    if (!containerRef.current) return;
    const orb = new OrbSystem(containerRef.current, config);
    sysRef.current = orb;
    return () => orb.dispose();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (sysRef.current && config) {
      sysRef.current.updateConfig(config);
    }
  }, [config]);

  return <div ref={containerRef} className={className || "w-full h-full"} />;
}
