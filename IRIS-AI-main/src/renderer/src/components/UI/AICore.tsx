import { Canvas, useFrame } from '@react-three/fiber'
import { useMemo, useRef } from 'react'
import * as THREE from 'three'

// ─────────────────────────────────────────────────────
// Color tokens — aligned with IRIS design system
// ─────────────────────────────────────────────────────
const C = {
  idle: new THREE.Color('#39ff14'), // pure neon green
  active: new THREE.Color('#00ffff'), // electric cyan
  dimIdle: new THREE.Color('#0b3300'), // deep dim green for outer shell
  ring: new THREE.Color('#39ff14'),
  ringGlow: new THREE.Color('#ccffb3') // bright neon glow
}

// ─────────────────────────────────────────────────────
// Particle shell — one concentric layer
// ─────────────────────────────────────────────────────
interface ShellProps {
  count: number
  radius: number
  pointSize: number
  rotSpeedY: number
  rotSpeedZ: number
  rotSpeedX: number
  baseOpacity: number
  isConnected: boolean
  isSpeaking: boolean
  timeOffset: number
}

function ParticleShell({
  count,
  radius,
  pointSize,
  rotSpeedY,
  rotSpeedZ,
  rotSpeedX,
  baseOpacity,
  isConnected,
  isSpeaking,
  timeOffset
}: ShellProps) {
  const ref = useRef<THREE.Points>(null)
  const volRef = useRef(0)

  const { positions, original, seeds } = useMemo(() => {
    const pos = new Float32Array(count * 3)
    const orig = new Float32Array(count * 3)
    const s = new Float32Array(count * 2) // seed x, seed y for per-particle noise

    for (let i = 0; i < count; i++) {
      // Uniform sphere distribution (Marsaglia method)
      let x, y, z, d
      do {
        x = Math.random() * 2 - 1
        y = Math.random() * 2 - 1
        z = Math.random() * 2 - 1
        d = x * x + y * y + z * z
      } while (d > 1 || d === 0)
      const n = 1 / Math.sqrt(d)
      const px = x * n * radius
      const py = y * n * radius
      const pz = z * n * radius

      pos[i * 3] = px
      pos[i * 3 + 1] = py
      pos[i * 3 + 2] = pz
      orig[i * 3] = px
      orig[i * 3 + 1] = py
      orig[i * 3 + 2] = pz

      s[i * 2] = Math.random() * Math.PI * 2 // phase offset
      s[i * 2 + 1] = 0.6 + Math.random() * 0.8 // amplitude weight
    }
    return { positions: pos, original: orig, seeds: s }
  }, [count, radius])

  const colorBuf = useMemo(() => {
    const c = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      c[i * 3] = C.idle.r
      c[i * 3 + 1] = C.idle.g
      c[i * 3 + 2] = C.idle.b
    }
    return c
  }, [count])

  const blendColor = useMemo(() => new THREE.Color(), [])

  useFrame((_, delta) => {
    if (!ref.current) return
    const pts = ref.current
    const geo = pts.geometry
    const mat = pts.material as THREE.PointsMaterial

    // Rotation — each shell on unique axes
    pts.rotation.y += delta * rotSpeedY
    pts.rotation.z += delta * rotSpeedZ
    pts.rotation.x += delta * rotSpeedX

    // Volume simulation
    const t = performance.now() * 0.001 + timeOffset
    let targetVol = 0
    if (isSpeaking) {
      const pulse = Math.pow(Math.abs(Math.sin(t * 10) * Math.cos(t * 6.3)), 1.6)
      targetVol = pulse * 0.7 + Math.random() * 0.15
    } else if (isConnected) {
      targetVol = Math.abs(Math.sin(t * 1.8)) * 0.04
    }
    volRef.current = THREE.MathUtils.lerp(volRef.current, targetVol, 0.18)
    const vol = volRef.current

    // Color lerp: idle green → speaking cyan
    blendColor.lerpColors(C.idle, C.active, vol * 1.8)
    mat.color.copy(blendColor)

    // Opacity
    const targetOpacity = isConnected ? baseOpacity + vol * 0.35 : baseOpacity * 0.35
    mat.opacity = THREE.MathUtils.lerp(mat.opacity, targetOpacity, 0.08)

    // Per-particle displacement — wave noise, not uniform expand
    const posArr = geo.attributes.position.array as Float32Array
    for (let i = 0; i < count; i++) {
      const ix = i * 3
      const phase = seeds[i * 2]
      const weight = seeds[i * 2 + 1]

      // Wave displacement along original normal direction
      const waveA = Math.sin(t * 8.5 + phase) * vol * weight * 0.18
      const waveB = Math.cos(t * 5.2 + phase * 0.7) * vol * weight * 0.09

      const ox = original[ix]
      const oy = original[ix + 1]
      const oz = original[ix + 2]
      const len = Math.sqrt(ox * ox + oy * oy + oz * oz) || 1

      posArr[ix] = ox + (ox / len) * (waveA + waveB)
      posArr[ix + 1] = oy + (oy / len) * (waveA - waveB * 0.5)
      posArr[ix + 2] = oz + (oz / len) * waveB
    }

    geo.attributes.position.needsUpdate = true
    geo.computeBoundingSphere()
  })

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[positions, 3]}
          usage={THREE.DynamicDrawUsage}
        />
        <bufferAttribute attach="attributes-color" args={[colorBuf, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={pointSize}
        transparent
        opacity={baseOpacity * 0.5}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
        depthWrite={false}
        vertexColors={false}
      />
    </points>
  )
}

