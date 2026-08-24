'use client';

import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import * as THREE from 'three';

type HexagramTempleProps = {
  hexagramBinary: string;
};

const TEMPLE_COLOR = '#43e8ff';

function NeonBar({ position, size, opacity = 0.85 }: { position: [number, number, number]; size: [number, number, number]; opacity?: number }) {
  const materialRef = useRef<THREE.MeshBasicMaterial>(null);

  useFrame(({ clock }) => {
    if (materialRef.current) materialRef.current.opacity = opacity * (0.72 + Math.sin(clock.elapsedTime * 1.8 + position[1]) * 0.18);
  });

  return (
    <mesh position={position}>
      <boxGeometry args={size} />
      <meshBasicMaterial ref={materialRef} color={TEMPLE_COLOR} transparent opacity={opacity} blending={THREE.AdditiveBlending} depthWrite={false} />
    </mesh>
  );
}

function HexagramLine({ bit, y, index }: { bit: string; y: number; index: number }) {
  const lineWidth = 6.4 - index * 0.12;
  if (bit === '1') {
    return <NeonBar position={[0, y, -3.6]} size={[lineWidth, 0.075, 0.075]} />;
  }

  const segmentWidth = (lineWidth - 0.5) / 2;
  return (
    <group>
      <NeonBar position={[-(segmentWidth + 0.25) / 2, y, -3.6]} size={[segmentWidth, 0.075, 0.075]} />
      <NeonBar position={[(segmentWidth + 0.25) / 2, y, -3.6]} size={[segmentWidth, 0.075, 0.075]} />
    </group>
  );
}

export default function HexagramTemple({ hexagramBinary }: HexagramTempleProps) {
  const bits = /^[01]{6}$/.test(hexagramBinary) ? hexagramBinary : '000000';

  return (
    <group position={[0.25, 0, 0]}>
      {bits.split('').map((bit, index) => (
        <HexagramLine key={`${index}-${bit}`} bit={bit} index={index} y={-4.5 + index * 1.8} />
      ))}
      <mesh position={[0, 0, -3.8]} rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[3.2, 3.24, 96]} />
        <meshBasicMaterial color={TEMPLE_COLOR} transparent opacity={0.16} blending={THREE.AdditiveBlending} depthWrite={false} />
      </mesh>
    </group>
  );
}