'use client';

import { motion } from 'framer-motion';

export type ManaElement = 'FIRE' | 'WATER' | 'AIR' | 'EARTH' | 'METAL';
export type ManaPool = Partial<Record<ManaElement, number>>;

type ManaMagicCircleProps = {
  manaPool: ManaPool;
};

const RINGS: Array<{ element: ManaElement; label: string; color: string }> = [
  { element: 'FIRE', label: '火', color: '#fb4b5f' },
  { element: 'WATER', label: '水', color: '#36d9ff' },
  { element: 'AIR', label: '風', color: '#d7f9ff' },
  { element: 'EARTH', label: '地', color: '#e7b84b' },
  { element: 'METAL', label: '金', color: '#b7c4d8' },
];

const VIEWBOX_CENTER = 96;
const RING_GAP = 11;
const RING_RADIUS = 27;
const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS;

export default function ManaMagicCircle({ manaPool }: ManaMagicCircleProps) {
  const totalMana = RINGS.reduce((total, ring) => total + Math.max(0, manaPool[ring.element] ?? 0), 0);

  return (
    <aside className="fixed bottom-8 right-8 z-40 h-56 w-56 text-white" aria-label="Mana pool">
      <div className="absolute inset-0 rounded-full bg-black/40 shadow-[0_0_70px_rgba(57,210,255,0.14)] backdrop-blur-sm" />
      <svg viewBox="0 0 192 192" className="relative h-full w-full overflow-visible">
        <circle cx={VIEWBOX_CENTER} cy={VIEWBOX_CENTER} r="88" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="0.5" strokeDasharray="1 5" />
        {RINGS.map((ring, index) => {
          const mana = Math.max(0, manaPool[ring.element] ?? 0);
          const progress = Math.min(1, mana / 1000);
          const radius = RING_RADIUS + index * RING_GAP;
          const circumference = 2 * Math.PI * radius;
          const speed = Math.max(5, 18 - Math.min(mana, 1000) / 90);

          return (
            <g key={ring.element}>
              <circle cx={VIEWBOX_CENTER} cy={VIEWBOX_CENTER} r={radius} fill="none" stroke={ring.color} strokeOpacity="0.12" strokeWidth="2" />
              <motion.circle
                cx={VIEWBOX_CENTER}
                cy={VIEWBOX_CENTER}
                r={radius}
                fill="none"
                stroke={ring.color}
                strokeWidth="2"
                strokeLinecap="round"
                transform={`rotate(-90 ${VIEWBOX_CENTER} ${VIEWBOX_CENTER})`}
                strokeDasharray={`${circumference} ${circumference}`}
                initial={{ strokeDashoffset: circumference }}
                animate={{ strokeDashoffset: circumference * (1 - progress), opacity: [0.55, 1, 0.55] }}
                transition={{ strokeDashoffset: { duration: 0.8, ease: 'easeOut' }, opacity: { duration: speed, repeat: Infinity, ease: 'easeInOut' } }}
                style={{ filter: `drop-shadow(0 0 ${3 + progress * 10}px ${ring.color})` }}
              />
            </g>
          );
        })}
        <motion.circle
          cx={VIEWBOX_CENTER}
          cy={VIEWBOX_CENTER}
          r="20"
          fill="rgba(3, 7, 18, 0.88)"
          stroke="#d7f9ff"
          strokeWidth="0.7"
          animate={{ rotate: 360 }}
          transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
          style={{ transformOrigin: '96px 96px' }}
        />
      </svg>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center font-mono">
        <span className="text-[9px] uppercase tracking-[0.28em] text-cyan-100/60">Mana pool</span>
        <strong className="mt-1 text-xl font-normal tracking-[0.12em] text-white">{Math.round(totalMana)}</strong>
        <span className="mt-1 text-[8px] tracking-[0.22em] text-white/40">GRIMOIRE / 05</span>
      </div>
      {RINGS.map((ring, index) => {
        const angle = -90 + index * 72;
        const radians = (angle * Math.PI) / 180;
        const radius = 80;
        return (
          <span
            key={ring.element}
            className="absolute -translate-x-1/2 -translate-y-1/2 font-mono text-[9px]"
            style={{ left: `${50 + (Math.cos(radians) * radius) / 2.24}%`, top: `${50 + (Math.sin(radians) * radius) / 2.24}%`, color: ring.color }}
          >
            {ring.label}
          </span>
        );
      })}
    </aside>
  );
}