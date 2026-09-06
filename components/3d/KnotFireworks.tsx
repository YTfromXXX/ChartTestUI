'use client';

import { useEffect, useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

type KnotFireworksProps = {
  burstPosition: THREE.Vector3;
  energy: number;
  tarotColor: string;
  backgroundHex?: string;
  triggerFirework?: boolean;
  burstId?: number;
  active?: boolean;
};

const vertexShader = `
  attribute vec3 aVelocity;
  attribute float aSeed;
  uniform float uTime;
  uniform float uLife;
  varying float vFade;
  varying float vSeed;
  void main() {
    float age = uTime;
    vec3 positionOffset = aVelocity * age;
    positionOffset.y -= 2.1 * age * age;
    vec3 transformed = position + positionOffset;
    vec4 viewPosition = modelViewMatrix * vec4(transformed, 1.0);
    gl_Position = projectionMatrix * viewPosition;
    gl_PointSize = clamp((7.0 + aSeed * 7.0) / max(1.0, -viewPosition.z * 0.12), 1.5, 18.0);
    vFade = max(0.0, 1.0 - age / max(uLife, 0.001));
    vSeed = aSeed;
  }
`;

const fragmentShader = `
  uniform vec3 uStartColor;
  uniform vec3 uEndColor;
  varying float vFade;
  varying float vSeed;
  void main() {
    float distanceToCenter = distance(gl_PointCoord, vec2(0.5));
    if (distanceToCenter > 0.5) discard;
    float core = 1.0 - smoothstep(0.0, 0.5, distanceToCenter);
    vec3 color = mix(uStartColor, uEndColor, clamp(vSeed + (1.0 - vFade) * 0.45, 0.0, 1.0));
    gl_FragColor = vec4(color * (core * core + 0.12), vFade * core);
  }
`;

export default function KnotFireworks({ burstPosition, energy, tarotColor, backgroundHex = '#e0ff00', triggerFirework = false, burstId = 0, active = true }: KnotFireworksProps) {
  const pointsRef = useRef<THREE.Points>(null);
  const materialRef = useRef<THREE.ShaderMaterial>(null);
  const elapsedRef = useRef(Number.POSITIVE_INFINITY);
  const previousTriggerRef = useRef(false);
  const particleCount = 24000;

  const [positions, velocities, seeds] = useMemo(() => {
    const nextPositions = new Float32Array(particleCount * 3);
    const nextVelocities = new Float32Array(particleCount * 3);
    const nextSeeds = new Float32Array(particleCount);

    for (let index = 0; index < particleCount; index += 1) {
      const offset = index * 3;
      nextPositions[offset] = burstPosition.x;
      nextPositions[offset + 1] = burstPosition.y;
      nextPositions[offset + 2] = burstPosition.z;

      const theta = Math.random() * Math.PI * 2;
      const z = Math.random() * 2 - 1;
      const radius = Math.sqrt(1 - z * z);
      const speed = (0.7 + Math.random() * 0.8) * Math.max(0.8, Math.min(energy / 1000, 8));
      nextSeeds[index] = Math.random();

      nextVelocities[offset] = radius * Math.cos(theta) * speed;
      nextVelocities[offset + 1] = radius * Math.sin(theta) * speed;
      nextVelocities[offset + 2] = z * speed;
    }

    return [nextPositions, nextVelocities, nextSeeds];
  }, [particleCount, energy]);

  useEffect(() => {
    const shouldBurst = triggerFirework && !previousTriggerRef.current;
    previousTriggerRef.current = triggerFirework;
    if (!shouldBurst && burstId === 0) return;
    elapsedRef.current = 0;
    for (let index = 0; index < particleCount; index += 1) {
      const offset = index * 3;
      positions[offset] = burstPosition.x;
      positions[offset + 1] = burstPosition.y;
      positions[offset + 2] = burstPosition.z;
    }
    const positionAttribute = pointsRef.current?.geometry.attributes.position;
    if (positionAttribute) positionAttribute.needsUpdate = true;
  }, [burstId, burstPosition, particleCount, positions, triggerFirework]);

  useFrame((_, delta) => {
    if (!pointsRef.current || !materialRef.current) return;
    if (elapsedRef.current !== Number.POSITIVE_INFINITY) elapsedRef.current += delta;
    materialRef.current.uniforms.uTime.value = elapsedRef.current;
    materialRef.current.uniforms.uStartColor.value.set(tarotColor);
    materialRef.current.uniforms.uEndColor.value.set(backgroundHex);
    pointsRef.current.visible = active && elapsedRef.current < 4.0;
  });

  return (
    <points ref={pointsRef} visible={active} frustumCulled={false}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} count={particleCount} array={positions} itemSize={3} />
        <bufferAttribute attach="attributes-aVelocity" args={[velocities, 3]} count={particleCount} array={velocities} itemSize={3} />
        <bufferAttribute attach="attributes-aSeed" args={[seeds, 1]} count={particleCount} array={seeds} itemSize={1} />
      </bufferGeometry>
      <shaderMaterial
        ref={materialRef}
        uniforms={{ uTime: { value: Number.POSITIVE_INFINITY }, uLife: { value: 4 }, uStartColor: { value: new THREE.Color(tarotColor) }, uEndColor: { value: new THREE.Color(backgroundHex) } }}
        vertexShader={vertexShader}
        fragmentShader={fragmentShader}
        transparent
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </points>
  );
}