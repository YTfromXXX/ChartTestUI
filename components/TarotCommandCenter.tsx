"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Activity, Crown, Radio, ShieldAlert, Sparkles, Wifi, WifiOff } from "lucide-react";
import { CandlestickSeries, ColorType, createChart, LineSeries, type IChartApi, type ISeriesApi, type Time } from "lightweight-charts";
import { useEffect, useRef, useState } from "react";

type Phase = "WATER" | "WOOD" | "FIRE" | "EARTH" | "METAL";
type Status = { macro: string; meso: string; micro: string };
type ChartData = { time: number; open: number; high: number; low: number; close: number; sma20: number };
type Signal = { symbol: string; wuxing_phase: Phase; status: Status; minor_arcana?: string; chart_data?: ChartData };

type Archetype = "FOOL" | "TOWER" | "EMPEROR";

const phaseStyle: Record<Phase, { panel: string; border: string; accent: string; label: string }> = {
  WATER: { panel: "from-cyan-950/85 via-slate-950 to-slate-950", border: "border-cyan-400/70", accent: "text-cyan-300", label: "WATER / 水" },
  WOOD: { panel: "from-emerald-950/85 via-slate-950 to-slate-950", border: "border-emerald-400/70", accent: "text-emerald-300", label: "WOOD / 木" },
  FIRE: { panel: "from-red-950/85 via-slate-950 to-slate-950", border: "border-red-400/70", accent: "text-red-300", label: "FIRE / 火" },
  EARTH: { panel: "from-yellow-950/85 via-slate-950 to-slate-950", border: "border-yellow-400/70", accent: "text-yellow-300", label: "EARTH / 土" },
  METAL: { panel: "from-zinc-700/85 via-slate-950 to-slate-950", border: "border-zinc-300/70", accent: "text-zinc-200", label: "METAL / 金" },
};

const demoChart: ChartData = { time: 1724017200, open: 64000, high: 64100, low: 63950, close: 64050, sma20: 63980.5 };
const demoSignal: Signal = {
  symbol: "BTCUSD",
  wuxing_phase: "FIRE",
  status: { macro: "DOWN", meso: "KNOT", micro: "FILLING" },
  chart_data: demoChart,
};

function archetypeFor(status: Status): Archetype {
  if (status.meso === "BREAKOUT" || status.micro === "BREAKOUT") return "TOWER";
  if (status.macro === "DOWN" && status.meso === "KNOT" && status.micro === "FILLING") return "EMPEROR";
  return "FOOL";
}

function normalizeSignal(payload: Record<string, unknown>): Signal | null {
  const nested = (payload.data ?? payload) as Record<string, unknown>;
  const symbols = nested.symbols as Record<string, Record<string, unknown>> | undefined;
  const source = symbols?.BTCUSD ?? nested;
  const status = (source.status ?? source.tri_layer ?? nested.status ?? nested.tri_layer ?? { macro: "UNKNOWN", meso: "UNKNOWN", micro: "NOISE" }) as Partial<Status>;
  const phase = String(source.wuxing_phase ?? nested.wuxing_phase ?? "WATER").toUpperCase() as Phase;
  if (!(phase in phaseStyle)) return null;
  return {
    symbol: String(source.symbol ?? nested.symbol ?? "BTCUSD"),
    wuxing_phase: phase,
    minor_arcana: String(source.minor_arcana ?? nested.minor_arcana ?? ""),
    status: { macro: String(status.macro ?? "UNKNOWN"), meso: String(status.meso ?? "UNKNOWN"), micro: String(status.micro ?? "NOISE") },
    chart_data: (source.chart_data ?? nested.chart_data) as ChartData | undefined,
  };
}

