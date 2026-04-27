"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";
import gsap from "gsap";

/**
 * Iridescent Liquid Glass Core Orb
 * Specification:
 * 1. Geometry: High-poly Icosahedron (Subdivided 5x)
 * 2. Surface: 3D Simplex Noise for organic protrusions
 * 3. Material: Glassmorphic, High Refractive Index, Fresnel Rim Lighting
 * 4. Palette: Electric Cyan, Deep Purple, Soft Magenta
 * 5. Animation: Audio-reactive pulsing and shivering
 */

const snoiseFunc = `
vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 permute(vec4 x) { return mod289(((x*34.0)+1.0)*x); }
vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }

float snoise(vec3 v) { 
  const vec2  C = vec2(1.0/6.0, 1.0/3.0) ;
  const vec4  D = vec4(0.0, 0.5, 1.0, 2.0);

  vec3 i  = floor(v + dot(v, C.yyy) );
  vec3 x0 =   v - i + dot(i, C.xxx) ;

  vec3 g = step(x0.yzx, x0.xyz);
  vec3 l = 1.0 - g;
  vec3 i1 = min( g.xyz, l.zxy );
  vec3 i2 = max( g.xyz, l.zxy );

  vec3 x1 = x0 - i1 + C.xxx;
  vec3 x2 = x0 - i2 + C.yyy;
  vec3 x3 = x0 - D.yyy;

  i = mod289(i); 
  vec4 p = permute( permute( permute( 
             i.z + vec4(0.0, i1.z, i2.z, 1.0 ))
           + i.y + vec4(0.0, i1.y, i2.y, 1.0 )) 
           + i.x + vec4(0.0, i1.x, i2.x, 1.0 ));

  float n_ = 1.0/7.0;
  vec3  ns = n_ * D.wyz - D.xzx;

  vec4 j = p - 49.0 * floor(p * ns.z * ns.z);

  vec4 x_ = floor(j * ns.z);
  vec4 y_ = floor(j - 7.0 * x_ );

  vec4 x = x_ *ns.x + ns.yyyy;
  vec4 y = y_ *ns.x + ns.yyyy;
  vec4 h = 1.0 - abs(x) - abs(y);

  vec4 b0 = vec4( x.xy, y.xy );
  vec4 b1 = vec4( x.zw, y.zw );

  vec4 s0 = floor(b0)*2.0 + 1.0;
  vec4 s1 = floor(b1)*2.0 + 1.0;
  vec4 sh = -step(h, vec4(0.0));

  vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy ;
  vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww ;

  vec3 p0 = vec3(a0.xy,h.x);
  vec3 p1 = vec3(a0.zw,h.y);
  vec3 p2 = vec3(a1.xy,h.z);
  vec3 p3 = vec3(a1.zw,h.w);

  vec4 sig = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2,p2), dot(p3,p3)));
  p0 *= sig.x;
  p1 *= sig.y;
  p2 *= sig.z;
  p3 *= sig.w;

  vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
  m = m * m;
  return 42.0 * dot( m*m, vec4( dot(p0,x0), dot(p1,x1), 
                                dot(p2,x2), dot(p3,x3) ) );
}
`;

const glassVertexShader = `
uniform float uTime;
uniform float uAudioAmplitude;
uniform float uAudioTreble;
varying vec3 vNormal;
varying vec3 vViewPosition;
varying float vNoise;

${snoiseFunc}

void main() {
  vNormal = normalize(normalMatrix * normal);
  
  float noise = snoise(position + uTime * 0.4);
  float audioNoise = snoise(position * 2.0 + uTime * 3.0) * uAudioAmplitude * 0.5;
  float trebleNoise = snoise(position * 10.0 + uTime * 20.0) * uAudioTreble * 0.1;
  
  vNoise = noise + audioNoise + trebleNoise;
  
  vec3 newPosition = position + normal * (vNoise * 0.12);
  vec4 mvPosition = modelViewMatrix * vec4(newPosition, 1.0);
  vViewPosition = -mvPosition.xyz;
  
  gl_Position = projectionMatrix * mvPosition;
}
`;

const glassFragmentShader = `
uniform float uTime;
varying vec3 vNormal;
varying vec3 vViewPosition;
varying float vNoise;

void main() {
  vec3 normal = normalize(vNormal);
  vec3 viewDir = normalize(vViewPosition);
  
  float fresnel = pow(1.0 - dot(normal, viewDir), 3.0);
  
  // Sharp grazing edge rim light
  float rim = pow(1.0 - dot(normal, viewDir), 5.0) * 2.0;
  
  // Specular "caustic" highlights
  float spec = pow(max(0.0, vNoise), 8.0) * 0.6;
  
  vec3 finalColor = vec3(1.0) * (rim + spec + fresnel * 0.5);
  
  // Glass transparency
  float alpha = clamp(fresnel * 0.8 + spec * 0.5, 0.1, 0.9);
  
  gl_FragColor = vec4(finalColor, alpha);
}
`;

const coreVertexShader = `
uniform float uTime;
uniform float uAudioAmplitude;
varying vec2 vUv;
varying vec3 vNormal;
varying float vNoise;

${snoiseFunc}

void main() {
  vUv = uv;
  vNormal = normalize(normalMatrix * normal);
  
  float noise = snoise(position * 1.5 + uTime * 0.6);
  vNoise = noise;
  
  vec3 newPosition = position * (0.85 + noise * 0.1 + uAudioAmplitude * 0.2);
  gl_Position = projectionMatrix * modelViewMatrix * vec4(newPosition, 1.0);
}
`;

