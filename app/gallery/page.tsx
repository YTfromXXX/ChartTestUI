"use client";

import { motion } from "framer-motion";
import { ArrowLeft, CircleDot, Radio, ScanSearch, Sparkles } from "lucide-react";
import Link from "next/link";
import { useMemo } from "react";
import TarotCard, { type TarotCardProps, type TriLayerStatus, type WuxingPhase } from "@/components/TarotCard";
import { useMarketStream } from "@/hooks/useMarketStream";

type GalleryCard = TarotCardProps & { index: number };

type SignalUpdate = {
  symbol?: string;
  wuxing_phase?: string;
  hexagram_binary?: string;
  tri_layer?: Partial<TriLayerStatus>;
  status?: Partial<TriLayerStatus>;
};

const arcanaCards: Array<Pick<GalleryCard, "index" | "cardName" | "symbol">> = [
  { index: 0, cardName: "0_THE_FOOL", symbol: "DOGEUSD" },
  { index: 1, cardName: "1_THE_MAGICIAN", symbol: "BTCUSD" },
  { index: 2, cardName: "2_THE_HIGH_PRIESTESS", symbol: "EURUSD" },
  { index: 3, cardName: "3_THE_EMPRESS", symbol: "XAUUSD" },
  { index: 4, cardName: "4_THE_EMPEROR", symbol: "US500" },
  { index: 5, cardName: "5_THE_HIEROPHANT", symbol: "GBPUSD" },
  { index: 6, cardName: "6_THE_LOVERS", symbol: "ETHUSD" },
  { index: 7, cardName: "7_THE_CHARIOT", symbol: "NAS100" },
  { index: 8, cardName: "8_STRENGTH", symbol: "US30" },
  { index: 9, cardName: "9_THE_HERMIT", symbol: "USDJPY" },
  { index: 10, cardName: "10_WHEEL_OF_FORTUNE", symbol: "SOLUSD" },
  { index: 11, cardName: "11_JUSTICE", symbol: "AUDUSD" },
  { index: 12, cardName: "12_THE_HANGED_MAN", symbol: "XAGUSD" },
  { index: 13, cardName: "13_DEATH", symbol: "LTCUSD" },
  { index: 14, cardName: "14_TEMPERANCE", symbol: "USDCHF" },
  { index: 15, cardName: "15_THE_DEVIL", symbol: "XRPUSD" },
  { index: 16, cardName: "16_THE_TOWER", symbol: "BTCXAU" },
  { index: 17, cardName: "17_THE_STAR", symbol: "NZDUSD" },
  { index: 18, cardName: "18_THE_MOON", symbol: "USDCAD" },
  { index: 19, cardName: "19_THE_SUN", symbol: "DAX40" },
  { index: 20, cardName: "20_JUDGEMENT", symbol: "ADAUSD" },
  { index: 21, cardName: "21_THE_WORLD", symbol: "GER40" },
];

const phases: WuxingPhase[] = ["FIRE", "WATER", "WOOD", "EARTH", "METAL"];
const macroStates = ["DOWN_CONFIRMED", "UP_CONFIRMED", "NEUTRAL", "TRENDING"];
const mesoStates = ["KNOT_FORMED", "SCANNING", "KNOT", "SCANNING"];
const microStates = ["FILLING", "STABLE", "NOISE", "PRESSURE"];

function demoState(index: number): GalleryCard {
  return {
    ...arcanaCards[index],
    wuxing_phase: phases[index % phases.length],
    hexagramBinary: index.toString(2).padStart(6, "0"),
    tri_layer: {
      macro: macroStates[index % macroStates.length],
      meso: mesoStates[index % mesoStates.length],
      micro: microStates[index % microStates.length],
    },
  };
}

function phaseFrom(value: string | undefined, fallback: WuxingPhase): WuxingPhase {
  const normalized = value?.toUpperCase() as WuxingPhase | undefined;
  return normalized && phases.includes(normalized) ? normalized : fallback;
}

