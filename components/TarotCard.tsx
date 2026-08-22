"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Activity, Gem, Orbit, Shield } from "lucide-react";
import IChingHexagram from "@/components/IChingHexagram";

export type WuxingPhase = "WATER" | "WOOD" | "FIRE" | "EARTH" | "METAL";

export type TriLayerStatus = {
  macro: string;
  meso: string;
  micro: string;
};

export type TarotCardProps = {
  symbol: string;
  cardName: string;
  wuxing_phase: WuxingPhase;
  tri_layer: TriLayerStatus;
  hexagramBinary?: string;
};

type PhaseTheme = {
  accent: string;
  border: string;
  glow: string;
  halo: string;
  badge: string;
};

const phaseThemes: Record<WuxingPhase, PhaseTheme> = {
  WATER: {
    accent: "text-cyan-200",
    border: "border-cyan-300/40 hover:border-cyan-200/80",
    glow: "rgba(34, 211, 238, 0.34)",
    halo: "bg-cyan-400/20",
    badge: "bg-cyan-300/10 text-cyan-200",
  },
  WOOD: {
    accent: "text-emerald-200",
    border: "border-emerald-300/40 hover:border-emerald-200/80",
    glow: "rgba(52, 211, 153, 0.32)",
    halo: "bg-emerald-400/20",
    badge: "bg-emerald-300/10 text-emerald-200",
  },
  FIRE: {
    accent: "text-red-200",
    border: "border-red-300/45 hover:border-red-200/85",
    glow: "rgba(248, 113, 113, 0.38)",
    halo: "bg-red-400/20",
    badge: "bg-red-300/10 text-red-200",
  },
  EARTH: {
    accent: "text-yellow-200",
    border: "border-yellow-300/40 hover:border-yellow-200/80",
    glow: "rgba(250, 204, 21, 0.32)",
    halo: "bg-yellow-400/20",
    badge: "bg-yellow-300/10 text-yellow-200",
  },
  METAL: {
    accent: "text-zinc-100",
    border: "border-zinc-200/45 hover:border-white/85",
    glow: "rgba(226, 232, 240, 0.34)",
    halo: "bg-zinc-200/20",
    badge: "bg-zinc-200/10 text-zinc-100",
  },
};

const strongMacroStates = new Set(["DOWN_CONFIRMED", "UP_CONFIRMED", "BREAKOUT", "TRENDING"]);
const knotStates = new Set(["KNOT", "KNOT_FORMED", "FORMED"]);
const activeMicroStates = new Set(["FILLING", "NOISE", "PRESSURE", "DISTORTION"]);

function statusTone(status: string) {
  return strongMacroStates.has(status) ? "text-amber-100" : "text-stone-300";
}

function glowWithOpacity(glow: string, opacity: number) {
  return glow.replace(/[^,]+\)$/u, `${opacity})`);
}

