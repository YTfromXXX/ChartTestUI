'use client';

import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';
import { useMemo } from 'react';

type CameraControllerProps = {
  isZooming: boolean;
  focusTarget: THREE.Vector3;
  controls?: React.RefObject<OrbitControlsImpl | null>;
};

export default function CameraController({ isZooming, focusTarget, controls }: CameraControllerProps) {
  const { camera } = useThree();
  const target = useMemo(() => new THREE.Vector3(), []);
  const destination = useMemo(() => new THREE.Vector3(), []);
  const defaultPosition = useMemo(() => new THREE.Vector3(0, 0.8, 7), []);
  const zoomOffset = useMemo(() => new THREE.Vector3(0.15, 0.08, 0.55), []);

  useFrame((_, delta) => {
    const factor = 1 - Math.exp(-delta * (isZooming ? 4.5 : 2.2));
    target.lerp(isZooming ? focusTarget : new THREE.Vector3(0, 0, 0), factor);
    destination.copy(isZooming ? focusTarget : new THREE.Vector3(0, 0, 0));
    destination.add(isZooming ? zoomOffset : defaultPosition);
    camera.position.lerp(destination, factor);

    if (controls?.current) {
      controls.current.enabled = !isZooming;
      controls.current.target.lerp(target, factor);
      controls.current.update();
    } else {
      camera.lookAt(target);
    }
  });

  return null;
}