function MarketChart({ chartData }: { chartData?: ChartData }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const lineRef = useRef<ISeriesApi<"Line"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 330,
      layout: { background: { type: ColorType.Solid, color: "#0b1018" }, textColor: "#94a3b8" },
      grid: { vertLines: { color: "#17202c" }, horzLines: { color: "#17202c" } },
      rightPriceScale: { borderColor: "#334155" }, timeScale: { borderColor: "#334155", timeVisible: true },
    });
    const candles = chart.addSeries(CandlestickSeries, { upColor: "#d8b56b", downColor: "#e56b6f", borderVisible: false, wickUpColor: "#d8b56b", wickDownColor: "#e56b6f" });
    const sma = chart.addSeries(LineSeries, { color: "#f4d06f", lineWidth: 2, priceLineVisible: false });
    chartRef.current = chart;
    candleRef.current = candles;
    lineRef.current = sma;
    const resize = () => chart.applyOptions({ width: containerRef.current?.clientWidth ?? 600 });
    window.addEventListener("resize", resize);
    return () => { window.removeEventListener("resize", resize); chart.remove(); chartRef.current = null; };
  }, []);

  useEffect(() => {
    if (!chartData || !candleRef.current || !lineRef.current) return;
    candleRef.current.update({ time: chartData.time as Time, open: chartData.open, high: chartData.high, low: chartData.low, close: chartData.close });
    lineRef.current.update({ time: chartData.time as Time, value: chartData.sma20 });
    chartRef.current?.timeScale().fitContent();
  }, [chartData]);

  return <div ref={containerRef} className="h-[330px] w-full" />;
}

