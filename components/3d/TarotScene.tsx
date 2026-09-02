'use client';

import { Environment, OrbitControls } from '@react-three/drei';
import { Canvas, useFrame } from '@react-three/fiber';
import { useMemo, useRef } from 'react';
import * as THREE from 'three';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';
import CameraController from './CameraController';
import DataTornado from './DataTornado';
import HexagramTemple from './HexagramTemple';
import KnotFireworks from './KnotFireworks';

type TarotSceneData = {
  cardName: string;
  symbol: string;
  knotType?: string;
  wuxingPhase: string;
  isEmperorSynchronized: boolean;
  s15Volume: number;
  s15Delta: number;
  isOverdrive?: boolean;
  hexagramBinary?: string;
  elasticEnergy?: number;
  burstId?: number;
  tarotColor?: string;
};

type TarotSceneProps = {
  data: TarotSceneData;
  className?: string;
};

function TarotCard3D({ data }: { data: TarotSceneData }) {
  const groupRef = useRef<THREE.Group>(null);
  const accent = data.wuxingPhase === 'FIRE' ? '#ef4444' : data.wuxingPhase === 'WATER' ? '#22d3ee' : '#facc15';

  useFrame((state) => {
    if (!groupRef.current) return;
    groupRef.current.rotation.y = Math.sin(state.clock.getElapsedTime() * 0.25) * 0.08;
    groupRef.current.position.y = Math.sin(state.clock.getElapsedTime() * 0.45) * 0.04;
  });

  return (
    <group ref={groupRef} position={[-2.8, 0, 0]} rotation={[0, 0.28, 0]}>
      <mesh>
        <boxGeometry args={[2.2, 3.4, 0.12]} />
        <meshStandardMaterial color="#111827" emissive={accent} emissiveIntensity={data.isEmperorSynchronized ? 0.55 : 0.16} metalness={0.7} roughness={0.28} />
      </mesh>
      <mesh position={[0, 0, 0.08]}>
        <planeGeometry args={[1.85, 3.05]} />
        <meshBasicMaterial color={accent} transparent opacity={0.12} />
      </mesh>
    </group>
  );
}

export default function TarotScene({ data, className }: TarotSceneProps) {
  const knotCenter = useMemo(() => new THREE.Vector3(0, 0, 0), []);
  const controlsRef = useRef<OrbitControlsImpl>(null);

  return (
    <div className={className ?? 'relative h-[600px] w-full overflow-hidden rounded-xl bg-gray-950'}>
      <Canvas camera={{ position: [0, 0.8, 7], fov: 48, near: 0.01, far: 100 }} dpr={[1, 2]}>
        <color attach="background" args={['#030712']} />
        <fog attach="fog" args={['#030712', 7, 30]} />
        <ambientLight intensity={0.42} />
        <pointLight position={[4, 5, 4]} intensity={18} distance={18} color="#f8fafc" />
        <pointLight position={[-3, 1, 1]} intensity={8} distance={12} color={data.wuxingPhase === 'FIRE' ? '#ef4444' : '#22d3ee'} />

        <CameraController isZooming={data.isEmperorSynchronized} focusTarget={knotCenter} controls={controlsRef} />
        <OrbitControls ref={controlsRef} enabled={!data.isEmperorSynchronized} enableDamping enableZoom />
        <TarotCard3D data={data} />
        <group position={[0.25, 0, 0]}>
          <HexagramTemple hexagramBinary={data.hexagramBinary ?? '101100'} />
          <DataTornado s15Volume={data.s15Volume} s15Delta={data.s15Delta} wuxingPhase={data.wuxingPhase} knotType={data.knotType ?? ''} isOverdrive={data.isOverdrive ?? false} />
          <KnotFireworks burstPosition={knotCenter} energy={data.elasticEnergy ?? 0} tarotColor={data.tarotColor ?? '#e0ff00'} burstId={data.burstId ?? 0} />
        </group>
        <Environment preset="night" />
      </Canvas>
      <div className="pointer-events-none absolute left-5 top-5 font-mono text-[10px] uppercase tracking-[0.3em] text-white/50">
        {data.isEmperorSynchronized ? 'deep dive / knot heart' : `${data.cardName} / ${data.symbol}`}
      </div>
    </div>
  );
}
