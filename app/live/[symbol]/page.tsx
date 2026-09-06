'use client';

import { ArrowLeft, CircleDot, Radio, Wifi, WifiOff } from 'lucide-react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import LiveChartView from '@/components/LiveChartView';
import { useMarketStream } from '@/hooks/useMarketStream';

const arcanaBySymbol: Record<string, string> = {
  DOGEUSD: '0_THE_FOOL', BTCUSD: '1_THE_MAGICIAN', EURUSD: '2_THE_HIGH_PRIESTESS', XAUUSD: '3_THE_EMPRESS',
  US500: '4_THE_EMPEROR', GBPUSD: '5_THE_HIEROPHANT', ETHUSD: '6_THE_LOVERS', NAS100: '7_THE_CHARIOT',
  US30: '8_STRENGTH', USDJPY: '9_THE_HERMIT', SOLUSD: '10_WHEEL_OF_FORTUNE', AUDUSD: '11_JUSTICE',
  XAGUSD: '12_THE_HANGED_MAN', LTCUSD: '13_DEATH', USDCHF: '14_TEMPERANCE', XRPUSD: '15_THE_DEVIL',
  BTCXAU: '16_THE_TOWER', NZDUSD: '17_THE_STAR', USDCAD: '18_THE_MOON', DAX40: '19_THE_SUN',
  ADAUSD: '20_JUDGEMENT', GER40: '21_THE_WORLD',
};

export default function LiveSymbolPage() {
  const params = useParams<{ symbol: string }>();
  const symbol = decodeURIComponent(params.symbol ?? '').toUpperCase();
  const { marketDataMap, isConnected, burstEvent, burstId } = useMarketStream(process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:8000/ws/signals', symbol);
  const data = marketDataMap[symbol];
  const selectedArcana = data?.major_arcana || arcanaBySymbol[symbol] || 'ARCANA_PENDING';
  const physics = data?.rendered_physics;
  const visuals = data?.visual_triggers;

  return (
    <main className="min-h-screen bg-[#080b10] px-4 py-6 font-display text-stone-100 sm:px-8 lg:px-12">
      <div className="mx-auto max-w-6xl">
        <header className="mb-8 flex flex-col gap-5 border-b border-white/10 pb-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <Link href="/gallery" className="mb-5 inline-flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.25em] text-stone-500 transition-colors hover:text-cyan-200"><ArrowLeft className="h-3 w-3" /> Arcana gallery</Link>
            <div className="flex items-center gap-3"><Radio className="h-4 w-4 text-cyan-300" /><p className="font-mono text-[10px] uppercase tracking-[0.4em] text-stone-500">Live chart access</p></div>
            <h1 className="mt-2 text-4xl font-medium tracking-[-0.04em] text-cyan-100 sm:text-6xl">{symbol || 'UNKNOWN'}</h1>
          </div>
          <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-stone-500">{isConnected ? <Wifi className="h-4 w-4 text-emerald-300" /> : <WifiOff className="h-4 w-4 text-stone-600" />} {isConnected ? 'live transmission' : 'demo relay'}</div>
        </header>

        <div className="mb-5 grid gap-3 sm:grid-cols-4">
          <div className="border-l border-cyan-300/50 bg-white/[0.03] px-4 py-3"><p className="font-mono text-[9px] uppercase tracking-[0.22em] text-stone-600">Selected arcana</p><p className="mt-1 text-sm text-stone-200">{selectedArcana}</p></div>
          <div className="border-l border-amber-200/50 bg-white/[0.03] px-4 py-3"><p className="font-mono text-[9px] uppercase tracking-[0.22em] text-stone-600">Wuxing</p><p className="mt-1 text-sm text-amber-100">{data?.wuxing_phase || 'UNKNOWN'}</p></div>
          <div className="border-l border-emerald-300/50 bg-white/[0.03] px-4 py-3"><p className="font-mono text-[9px] uppercase tracking-[0.22em] text-stone-600">Micro pressure</p><p className="mt-1 text-sm text-emerald-200">{data?.tri_layer.micro || 'SCANNING'}</p></div>
          <div className="border-l border-red-300/50 bg-white/[0.03] px-4 py-3"><p className="font-mono text-[9px] uppercase tracking-[0.22em] text-stone-600">Delta</p><p className="mt-1 text-sm text-red-200">{data ? data.s15_delta.toFixed(4) : '--'}</p></div>
        </div>
        <section className="mb-5 grid gap-3 border border-white/10 bg-white/[0.025] p-4 sm:grid-cols-2 lg:grid-cols-5" aria-label="Live physics telemetry">
          {[
            ['R / thickness', physics?.thickness_r],
            ['T / tension', physics?.tension_t],
            ['C / complexity', physics?.complexity_c],
            ['Tilt', physics?.tornado_tilt_deg],
            ['Gravity', physics?.gravity_g],
          ].map(([label, value]) => <div key={label as string}><p className="font-mono text-[9px] uppercase tracking-[0.18em] text-stone-600">{label}</p><p className="mt-1 font-mono text-sm text-cyan-100">{typeof value === 'number' ? value.toFixed(3) : '--'}</p></div>)}
        </section>
        <LiveChartView symbol={symbol} data={data} isConnected={isConnected} />
        {burstEvent && <p className="mt-3 font-mono text-[10px] uppercase tracking-[0.2em] text-fuchsia-200">Knot burst detected / elastic threshold exceeded</p>}
        <p className="mt-4 flex items-center gap-2 font-mono text-[9px] uppercase tracking-[0.2em] text-stone-600"><CircleDot className="h-3 w-3" /> Selected symbol stream / one-second physics refresh {visuals?.i_ching_hexagram_symbol ? `/ ${visuals.i_ching_hexagram_symbol}` : ''}</p>
      </div>
    </main>
  );
}