'use client';

import { Environment, OrbitControls } from '@react-three/drei';
import { Canvas, useFrame } from '@react-three/fiber';
import { DepthOfField, EffectComposer } from '@react-three/postprocessing';
import { useEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';
import CameraController from './CameraController';
import DataTornado from './DataTornado';
import HexagramTemple from './HexagramTemple';
import KnotFireworks from './KnotFireworks';
import ProbabilityBranches from './ProbabilityBranches';
import type { OracleBranch, Vector3Tuple } from '@/hooks/useMarketStream';
import { getTransitionRoute, type TransitionRoute } from '@/lib/portfolio';

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
  isGraphMode?: boolean;
  triggerFirework?: boolean;
  backgroundHex?: string;
  iChingHexagramSymbol?: string;
  trajectory?: Vector3Tuple[];
  oracleBranches?: OracleBranch[];
  resonance?: number;
  transitionRoute?: TransitionRoute;
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

function VoxelCollapse({ active }: { active: boolean }) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const startedAt = useRef<number | null>(null);
  const { matrices, colors } = useMemo(() => {
    const base = new THREE.Matrix4();
    const nextMatrices: THREE.Matrix4[] = [];
    const nextColors: THREE.Color[] = [];
    for (let index = 0; index < 420; index += 1) {
      const x = ((index * 37) % 160) / 20 - 4;
      const y = ((index * 61) % 100) / 20 - 2.5;
      const z = ((index * 17) % 50) / 10 - 1;
      base.makeTranslation(x, y, z).scale(new THREE.Vector3(0.035, 0.035, 0.035));
      nextMatrices.push(base.clone());
      nextColors.push(new THREE.Color().setHSL(0.48 + (index % 7) * 0.035, 0.7, 0.62));
    }
    return { matrices: nextMatrices, colors: nextColors };
  }, []);

  useEffect(() => {
    if (active) startedAt.current = performance.now();
    else startedAt.current = null;
    if (meshRef.current) {
      matrices.forEach((matrix, index) => meshRef.current?.setMatrixAt(index, matrix));
      meshRef.current.instanceMatrix.needsUpdate = true;
      meshRef.current.visible = true;
    }
  }, [active, matrices]);

  useFrame(() => {
    if (!meshRef.current || !active || startedAt.current === null) return;
    const progress = Math.min((performance.now() - startedAt.current) / 900, 1);
    const matrix = new THREE.Matrix4();
    const position = new THREE.Vector3();
    const scale = new THREE.Vector3();
    matrices.forEach((base, index) => {
      base.decompose(position, new THREE.Quaternion(), scale);
      position.z -= progress * (5 + (index % 11) * 0.35);
      scale.setScalar(0.035 * (1 - progress * 0.7));
      matrix.compose(position, new THREE.Quaternion(), scale);
      meshRef.current?.setMatrixAt(index, matrix);
    });
    meshRef.current.instanceMatrix.needsUpdate = true;
    meshRef.current.visible = progress < 1;
  });

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, matrices.length]} frustumCulled={false}>
      <cylinderGeometry args={[0.04, 0.04, 0.055, 6]} />
      <meshBasicMaterial vertexColors transparent opacity={0.9} />
    </instancedMesh>
  );
}

export default function TarotScene({ data, className }: TarotSceneProps) {
  const knotCenter = useMemo(() => new THREE.Vector3(0, 0, 0), []);
  const controlsRef = useRef<OrbitControlsImpl>(null);
  const route = data.transitionRoute ?? getTransitionRoute(data.resonance ?? (data.isEmperorSynchronized ? 0.82 : 0.34));
  const lensFocus = route === 'lens' && (data.isEmperorSynchronized || (data.resonance ?? 0) >= 0.58);

  return (
    <div className={className ?? 'relative h-[600px] w-full overflow-hidden rounded-xl bg-gray-950'}>
      <Canvas camera={{ position: [0, 0.8, 7], fov: 48, near: 0.01, far: 100 }} dpr={[1, 2]}>
        <color attach="background" args={['#030712']} />
        <fog attach="fog" args={['#030712', 7, 30]} />
        <ambientLight intensity={0.42} />
        <pointLight position={[4, 5, 4]} intensity={18} distance={18} color="#f8fafc" />
        <pointLight position={[-3, 1, 1]} intensity={8} distance={12} color={data.wuxingPhase === 'FIRE' ? '#ef4444' : '#22d3ee'} />

        <CameraController isZooming={lensFocus} isGraphMode={data.isGraphMode ?? !lensFocus} focusTarget={knotCenter} controls={controlsRef} />
        <OrbitControls ref={controlsRef} enabled={data.isGraphMode ?? !data.isEmperorSynchronized} enableDamping enableZoom />
        <TarotCard3D data={data} />
        <group position={[0.25, 0, 0]}>
          <HexagramTemple hexagramBinary={data.hexagramBinary ?? '101100'} />
          <DataTornado s15Volume={data.s15Volume} s15Delta={data.s15Delta} wuxingPhase={data.wuxingPhase} knotType={data.knotType ?? ''} isOverdrive={data.isOverdrive ?? false} trajectory={data.trajectory} />
          <ProbabilityBranches origin={data.trajectory?.at(-1)} branches={data.oracleBranches ?? []} />
          <KnotFireworks burstPosition={knotCenter} energy={data.elasticEnergy ?? 0} tarotColor={data.tarotColor ?? '#e0ff00'} backgroundHex={data.backgroundHex} triggerFirework={data.triggerFirework} burstId={data.burstId} active={Boolean(data.triggerFirework)} />
        </group>
        <VoxelCollapse active={route === 'voxel' && Boolean(data.triggerFirework)} />
        {lensFocus && <EffectComposer multisampling={0}><DepthOfField focusDistance={0.02} focalLength={0.12} bokehScale={8} height={480} /></EffectComposer>}
        <Environment preset="night" />
      </Canvas>
      <div className="pointer-events-none absolute left-5 top-5 font-mono text-[10px] uppercase tracking-[0.3em] text-white/50">
        {lensFocus ? 'lens focus / knot heart' : `${data.cardName} / ${data.symbol}`}
      </div>
    </div>
  );
}
