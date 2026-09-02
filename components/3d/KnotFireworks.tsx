'use client';

import { useEffect, useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

type KnotFireworksProps = {
  burstPosition: THREE.Vector3;
  energy: number;
  tarotColor: string;
  active?: boolean;
};

export default function KnotFireworks({ burstPosition, energy, tarotColor, active = true }: KnotFireworksProps) {
  const pointsRef = useRef<THREE.Points>(null);
  const particleCount = Math.min(1000, Math.max(120, Math.floor(energy / 10)));

  const [positions, velocities] = useMemo(() => {
    const nextPositions = new Float32Array(particleCount * 3);
    const nextVelocities = new Float32Array(particleCount * 3);

    for (let index = 0; index < particleCount; index += 1) {
      const offset = index * 3;
      nextPositions[offset] = burstPosition.x;
      nextPositions[offset + 1] = burstPosition.y;
      nextPositions[offset + 2] = burstPosition.z;

      const theta = Math.random() * Math.PI * 2;
      const z = Math.random() * 2 - 1;
      const radius = Math.sqrt(1 - z * z);
      const speed = (0.5 + Math.random() * 0.5) * Math.min(energy / 1000, 8);

      nextVelocities[offset] = radius * Math.cos(theta) * speed;
      nextVelocities[offset + 1] = radius * Math.sin(theta) * speed;
      nextVelocities[offset + 2] = z * speed;
    }

    return [nextPositions, nextVelocities];
  }, [burstPosition, energy, particleCount]);

  useEffect(() => {
    if (!pointsRef.current) return;

    const positionArray = pointsRef.current.geometry.attributes.position.array as Float32Array;
    for (let index = 0; index < particleCount; index += 1) {
      const offset = index * 3;
      positionArray[offset] = burstPosition.x;
      positionArray[offset + 1] = burstPosition.y;
      positionArray[offset + 2] = burstPosition.z;
    }

    pointsRef.current.geometry.attributes.position.needsUpdate = true;
  }, [active, burstPosition, particleCount]);

  useFrame((_, delta) => {
    if (!active || !pointsRef.current) return;

    const positionArray = pointsRef.current.geometry.attributes.position.array as Float32Array;
    for (let index = 0; index < particleCount; index += 1) {
      const offset = index * 3;
      velocities[offset + 1] -= 2.5 * delta;
      velocities[offset] *= 0.985;
      velocities[offset + 1] *= 0.985;
      velocities[offset + 2] *= 0.985;
      positionArray[offset] += velocities[offset] * delta;
      positionArray[offset + 1] += velocities[offset + 1] * delta;
      positionArray[offset + 2] += velocities[offset + 2] * delta;
    }

    pointsRef.current.geometry.attributes.position.needsUpdate = true;
  });

  return (
    <points ref={pointsRef} visible={active} frustumCulled={false}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} count={particleCount} array={positions} itemSize={3} />
      </bufferGeometry>
      <pointsMaterial size={0.08} color={tarotColor} transparent opacity={0.9} blending={THREE.AdditiveBlending} depthWrite={false} />
    </points>
  );
}