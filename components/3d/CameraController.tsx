'use client';

import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';
import { useMemo } from 'react';

type CameraControllerProps = {
  isZooming: boolean;
  isGraphMode?: boolean;
  focusTarget: THREE.Vector3;
  controls?: React.RefObject<OrbitControlsImpl | null>;
};

export default function CameraController({ isZooming, isGraphMode = true, focusTarget, controls }: CameraControllerProps) {
  const { camera, scene } = useThree();
  const target = useMemo(() => new THREE.Vector3(), []);
  const destination = useMemo(() => new THREE.Vector3(), []);
  const zoomOffset = useMemo(() => new THREE.Vector3(0.15, 0.08, 0.55), []);
  const cinematicOffset = useMemo(() => new THREE.Vector3(0, -0.7, 4.8), []);

  useFrame((_, delta) => {
    const cinematicMode = !isGraphMode;
    if (scene.fog instanceof THREE.FogExp2) scene.fog.density = cinematicMode ? 0.035 : 0;
    if (controls?.current) {
      controls.current.enabled = isGraphMode && !isZooming;
    }

    if (isGraphMode) {
      controls?.current?.update();
      return;
    }

    const factor = 1 - Math.exp(-delta * (isZooming ? 4.5 : 2.2));
    target.lerp(focusTarget, factor);
    destination.copy(focusTarget);
    destination.add(isZooming ? zoomOffset : cinematicOffset);
    camera.position.lerp(destination, factor);

    if (controls?.current) {
      controls.current.target.lerp(target, factor);
      controls.current.update();
    } else {
      camera.lookAt(target);
    }
  });

  return null;
}