// ─────────────────────────────────────────────────────
// Orbital ring — torus on a tilted axis
// ─────────────────────────────────────────────────────
function OrbitalRing({
  radius,
  tube,
  tilt,
  rotSpeed,
  isConnected,
  isSpeaking
}: {
  radius: number
  tube: number
  tilt: number
  rotSpeed: number
  isConnected: boolean
  isSpeaking: boolean
}) {
  const ref = useRef<THREE.Mesh>(null)
  const matRef = useRef<THREE.MeshBasicMaterial>(null)
  const volRef = useRef(0)

  useFrame((_, delta) => {
    if (!ref.current || !matRef.current) return

    ref.current.rotation.y += delta * rotSpeed
    ref.current.rotation.z += delta * rotSpeed * 0.3

    const t = performance.now() * 0.001
    let targetVol = 0
    if (isSpeaking) {
      targetVol = Math.abs(Math.sin(t * 9)) * 0.6 + 0.2
    } else if (isConnected) {
      targetVol = Math.abs(Math.sin(t * 1.5)) * 0.12
    }
    volRef.current = THREE.MathUtils.lerp(volRef.current, targetVol, 0.12)
    const vol = volRef.current

    // Color lerp on ring
    const ringColor = new THREE.Color().lerpColors(C.ring, C.ringGlow, vol)
    matRef.current.color.copy(ringColor)

    // Opacity: faint idle, bright when speaking
    const targetOp = isConnected ? 0.15 + vol * 0.65 : 0.04
    matRef.current.opacity = THREE.MathUtils.lerp(matRef.current.opacity, targetOp, 0.1)
  })

  return (
    <mesh ref={ref} rotation={[tilt, 0, 0]}>
      <torusGeometry args={[radius, tube, 3, 96]} />
      <meshBasicMaterial
        ref={matRef}
        color={C.ring}
        transparent
        opacity={0.08}
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </mesh>
  )
}

// ─────────────────────────────────────────────────────
// Core — assembles all layers + master scale
// ─────────────────────────────────────────────────────
function AIOrb({ isConnected, isSpeaking }: { isConnected: boolean; isSpeaking: boolean }) {
  const groupRef = useRef<THREE.Group>(null)

  useFrame((_, delta) => {
    if (!groupRef.current) return
    const targetScale = !isConnected ? 0.44 : isSpeaking ? 0.7 : 0.62
    groupRef.current.scale.lerp(
      new THREE.Vector3(targetScale, targetScale, targetScale),
      delta * 3.5
    )
    // Subtle slow Y drift
    groupRef.current.rotation.y += delta * 0.04
  })

  return (
    <group ref={groupRef}>
      {/* ── 3 concentric particle shells ── */}
      {/* Inner shell — densest, largest particles, slowest spin */}
      <ParticleShell
        count={1800}
        radius={1.15}
        pointSize={0.022}
        rotSpeedY={0.06}
        rotSpeedZ={0.04}
        rotSpeedX={0.02}
        baseOpacity={0.75}
        isConnected={isConnected}
        isSpeaking={isSpeaking}
        timeOffset={0}
      />

      {/* Mid shell — medium density, medium particles */}
      <ParticleShell
        count={2400}
        radius={1.55}
        pointSize={0.013}
        rotSpeedY={-0.09}
        rotSpeedZ={0.06}
        rotSpeedX={-0.03}
        baseOpacity={0.55}
        isConnected={isConnected}
        isSpeaking={isSpeaking}
        timeOffset={1.2}
      />

      {/* Outer shell — sparse, tiny particles, fastest spin */}
      <ParticleShell
        count={1400}
        radius={1.95}
        pointSize={0.008}
        rotSpeedY={0.12}
        rotSpeedZ={-0.08}
        rotSpeedX={0.05}
        baseOpacity={0.3}
        isConnected={isConnected}
        isSpeaking={isSpeaking}
        timeOffset={2.7}
      />

      {/* ── Orbital rings ── */}
      {/* Primary equatorial ring — thin, bright */}
      <OrbitalRing
        radius={1.42}
        tube={0.006}
        tilt={Math.PI * 0.08}
        rotSpeed={0.18}
        isConnected={isConnected}
        isSpeaking={isSpeaking}
      />

      {/* Secondary tilted ring — slightly wider tube */}
      <OrbitalRing
        radius={1.68}
        tube={0.004}
        tilt={Math.PI * 0.38}
        rotSpeed={-0.11}
        isConnected={isConnected}
        isSpeaking={isSpeaking}
      />

      {/* Tertiary polar ring — thinnest, very faint */}
      <OrbitalRing
        radius={1.28}
        tube={0.003}
        tilt={Math.PI * 0.5}
        rotSpeed={0.22}
        isConnected={isConnected}
        isSpeaking={isSpeaking}
      />
    </group>
  )
}

// ─────────────────────────────────────────────────────
// Export
// ─────────────────────────────────────────────────────
export default function AICore({
  isConnected = false,
  isSpeaking = false
}: {
  isConnected?: boolean
  isSpeaking?: boolean
}) {
  return (
    <div className="absolute inset-0 flex items-center justify-center z-0 pointer-events-none">
      <Canvas
        style={{ width: '100%', height: '100%' }}
        camera={{ position: [0, 0, 5], fov: 42 }}
        gl={{
          antialias: true,
          powerPreference: 'high-performance',
          alpha: true
        }}
      >
        {/* Minimal ambient — particles use AdditiveBlending so lights don't matter */}
        <ambientLight intensity={0} />
        <AIOrb isConnected={isConnected} isSpeaking={isSpeaking} />
      </Canvas>
    </div>
  )
}
