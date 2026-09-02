'use client';

import { ArrowLeft, CircleDot, Radio, Wifi, WifiOff } from 'lucide-react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import LiveChartView from '@/components/LiveChartView';
import { useMarketStream } from '@/hooks/useMarketStream';

export default function LiveSymbolPage() {
  const params = useParams<{ symbol: string }>();
  const symbol = decodeURIComponent(params.symbol ?? '').toUpperCase();
  const { marketDataMap, isConnected, burstEvent, burstId } = useMarketStream(process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:8000/ws/signals', symbol);
  const data = marketDataMap[symbol];

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
          <div className="border-l border-cyan-300/50 bg-white/[0.03] px-4 py-3"><p className="font-mono text-[9px] uppercase tracking-[0.22em] text-stone-600">Arcana</p><p className="mt-1 text-sm text-stone-200">{data?.major_arcana || 'Awaiting signal'}</p></div>
          <div className="border-l border-amber-200/50 bg-white/[0.03] px-4 py-3"><p className="font-mono text-[9px] uppercase tracking-[0.22em] text-stone-600">Wuxing</p><p className="mt-1 text-sm text-amber-100">{data?.wuxing_phase || 'UNKNOWN'}</p></div>
          <div className="border-l border-emerald-300/50 bg-white/[0.03] px-4 py-3"><p className="font-mono text-[9px] uppercase tracking-[0.22em] text-stone-600">Micro pressure</p><p className="mt-1 text-sm text-emerald-200">{data?.tri_layer.micro || 'SCANNING'}</p></div>
          <div className="border-l border-red-300/50 bg-white/[0.03] px-4 py-3"><p className="font-mono text-[9px] uppercase tracking-[0.22em] text-stone-600">Delta</p><p className="mt-1 text-sm text-red-200">{data ? data.s15_delta.toFixed(4) : '--'}</p></div>
        </div>
        <LiveChartView symbol={symbol} data={data} isConnected={isConnected} />
        {burstEvent && <p className="mt-3 font-mono text-[10px] uppercase tracking-[0.2em] text-fuchsia-200">Knot burst detected / elastic threshold exceeded</p>}
        <p className="mt-4 flex items-center gap-2 font-mono text-[9px] uppercase tracking-[0.2em] text-stone-600"><CircleDot className="h-3 w-3" /> Selected symbol stream / five-second refresh</p>
      </div>
    </main>
  );
}