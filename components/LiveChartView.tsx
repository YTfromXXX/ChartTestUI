'use client';

import { CandlestickSeries, ColorType, createChart, LineSeries, type IChartApi, type ISeriesApi, type Time } from 'lightweight-charts';
import { useEffect, useRef } from 'react';
import type { MarketData } from '@/hooks/useMarketStream';

type LiveChartViewProps = {
  symbol: string;
  data?: MarketData;
  isConnected: boolean;
};

export default function LiveChartView({ symbol, data, isConnected }: LiveChartViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const lineRef = useRef<ISeriesApi<'Line'> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 460,
      layout: { background: { type: ColorType.Solid, color: '#070b12' }, textColor: '#8c9aaa' },
      grid: { vertLines: { color: '#17212d' }, horzLines: { color: '#17212d' } },
      rightPriceScale: { borderColor: '#263546' },
      timeScale: { borderColor: '#263546', timeVisible: true, secondsVisible: false },
      crosshair: { vertLine: { color: '#46d9f5' }, horzLine: { color: '#46d9f5' } },
    });
    candleRef.current = chart.addSeries(CandlestickSeries, {
      upColor: '#55e6bd', downColor: '#fb6475', borderVisible: false,
      wickUpColor: '#55e6bd', wickDownColor: '#fb6475',
    });
    lineRef.current = chart.addSeries(LineSeries, { color: '#f2c96d', lineWidth: 2, priceLineVisible: false });
    chartRef.current = chart;
    const resize = () => chart.applyOptions({ width: containerRef.current?.clientWidth ?? 720 });
    window.addEventListener('resize', resize);
    return () => { window.removeEventListener('resize', resize); chart.remove(); chartRef.current = null; };
  }, []);

  useEffect(() => {
    const chartData = data?.chart_data;
    if (!chartData || !candleRef.current || !lineRef.current) return;
    candleRef.current.update({ time: chartData.time as Time, open: chartData.open, high: chartData.high, low: chartData.low, close: chartData.close });
    lineRef.current.update({ time: chartData.time as Time, value: chartData.sma20 });
    chartRef.current?.timeScale().fitContent();
  }, [data?.chart_data]);

  return (
    <section className="overflow-hidden border border-cyan-300/20 bg-[#070b12] shadow-[0_0_70px_rgba(34,211,238,0.08)]">
      <div className="flex items-center justify-between border-b border-white/10 px-5 py-4 font-mono text-[10px] uppercase tracking-[0.24em]">
        <span className="text-stone-400">M7 / live market field</span>
        <span className={isConnected ? 'text-emerald-300' : 'text-stone-600'}>{isConnected ? 'connected' : 'awaiting signal'}</span>
      </div>
      <div ref={containerRef} className="h-[460px] w-full" />
      {!data?.chart_data && <div className="border-t border-white/10 px-5 py-3 font-mono text-[10px] uppercase tracking-[0.16em] text-stone-600">Waiting for {symbol} chart data</div>}
    </section>
  );
}