const coreFragmentShader = `
uniform float uTime;
uniform vec3 uColorCyan;
uniform vec3 uColorPurple;
uniform vec3 uColorMagenta;
varying vec2 vUv;
varying vec3 vNormal;
varying float vNoise;

void main() {
  float noiseFactor = (vNoise + 1.0) * 0.5;
  
  vec3 color = mix(uColorPurple, uColorCyan, noiseFactor);
  color = mix(color, uColorMagenta, sin(uTime + vUv.x * 3.0) * 0.5 + 0.5);
  
  // Internal "cloudy" glow
  float glow = pow(noiseFactor, 2.0) * 1.5;
  
  gl_FragColor = vec4(color * glow, 0.8);
}
`;

export function NexusOrb({ isListening, volume }: { isListening: boolean; volume: number }) {
  const mountRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const orbRef = useRef<THREE.Group | null>(null);
  
  const uniforms = useRef({
    uTime: { value: 0 },
    uAudioAmplitude: { value: 0 },
    uAudioTreble: { value: 0 },
    uColorCyan: { value: new THREE.Color("#00F0FF") },
    uColorPurple: { value: new THREE.Color("#6D28D9") },
    uColorMagenta: { value: new THREE.Color("#F472B6") },
  });

  useEffect(() => {
    if (!mountRef.current) return;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 1000);
    camera.position.z = 3.5;

    const renderer = new THREE.WebGLRenderer({ 
      antialias: true, 
      alpha: true,
      powerPreference: "high-performance" 
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);
    
    // Clear any existing children to prevent duplicates (Strict Mode)
    if (mountRef.current) {
      mountRef.current.innerHTML = "";
      mountRef.current.appendChild(renderer.domElement);
    }
    rendererRef.current = renderer;

    // Handle Context Loss (Senior Production Requirement)
    const handleContextLoss = (event: Event) => {
      event.preventDefault();
      console.warn("Nexus Core: WebGL Context Lost");
      cancelAnimationFrame(animationId);
    };

    const handleContextRestored = () => {
      console.log("Nexus Core: WebGL Context Restored");
      window.location.reload(); // Simplest robust recovery
    };

    renderer.domElement.addEventListener("webglcontextlost", handleContextLoss, false);
    renderer.domElement.addEventListener("webglcontextrestored", handleContextRestored, false);

    const updateSize = () => {
      if (!mountRef.current) return;
      const { clientWidth, clientHeight } = mountRef.current;
      renderer.setSize(clientWidth, clientHeight);
      camera.aspect = clientWidth / clientHeight;
      camera.updateProjectionMatrix();
    };
    updateSize();
    window.addEventListener("resize", updateSize);

    const group = new THREE.Group();
    orbRef.current = group;
    scene.add(group);

    // Shared high-poly geometry
    const geometry = new THREE.IcosahedronGeometry(1.0, 64);

    // 1. Core cloudy emission
    const coreMaterial = new THREE.ShaderMaterial({
      uniforms: uniforms.current,
      vertexShader: coreVertexShader,
      fragmentShader: coreFragmentShader,
      transparent: true,
      blending: THREE.AdditiveBlending,
    });
    const core = new THREE.Mesh(geometry, coreMaterial);
    group.add(core);

    // 2. Glass outer shell
    const glassMaterial = new THREE.ShaderMaterial({
      uniforms: uniforms.current,
      vertexShader: glassVertexShader,
      fragmentShader: glassFragmentShader,
      transparent: true,
      side: THREE.DoubleSide,
    });
    const shell = new THREE.Mesh(geometry, glassMaterial);
    shell.scale.set(1.05, 1.05, 1.05);
    group.add(shell);

    // Entrance Animation (Senior Design Detail)
    gsap.fromTo(group.scale, 
      { x: 0, y: 0, z: 0 }, 
      { x: 1, y: 1, z: 1, duration: 1.5, ease: "elastic.out(1, 0.5)", delay: 0.2 }
    );
    gsap.fromTo(group.rotation,
      { y: -Math.PI },
      { y: 0, duration: 2, ease: "power3.out" }
    );

    let animationId: number;
    const animate = (time: number) => {
      animationId = requestAnimationFrame(animate);
      uniforms.current.uTime.value = time * 0.001;

      if (group) {
        group.rotation.y += 0.003;
        group.rotation.z += 0.001;
      }

      renderer.render(scene, camera);
    };
    animate(0);

    return () => {
      window.removeEventListener("resize", updateSize);
      cancelAnimationFrame(animationId);
      geometry.dispose();
      coreMaterial.dispose();
      glassMaterial.dispose();
      renderer.domElement.removeEventListener("webglcontextlost", handleContextLoss);
      renderer.domElement.removeEventListener("webglcontextrestored", handleContextRestored);
      renderer.dispose();
      if (mountRef.current) {
        mountRef.current.innerHTML = "";
      }
    };
  }, []);

  useEffect(() => {
    const targetAmplitude = isListening ? volume * 0.8 : 0.05;
    const targetTreble = isListening ? volume * 1.5 : 0.02;

    gsap.to(uniforms.current.uAudioAmplitude, {
      value: targetAmplitude,
      duration: 0.1,
      ease: "power2.out"
    });

    gsap.to(uniforms.current.uAudioTreble, {
      value: targetTreble,
      duration: 0.05,
      ease: "power1.out"
    });
  }, [volume, isListening]);

  return (
    <div 
      ref={mountRef} 
      className="w-full h-full flex items-center justify-center relative overflow-visible"
    />
  );
}