export default function TarotCommandCenter() {
  const [signal, setSignal] = useState<Signal>(demoSignal);
  const [connected, setConnected] = useState(false);
  const [firedAt, setFiredAt] = useState(0);
  const style = phaseStyle[signal.wuxing_phase];
  const archetype = archetypeFor(signal.status);
  const isEmperor = archetype === "EMPEROR";

  useEffect(() => {
    const url = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/signals";
    let socket: WebSocket | null = null;
    let retry: number | undefined;
    let stopped = false;
    const connect = () => {
      socket = new WebSocket(url);
      socket.onopen = () => setConnected(true);
      socket.onmessage = (event) => {
        try { const next = normalizeSignal(JSON.parse(event.data) as Record<string, unknown>); if (next) { setSignal(next); setFiredAt(Date.now()); } } catch { /* ignore malformed packets */ }
      };
      socket.onclose = () => { setConnected(false); if (!stopped) retry = window.setTimeout(connect, 3000); };
      socket.onerror = () => socket?.close();
    };
    connect();
    return () => { stopped = true; if (retry) window.clearTimeout(retry); socket?.close(); };
  }, []);

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#090b0f] px-4 py-6 font-display text-stone-100 sm:px-8 lg:px-12">
      <div className="pointer-events-none absolute inset-0 opacity-40 [background-image:linear-gradient(rgba(255,255,255,.035)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.035)_1px,transparent_1px)] [background-size:48px_48px]" />
      {archetype === "TOWER" && <motion.div className="pointer-events-none fixed inset-0 z-20 border-[14px] border-red-500/80" animate={{ opacity: [0.15, 0.9, 0.15] }} transition={{ duration: 0.65, repeat: Infinity }} />}
      {archetype === "FOOL" && <motion.div className="pointer-events-none fixed inset-0 z-20 opacity-20 mix-blend-screen [background-image:repeating-linear-gradient(0deg,transparent,transparent_3px,#f8fafc_4px)]" animate={{ opacity: [0.03, 0.25, 0.08, 0.18] }} transition={{ duration: 0.45, repeat: Infinity }} />}

      <section className={`relative mx-auto max-w-7xl overflow-hidden rounded-sm border bg-gradient-to-br ${style.panel} ${style.border} shadow-2xl transition-colors duration-1000 ${isEmperor ? "shadow-[0_0_80px_rgba(222,174,74,0.42)]" : ""}`}>
        <motion.div className="absolute inset-0 pointer-events-none" animate={isEmperor ? { opacity: [0.2, 0.7, 0.25], boxShadow: ["inset 0 0 30px rgba(234,179,8,.15)", "inset 0 0 100px rgba(234,179,8,.4)", "inset 0 0 30px rgba(234,179,8,.15)"] } : { opacity: 0.15 }} transition={{ duration: 2.8, repeat: Infinity }} />
        <header className="relative flex items-center justify-between border-b border-white/10 px-5 py-5 sm:px-8">
          <div><p className="font-mono text-[10px] uppercase tracking-[0.4em] text-stone-500">Signal doctrine / 07</p><h1 className="mt-1 text-2xl font-medium tracking-tight sm:text-3xl">TAROT COMMAND CENTER</h1></div>
          <div className="flex items-center gap-3 font-mono text-[10px] uppercase tracking-widest text-stone-400">{connected ? <Wifi className="h-4 w-4 text-emerald-400" /> : <WifiOff className="h-4 w-4 text-stone-600" />} {connected ? "Live feed" : "Demo relay"}</div>
        </header>

        <div className="relative grid gap-8 p-5 sm:p-8 lg:grid-cols-[0.85fr_1.6fr]">
          <aside className="flex min-h-[330px] flex-col justify-between border-l border-white/10 pl-5 sm:pl-7">
            <div><div className="flex items-center gap-2 font-mono text-xs uppercase tracking-[0.3em] text-stone-500"><Activity className="h-4 w-4" /> {signal.symbol}</div><p className={`mt-8 text-5xl font-medium tracking-tight ${style.accent}`}>{style.label}</p><p className="mt-3 max-w-xs font-mono text-xs leading-6 text-stone-400">The live field is reading the current pressure architecture across macro, meso, and micro layers.</p></div>
            <div className="space-y-3 font-mono text-xs uppercase tracking-widest text-stone-400">{Object.entries(signal.status).map(([key, value]) => <div className="flex justify-between border-b border-white/10 pb-2" key={key}><span>{key}</span><span className={value === "DOWN" || value === "FILLING" ? "text-amber-200" : "text-stone-200"}>{value}</span></div>)}</div>
          </aside>

          <div className="min-w-0"><div className="mb-3 flex items-center justify-between"><div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.3em] text-stone-500"><Radio className="h-3 w-3" /> M7 / realtime</div><span className={`font-mono text-[10px] uppercase tracking-widest ${style.accent}`}>{archetype === "EMPEROR" ? "synchronised" : archetype.toLowerCase()}</span></div><div className={`overflow-hidden border bg-black/20 transition-colors duration-1000 ${style.border}`}><MarketChart chartData={signal.chart_data} /></div></div>
        </div>

        <AnimatePresence mode="wait"><motion.div key={archetype} className="relative border-t border-white/10 px-5 py-5 sm:px-8" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.35 }}>
          <div className="flex items-center justify-between gap-4"><div><p className="font-mono text-[10px] uppercase tracking-[0.3em] text-stone-500">Active archetype</p><h2 className={`mt-1 text-2xl font-medium ${archetype === "TOWER" ? "text-red-300" : isEmperor ? "text-amber-200" : "text-stone-100"}`}>{archetype === "FOOL" ? "THE FOOL" : archetype === "TOWER" ? "THE TOWER" : "THE EMPEROR"}</h2></div>{archetype === "TOWER" ? <div className="flex items-center gap-2 font-mono text-xs uppercase tracking-widest text-red-300"><ShieldAlert className="h-4 w-4" /> Warning: knot destroyed</div> : archetype === "FOOL" ? <Sparkles className="h-5 w-5 text-fuchsia-300" /> : <Crown className="h-6 w-6 text-amber-300" />}</div>
          {isEmperor && <motion.button className="absolute bottom-5 right-5 border border-amber-200/70 bg-amber-100 px-5 py-3 font-mono text-xs font-bold tracking-[0.25em] text-stone-950 shadow-[0_0_32px_rgba(250,204,21,0.5)]" animate={{ y: [0, -4, 0], boxShadow: ["0 0 20px rgba(250,204,21,.35)", "0 0 45px rgba(250,204,21,.75)", "0 0 20px rgba(250,204,21,.35)"] }} transition={{ duration: 2.2, repeat: Infinity }}>EXECUTE</motion.button>}
          {archetype === "TOWER" && <motion.p className="mt-2 font-mono text-xs text-red-200/70" animate={{ opacity: [0.45, 1, 0.45] }} transition={{ duration: 0.8, repeat: Infinity }}>BREAKOUT EVENT / RECALIBRATE VECTOR</motion.p>}
        </motion.div></AnimatePresence>
      </section>
      <p className="relative mx-auto mt-4 max-w-7xl text-right font-mono text-[10px] uppercase tracking-[0.25em] text-stone-700">packet {firedAt ? new Date(firedAt).toISOString() : "awaiting transmission"}</p>
    </main>
  );
}
