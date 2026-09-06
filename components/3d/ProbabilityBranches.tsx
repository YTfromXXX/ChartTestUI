'use client';

import { Text } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import { useMemo, useRef } from 'react';
import * as THREE from 'three';
import type { OracleBranch, Vector3Tuple } from '@/hooks/useMarketStream';

type ProbabilityBranchesProps = {
  origin?: Vector3Tuple;
  branches: OracleBranch[];
};

const BRANCHES = [
  { id: 'wands', label: 'SURGE', color: '#ffd700', offset: -0.72, direction: [0.2, 3.6, 0] as Vector3Tuple },
  { id: 'swords', label: 'TREND', color: '#00ffff', offset: -0.24, direction: [1.1, 2.2, 0.15] as Vector3Tuple },
  { id: 'cups', label: 'RANGE', color: '#ffffff', offset: 0.24, direction: [1.7, 0.55, 0.1] as Vector3Tuple },
  { id: 'pentacles', label: 'DROP', color: '#a855f7', offset: 0.72, direction: [0.6, -3.2, -0.2] as Vector3Tuple },
];

function Laser({ branch, probability, origin }: { branch: (typeof BRANCHES)[number]; probability: number; origin: THREE.Vector3 }) {
  const warningRef = useRef<THREE.Group>(null);
  const curve = useMemo(() => {
    const [dx, dy, dz] = branch.direction;
    const start = origin.clone().add(new THREE.Vector3(branch.offset, 0, 0));
    const end = start.clone().add(new THREE.Vector3(dx, dy, dz));
    const control = start.clone().lerp(end, 0.5).add(new THREE.Vector3(branch.id === 'cups' ? 0.35 : -0.1, branch.id === 'cups' ? 0.35 : 0, 0.25));
    return new THREE.CatmullRomCurve3([start, control, end]);
  }, [branch, origin]);
  const radius = 0.012 + Math.max(0, Math.min(100, probability)) / 100 * 0.045;
  const opacity = 0.16 + Math.max(0, Math.min(100, probability)) / 100 * 0.84;
  const isWarning = branch.id === 'pentacles' && probability > 30;

  useFrame(({ clock }) => {
    if (warningRef.current) warningRef.current.visible = !isWarning || Math.sin(clock.elapsedTime * 12) > -0.2;
  });

  return (
    <group>
      <mesh>
        <tubeGeometry args={[curve, 32, radius, 6, false]} />
        <meshBasicMaterial color={branch.color} transparent opacity={opacity} blending={THREE.AdditiveBlending} depthWrite={false} />
      </mesh>
      <group ref={warningRef} position={curve.getPointAt(0.92, new THREE.Vector3())}>
        <Text fontSize={0.16} color={isWarning ? '#ff355d' : branch.color} anchorX="center" anchorY="middle" outlineColor="#050816" outlineWidth={0.012} fillOpacity={opacity}>
          [{probability.toFixed(1)}%]
        </Text>
        <Text position={[0, -0.19, 0]} fontSize={0.075} color={isWarning ? '#ff355d' : branch.color} anchorX="center" anchorY="middle" fillOpacity={0.72}>
          {branch.label}
        </Text>
      </group>
    </group>
  );
}

export default function ProbabilityBranches({ origin = [0, 0, 0], branches }: ProbabilityBranchesProps) {
  const originVector = useMemo(() => new THREE.Vector3(...origin), [origin]);
  return (
    <group>
      {BRANCHES.map((branch) => (
        <Laser key={branch.id} branch={branch} probability={branches.find((item) => item.id === branch.id)?.probability ?? branches[BRANCHES.indexOf(branch)]?.probability ?? 0} origin={originVector} />
      ))}
    </group>
  );
}