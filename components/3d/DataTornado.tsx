'use client';

import { useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { shaderMaterial } from '@react-three/drei';
import { extend, type ThreeElement } from '@react-three/fiber';

// ==========================================
// 1. カスタムシェーダーの定義 (GLSL)
// ==========================================
const TornadoMaterial = shaderMaterial(
  {
    uTime: 0,
    uSpeed: 1.0,      // S15のボリューム（出来高）に連動
    uPressure: 0.0,   // S15のデルタ（売り/買い圧力）に連動
    uColor1: new THREE.Color('#ef4444'), // ベースカラー（五行）
    uColor2: new THREE.Color('#eab308'), // 発光カラー
  },
  // Vertex Shader (頂点計算：シリンダー状の回転と乱気流のうねり)
  `
    uniform float uTime;
    uniform float uSpeed;
    uniform float uPressure;
    varying vec2 vUv;
    varying float vElevation;

    // ノイズ関数の簡易モック（乱気流のうねり用）
    float random(vec2 st) {
        return fract(sin(dot(st.xy, vec2(12.9898,78.233))) * 43758.5453123);
    }

    void main() {
      vUv = uv;

      // 元の座標
      vec3 pos = position;

      // 中心からの距離と角度
      float radius = length(pos.xz);
      float angle = atan(pos.z, pos.x);

      // Y軸（高さ）に応じた回転のねじれ ＋ S15スピード
      float twist = pos.y * 0.5;
      angle += uTime * uSpeed + twist;

      // 新しいXZ座標（回転適用）
      pos.x = cos(angle) * radius;
      pos.z = sin(angle) * radius;

      // S15の圧力（デルタ）によるZ/Y軸への強烈な引き伸ばし
      // 売り圧力（マイナス）なら下へ、買い（プラス）なら上へパーティクルが吹き飛ぶ
      float noise = random(pos.xz) * 0.5;
      pos.y += uPressure * uTime * 2.0 + (noise * uPressure);

      // 色のブレンド用に高さをFragmentへ渡す
      vElevation = pos.y;

      vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);

      // カメラに近づくほどパーティクルを大きくする（遠近法）
      gl_PointSize = (10.0 * (1.0 + abs(uPressure))) * (1.0 / -mvPosition.z);
      gl_Position = projectionMatrix * mvPosition;
    }
  `,
  // Fragment Shader (ピクセル描画：円形のパーティクルと色)
  `
    uniform vec3 uColor1;
    uniform vec3 uColor2;
    varying float vElevation;

    void main() {
      // 四角形のパーティクルを円形にくり抜く
      float distanceToCenter = distance(gl_PointCoord, vec2(0.5));
      if (distanceToCenter > 0.5) discard;

      // 中心ほど白く発光するグラデーション
      float strength = 0.05 / distanceToCenter - 0.1;

      // 高さに応じて色をブレンド
      vec3 mixColor = mix(uColor1, uColor2, sin(vElevation * 0.5) * 0.5 + 0.5);

      gl_FragColor = vec4(mixColor * strength, 1.0);
    }
  `
);

declare module '@react-three/fiber' {
  interface ThreeElements {
    tornadoMaterial: ThreeElement<typeof TornadoMaterial>;
  }
}

// R3FのJSXとして使えるように登録
extend({ TornadoMaterial });

// ==========================================
// 2. Reactコンポーネント本体
// ==========================================
interface DataTornadoProps {
  s15Volume: number; // 例: 100 ~ 1000
  s15Delta: number;  // 例: -50.0 ~ 50.0
  wuxingPhase: string;
}

export default function DataTornado({ s15Volume, s15Delta, wuxingPhase }: DataTornadoProps) {
  const materialRef = useRef<any>(null);
  const PARTICLE_COUNT = 30000; // 3万個のデータストリーム

  // パーティクルの初期座標（シリンダー状に配置）を計算
  const positions = useMemo(() => {
    const pos = new Float32Array(PARTICLE_COUNT * 3);
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const i3 = i * 3;
      // 半径2.0〜5.0の円柱状の層を作る
      const radius = 2.0 + Math.random() * 3.0;
      const angle = Math.random() * Math.PI * 2;
      const height = (Math.random() - 0.5) * 20.0; // Y軸方向に-10〜10の高さ

      pos[i3 + 0] = Math.cos(angle) * radius; // x
      pos[i3 + 1] = height;                   // y
      pos[i3 + 2] = Math.sin(angle) * radius; // z
    }
    return pos;
  }, []);

  // 五行に基づくパーティクルカラーの選定
  const colors = useMemo(() => {
    switch (wuxingPhase) {
      case 'WATER': return { c1: '#0891b2', c2: '#06b6d4' };
      case 'FIRE':  return { c1: '#dc2626', c2: '#ef4444' };
      case 'METAL': return { c1: '#9ca3af', c2: '#ffffff' };
      default:      return { c1: '#ca8a04', c2: '#eab308' }; // EARTH
    }
  }, [wuxingPhase]);

  // 毎フレーム（60fps）のシェーダー更新
  useFrame((state, delta) => {
    if (materialRef.current) {
      materialRef.current.uTime += delta;

      // S15のデータをGPU(シェーダー)のuniformへスムーズに渡す（Lerp）
      const targetSpeed = Math.max(0.2, s15Volume / 200.0);
      const targetPressure = s15Delta / 100.0; // マイナスなら下降、プラスなら上昇

      materialRef.current.uSpeed = THREE.MathUtils.lerp(materialRef.current.uSpeed, targetSpeed, 0.05);
      materialRef.current.uPressure = THREE.MathUtils.lerp(materialRef.current.uPressure, targetPressure, 0.05);
    }
  });

  return (
    <points>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[positions, 3]}
          count={PARTICLE_COUNT}
          array={positions}
          itemSize={3}
        />
      </bufferGeometry>
      <tornadoMaterial
        ref={materialRef}
        uColor1={new THREE.Color(colors.c1)}
        uColor2={new THREE.Color(colors.c2)}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending} // パーティクルが重なると白く発光する
      />
    </points>
  );
}