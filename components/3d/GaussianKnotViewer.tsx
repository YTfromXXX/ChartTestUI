"use client";

import { OrbitControls, Points, PointMaterial } from "@react-three/drei";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";

export type GaussianKnotViewerProps = {
  macroDensity: number;
  mesoDepthCenter: THREE.Vector3;
  microAreaScale: number;
  focusTarget: THREE.Vector3;
  isZooming: boolean;
  className?: string;
};

type KnotFieldProps = Omit<GaussianKnotViewerProps, "className">;

const PARTICLE_COUNT = 30000;
const INITIAL_CAMERA = new THREE.Vector3(0, 1.2, 15);
const UP = new THREE.Vector3(0, 1, 0);

function createGaussianField(count: number) {
  const positions = new Float32Array(count * 3);
  const colors = new Float32Array(count * 3);
  const color = new THREE.Color();

  for (let index = 0; index < count; index += 1) {
    const offset = index * 3;
    const radius = Math.pow(Math.random(), 0.55) * 5.4;
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    const turbulence = Math.sin(theta * 5 + radius * 1.7) * 0.22;

    positions[offset] = Math.sin(phi) * Math.cos(theta) * (radius + turbulence);
    positions[offset + 1] = Math.cos(phi) * (radius + turbulence) * 0.72;
    positions[offset + 2] = Math.sin(phi) * Math.sin(theta) * (radius + turbulence);

    const heat = Math.random();
    color.setHSL(0.52 + heat * 0.12, 0.75, 0.52 + heat * 0.2);
    colors[offset] = color.r;
    colors[offset + 1] = color.g;
    colors[offset + 2] = color.b;
  }

  return { positions, colors };
}

function KnotField({ macroDensity, mesoDepthCenter, microAreaScale, focusTarget, isZooming }: KnotFieldProps) {
  const pointsRef = useRef<THREE.Points>(null);
  const materialRef = useRef<THREE.PointsMaterial>(null);
  const controlsRef = useRef<OrbitControlsImpl>(null);
  const { camera } = useThree();
  const field = useMemo(() => createGaussianField(PARTICLE_COUNT), []);
  const smoothCenter = useRef(new THREE.Vector3());
  const desiredCamera = useMemo(() => new THREE.Vector3(), []);
  const desiredTarget = useMemo(() => new THREE.Vector3(), []);
  const cameraOffset = useMemo(() => new THREE.Vector3(0.4, 0.25, 2.1), []);

  useFrame((state, delta) => {
    if (!pointsRef.current || !materialRef.current) return;
    const elapsed = state.clock.getElapsedTime();
    const density = THREE.MathUtils.clamp(macroDensity, 0, 1);
    const areaScale = THREE.MathUtils.clamp(microAreaScale, 0.25, 4);

    smoothCenter.current.lerp(mesoDepthCenter, 1 - Math.exp(-delta * 4));
    pointsRef.current.position.copy(smoothCenter.current);
    pointsRef.current.rotation.y += delta * (0.055 + density * 0.12);
    pointsRef.current.rotation.z = Math.sin(elapsed * 0.18) * 0.08;
    pointsRef.current.scale.setScalar(0.92 + density * 0.18);

    materialRef.current.opacity = THREE.MathUtils.lerp(materialRef.current.opacity, 0.12 + density * 0.72, 1 - Math.exp(-delta * 6));
    materialRef.current.size = THREE.MathUtils.lerp(materialRef.current.size, (0.018 + density * 0.025) * areaScale, 1 - Math.exp(-delta * 7));

    if (isZooming) {
      desiredTarget.copy(focusTarget);
      desiredCamera.copy(focusTarget).add(cameraOffset);
      camera.position.lerp(desiredCamera, 1 - Math.exp(-delta * 3.2));
    } else {
      desiredTarget.copy(mesoDepthCenter);
      desiredCamera.copy(INITIAL_CAMERA).add(mesoDepthCenter);
      camera.position.lerp(desiredCamera, 1 - Math.exp(-delta * 1.8));
    }

    if (controlsRef.current) {
      controlsRef.current.target.lerp(desiredTarget, 1 - Math.exp(-delta * (isZooming ? 4.5 : 2.2)));
      controlsRef.current.update();
    } else {
      camera.lookAt(desiredTarget);
    }
  });

  return (
    <>
      <Points ref={pointsRef} positions={field.positions} colors={field.colors} frustumCulled={false}>
        <PointMaterial
          ref={materialRef}
          vertexColors
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
          size={0.03}
          sizeAttenuation
        />
      </Points>
      <OrbitControls ref={controlsRef} enableDamping dampingFactor={0.08} minDistance={0.45} maxDistance={28} />
    </>
  );
}

export default function GaussianKnotViewer(props: GaussianKnotViewerProps) {
  return (
    <div className={props.className ?? "h-[560px] w-full overflow-hidden rounded-xl bg-slate-950"}>
      <Canvas
        camera={{ position: [0, 1.2, 15], fov: 48, near: 0.01, far: 100 }}
        dpr={[1, 2]}
        gl={{ antialias: true, alpha: true }}
      >
        <color attach="background" args={["#030712"]} />
        <fog attach="fog" args={["#030712", 8, 32]} />
        <ambientLight intensity={0.25} />
        <KnotField {...props} />
      </Canvas>
    </div>
  );
}