function Silhouette({ theme, knotFormed, microActive }: { theme: PhaseTheme; knotFormed: boolean; microActive: boolean }) {
  return (
    <div className="relative flex h-52 items-center justify-center overflow-hidden rounded-sm border border-white/10 bg-black/20">
      <motion.div
        className={`absolute h-44 w-44 rounded-full blur-3xl ${theme.halo}`}
        animate={{ scale: microActive ? [0.8, 1.1, 0.85] : 1, opacity: microActive ? [0.18, 0.4, 0.2] : 0.2 }}
        transition={{ duration: 2.1, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="relative h-36 w-24"
        animate={microActive ? { y: [0, -3, 2, 0], rotate: [0, 1, -1, 0] } : { y: 0, rotate: 0 }}
        transition={{ duration: 1.6, repeat: microActive ? Infinity : 0, ease: "easeInOut" }}
      >
        <div className="absolute left-1/2 top-0 h-12 w-12 -translate-x-1/2 rounded-full bg-black/80 shadow-[0_0_25px_rgba(0,0,0,0.5)]" />
        <div className="absolute left-1/2 top-10 h-20 w-16 -translate-x-1/2 rounded-[45%_45%_24%_24%] bg-black/80" />
        <div className="absolute left-1/2 top-[4.6rem] h-20 w-28 -translate-x-1/2 bg-black/80 [clip-path:polygon(38%_0,62%_0,100%_100%,58%_84%,50%_100%,42%_84%,0_100%)]" />
        <motion.div className="absolute left-1/2 top-[4.5rem] h-1 w-14 -translate-x-1/2 rounded-full bg-white/20" animate={microActive ? { opacity: [0.1, 0.7, 0.1] } : { opacity: 0.2 }} transition={{ duration: 0.8, repeat: Infinity }} />
      </motion.div>
      <AnimatePresence>
        {knotFormed && (
          <motion.div
            className={`absolute left-1/2 top-[43%] z-10 -translate-x-1/2 -translate-y-1/2 ${theme.accent}`}
            initial={{ scale: 0, rotate: -45, opacity: 0 }}
            animate={{ scale: [0, 1.3, 1], rotate: [ -45, 8, 0 ], opacity: 1 }}
            exit={{ scale: 0, opacity: 0, rotate: 45 }}
            transition={{ duration: 0.48, type: "spring", stiffness: 500, damping: 18 }}
          >
            <div className="relative flex h-10 w-10 rotate-45 items-center justify-center border border-current bg-black/70 shadow-[0_0_24px_currentColor]">
              <Gem className="h-5 w-5 -rotate-45" strokeWidth={1.5} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function EnergyParticles({ color }: { color: string }) {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {[0, 1, 2, 3, 4].map((particle) => (
        <motion.span
          className="absolute h-1 w-1 rounded-full bg-current shadow-[0_0_10px_currentColor]"
          style={{ color, left: `${18 + particle * 16}%`, bottom: "18%" }}
          key={particle}
          animate={{ y: [-4, -92 - particle * 8], opacity: [0, 0.9, 0] }}
          transition={{ duration: 1.6 + particle * 0.18, delay: particle * 0.22, repeat: Infinity, ease: "easeOut" }}
        />
      ))}
    </div>
  );
}

export default function TarotCard({ symbol, cardName, wuxing_phase, tri_layer, hexagramBinary = "000000" }: TarotCardProps) {
  const theme = phaseThemes[wuxing_phase];
  const macroStrong = strongMacroStates.has(tri_layer.macro);
  const knotFormed = knotStates.has(tri_layer.meso);
  const microActive = activeMicroStates.has(tri_layer.micro);
  const glowOpacity = macroStrong ? 0.58 : 0.3;

  return (
    <motion.article
      className={`group relative isolate overflow-hidden rounded-xl border bg-white/[0.07] p-4 backdrop-blur-xl transition-colors duration-700 ${theme.border}`}
      style={{ boxShadow: `0 0 32px ${glowWithOpacity(theme.glow, glowOpacity)}` }}
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -6, transition: { duration: 0.22 } }}
      transition={{ duration: 0.45 }}
    >
      <motion.div
        className="pointer-events-none absolute inset-0 rounded-xl"
        animate={{ boxShadow: macroStrong ? [`inset 0 0 18px ${glowWithOpacity(theme.glow, 0.35)}`, `inset 0 0 46px ${glowWithOpacity(theme.glow, 0.75)}`, `inset 0 0 18px ${glowWithOpacity(theme.glow, 0.35)}`] : `inset 0 0 20px ${theme.glow}` }}
        transition={{ duration: 2.4, repeat: macroStrong ? Infinity : 0, ease: "easeInOut" }}
      />
      {microActive && <EnergyParticles color={theme.glow} />}

      <div className="absolute right-3 top-3 z-20">
        <IChingHexagram binaryString={hexagramBinary} wuxingPhase={wuxing_phase} />
        <p className="mt-1 text-center font-mono text-[8px] tracking-[0.18em] text-white/40">{/^[01]{6}$/.test(hexagramBinary) ? hexagramBinary : "000000"}</p>
      </div>

      <header className="relative flex items-start justify-between gap-3 border-b border-white/10 pb-3">
        <div className="min-w-0">
          <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-stone-500">Major arcana</p>
          <h2 className="mt-1 truncate text-lg font-medium tracking-tight text-stone-100">{cardName}</h2>
        </div>
        <span className={`shrink-0 rounded-full px-2 py-1 font-mono text-[9px] tracking-[0.18em] ${theme.badge}`}>{wuxing_phase}</span>
      </header>

      <div className="relative py-3">
        <Silhouette theme={theme} knotFormed={knotFormed} microActive={microActive} />
        {microActive && <motion.div className={`absolute inset-x-3 bottom-2 h-px ${theme.accent} bg-current`} animate={{ opacity: [0.15, 0.8, 0.15], scaleX: [0.65, 1, 0.7] }} transition={{ duration: 0.9, repeat: Infinity }} />}
      </div>

      <footer className="relative space-y-3">
        <div className="flex items-center justify-between"><span className="font-mono text-xs tracking-[0.14em] text-stone-300">{symbol}</span><Orbit className={`h-4 w-4 ${theme.accent}`} /></div>
        <div className="grid grid-cols-3 gap-2 font-mono text-[9px] uppercase tracking-wider">
          <div className="border-l border-white/15 pl-2"><span className="block text-stone-600">Macro</span><span className={statusTone(tri_layer.macro)}>{tri_layer.macro}</span></div>
          <div className="border-l border-white/15 pl-2"><span className="block text-stone-600">Meso</span><span className={knotFormed ? theme.accent : "text-stone-300"}>{tri_layer.meso}</span></div>
          <div className="border-l border-white/15 pl-2"><span className="block text-stone-600">Micro</span><span className={microActive ? theme.accent : "text-stone-300"}>{tri_layer.micro}</span></div>
        </div>
        <div className="flex items-center gap-2 border-t border-white/10 pt-3 font-mono text-[9px] uppercase tracking-[0.2em] text-stone-500"><Activity className="h-3 w-3" /> {knotFormed ? "knot equipped" : "field scanning"}{macroStrong && <Shield className="ml-auto h-3 w-3 text-amber-200" />}</div>
      </footer>
    </motion.article>
  );
}