function mergeUpdate(previous: GalleryCard[], update: SignalUpdate): GalleryCard[] {
  if (!update.symbol) return previous;
  return previous.map((card) => {
    if (card.symbol !== update.symbol) return card;
    const incomingStatus = update.tri_layer ?? update.status ?? {};
    const hexagramBinary = update.hexagram_binary ?? (incomingStatus as Partial<SignalUpdate>).hexagram_binary;
    return {
      ...card,
      wuxing_phase: phaseFrom(update.wuxing_phase, card.wuxing_phase),
      hexagramBinary: /^[01]{6}$/.test(hexagramBinary ?? "") ? hexagramBinary : card.hexagramBinary,
      tri_layer: {
        macro: incomingStatus.macro ?? card.tri_layer.macro,
        meso: incomingStatus.meso ?? card.tri_layer.meso,
        micro: incomingStatus.micro ?? card.tri_layer.micro,
      },
    };
  });
}

export default function GalleryPage() {
  const { marketDataMap, isConnected } = useMarketStream(process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/signals");
  const demoCards = useMemo(() => arcanaCards.map((_, index) => demoState(index)), []);
  const cards = useMemo(() => demoCards.map((card) => {
    const live = marketDataMap[card.symbol];
    if (!live) return card;
    return {
      ...card,
      wuxing_phase: phaseFrom(live.wuxing_phase, card.wuxing_phase),
      hexagramBinary: live.hexagram_binary,
      tri_layer: live.tri_layer,
    };
  }), [demoCards, marketDataMap]);

  const activeCount = useMemo(() => cards.filter((card) => card.tri_layer.micro !== "STABLE").length, [cards]);
  const updatedSymbol = Object.keys(marketDataMap).at(-1) ?? null;

  return (
    <main className="relative min-h-screen overflow-hidden bg-gray-950 px-4 py-6 text-stone-100 sm:px-8 lg:px-12">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_18%_8%,rgba(56,189,248,0.12),transparent_30%),radial-gradient(circle_at_82%_70%,rgba(168,85,247,0.1),transparent_28%),linear-gradient(135deg,#030712_0%,#111827_50%,#020617_100%)]" />
      <div className="pointer-events-none fixed inset-0 opacity-30 [background-image:linear-gradient(rgba(255,255,255,.035)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.035)_1px,transparent_1px)] [background-size:64px_64px]" />

      <div className="relative mx-auto max-w-[1800px]">
        <header className="mb-8 flex flex-col gap-6 border-b border-white/10 pb-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <Link href="/" className="mb-5 inline-flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.25em] text-stone-500 transition-colors hover:text-stone-200"><ArrowLeft className="h-3 w-3" /> Command center</Link>
            <div className="flex items-center gap-3"><Sparkles className="h-5 w-5 text-amber-200" /><p className="font-mono text-[10px] uppercase tracking-[0.42em] text-stone-500">The arcana observatory</p></div>
            <h1 className="mt-3 text-4xl font-medium tracking-[-0.04em] text-stone-100 sm:text-6xl">THE TWENTY-TWO</h1>
            <p className="mt-3 max-w-xl font-mono text-xs leading-6 text-stone-500">A living gallery of market archetypes. Each card carries its environment, knot, and micro-pressure as an active field.</p>
          </div>
          <div className="flex items-center gap-5 font-mono text-[10px] uppercase tracking-[0.22em] text-stone-500">
            <span className="flex items-center gap-2"><CircleDot className={`h-3 w-3 ${isConnected ? "text-emerald-300" : "text-stone-600"}`} /> {isConnected ? "live transmission" : "demo constellation"}</span>
            <span className="flex items-center gap-2"><ScanSearch className="h-3 w-3 text-cyan-300" /> {activeCount}/22 active</span>
          </div>
        </header>

        <section aria-label="Major Arcana market gallery" className="grid grid-cols-2 items-start gap-3 sm:gap-5 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6">
          {cards.map((card, index) => (
            <motion.div
              className="relative z-0"
              key={card.symbol}
              initial={{ opacity: 0, y: 26 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.035, duration: 0.5 }}
              whileHover={{ scale: 1.045, zIndex: 30, transition: { duration: 0.2 } }}
            >
              <TarotCard {...card} />
            </motion.div>
          ))}
        </section>

        <footer className="mt-8 flex items-center justify-between border-t border-white/10 pt-4 font-mono text-[9px] uppercase tracking-[0.24em] text-stone-600">
          <span className="flex items-center gap-2"><Radio className="h-3 w-3" /> {updatedSymbol ? `last signal / ${updatedSymbol}` : "awaiting field signal"}</span>
          <span>major arcana / 00—21</span>
        </footer>
      </div>
    </main>
  );
}
