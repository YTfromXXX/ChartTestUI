'use client';

import { CanvasTexture, Color, MeshPhysicalMaterial, SRGBColorSpace } from 'three';
import { Canvas, useFrame } from '@react-three/fiber';
import { useEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';
import type { PortfolioProfile } from '@/lib/portfolio';

type DogMagicianProps = { portfolio: PortfolioProfile; articleText: string; className?: string };

function Newspaper({ articleText }: { articleText: string }) {
  const texture = useMemo(() => {
    const canvas = document.createElement('canvas');
    canvas.width = 640;
    canvas.height = 420;
    return { canvas, texture: new CanvasTexture(canvas) };
  }, []);

  useEffect(() => {
    const context = texture.canvas.getContext('2d');
    if (!context) return;
    context.fillStyle = '#e7dfc9';
    context.fillRect(0, 0, texture.canvas.width, texture.canvas.height);
    context.fillStyle = '#17202b';
    context.font = 'bold 34px Georgia';
    context.fillText('THE RELATIVE EFFECT', 24, 48);
    context.strokeStyle = '#7c6f5a';
    context.strokeRect(18, 66, 604, 330);
    context.font = '18px Georgia';
    const words = articleText.split(' ');
    let line = '';
    let y = 108;
    words.forEach((word) => {
      const next = `${line} ${word}`.trim();
      if (context.measureText(next).width > 555) {
        context.fillText(line, 32, y);
        line = word;
        y += 30;
      } else line = next;
    });
    context.fillText(line, 32, y);
    texture.texture.colorSpace = SRGBColorSpace;
    texture.texture.needsUpdate = true;
  }, [articleText, texture]);

  return <mesh position={[0.72, -0.15, 0.2]} rotation={[0.1, -0.28, -0.1]}><planeGeometry args={[1.9, 1.25]} /><meshBasicMaterial map={texture.texture} /></mesh>;
}

function Hair({ portfolio }: { portfolio: PortfolioProfile }) {
  const ref = useRef<THREE.InstancedMesh>(null);
  const count = 72;
  const pattern = portfolio.diversification;
  useEffect(() => {
    if (!ref.current) return;
    const matrix = new THREE.Matrix4();
    for (let index = 0; index < count; index += 1) {
      const angle = (index / count) * Math.PI * 2;
      const radius = 0.48 + (index % 4) * 0.035;
      matrix.makeTranslation(Math.cos(angle) * radius, 1.32 + Math.sin(index * 1.7) * 0.08 + portfolio.totalAssetDeviation * 0.52, Math.sin(angle) * radius);
      ref.current.setMatrixAt(index, matrix);
      ref.current.setColorAt(index, new Color().setHSL((pattern * 0.22 + index / count * 0.38) % 1, 0.72, 0.56));
    }
    ref.current.instanceMatrix.needsUpdate = true;
    if (ref.current.instanceColor) ref.current.instanceColor.needsUpdate = true;
  }, [pattern, portfolio.totalAssetDeviation]);
  return <instancedMesh ref={ref} args={[undefined, undefined, count]}><boxGeometry args={[0.12, 0.12, 0.12]} /><meshStandardMaterial vertexColors roughness={0.38} metalness={0.2} /></instancedMesh>;
}

function MagicianModel({ portfolio, articleText }: DogMagicianProps) {
  const group = useRef<THREE.Group>(null);
  const lensColor = useMemo(() => new Color().setHSL(0.55 + portfolio.volatility * 0.92, 0.85, 0.58), [portfolio.volatility]);
  useFrame((state) => { if (group.current) group.current.rotation.y = Math.sin(state.clock.elapsedTime * 0.35) * 0.12; });
  return <group ref={group} position={[0, -1.1, 0]}>
    <mesh position={[0, 0.4, 0]}><sphereGeometry args={[0.92, 32, 24]} /><meshStandardMaterial color="#b8794f" roughness={0.65} /></mesh>
    <mesh position={[0, 1.18, 0.05]}><sphereGeometry args={[0.72, 32, 24]} /><meshStandardMaterial color="#c98b60" roughness={0.62} /></mesh>
    <mesh position={[-0.54, 1.65, 0]} rotation={[0, 0, -0.28]}><coneGeometry args={[0.24, 0.72, 4]} /><meshStandardMaterial color="#9a5c3d" roughness={0.7} /></mesh>
    <mesh position={[0.54, 1.65, 0]} rotation={[0, 0, 0.28]}><coneGeometry args={[0.24, 0.72, 4]} /><meshStandardMaterial color="#9a5c3d" roughness={0.7} /></mesh>
    <mesh position={[0, 1.04, 0.66]}><sphereGeometry args={[0.28, 20, 14]} /><meshStandardMaterial color="#efd3b1" roughness={0.78} /></mesh>
    <mesh position={[0, 1.08, 0.9]}><sphereGeometry args={[0.08, 16, 12]} /><meshStandardMaterial color="#241a18" /></mesh>
    <mesh position={[-0.29, 1.35, 0.62]}><circleGeometry args={[0.2, 24]} /><meshPhysicalMaterial color={lensColor} transmission={0.42 + (1 - portfolio.volatility) * 0.42} transparent opacity={0.7} roughness={0.08} metalness={0.15} thickness={0.18} /></mesh>
    <mesh position={[0.29, 1.35, 0.62]}><circleGeometry args={[0.2, 24]} /><meshPhysicalMaterial color={lensColor} transmission={0.42 + (1 - portfolio.volatility) * 0.42} transparent opacity={0.7} roughness={0.08} metalness={0.15} thickness={0.18} /></mesh>
    <mesh position={[0, 1.35, 0.62]}><boxGeometry args={[0.18, 0.045, 0.04]} /><meshStandardMaterial color="#2b1f25" metalness={0.8} /></mesh>
    <mesh position={[0.3, 0.15, 0.7]} rotation={[0, -0.15, 0.1]}><boxGeometry args={[0.18, 1.4, 0.18]} /><meshStandardMaterial color="#5a3b83" roughness={0.5} /></mesh>
    <Hair portfolio={portfolio} />
    <Newspaper articleText={articleText} />
  </group>;
}

export default function DogMagician({ portfolio, articleText, className }: DogMagicianProps) {
  return <div className={className ?? 'h-[520px] w-full'}><Canvas camera={{ position: [0, 0.8, 5.8], fov: 34 }}><color attach="background" args={['#091018']} /><ambientLight intensity={1.4} /><pointLight position={[3, 4, 4]} intensity={18} color="#b6e8ff" /><pointLight position={[-3, 1, 2]} intensity={10} color="#ff3caf" /><MagicianModel portfolio={portfolio} articleText={articleText} /></Canvas></div>;
}