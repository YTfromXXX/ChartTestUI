'use client';

import { useEffect, useRef, useState } from 'react';

export interface MarketData {
  symbol: string;
  major_arcana: string;
  minor_arcana?: string;
  wuxing_phase: string;
  hexagram_binary: string;
  tri_layer: {
    macro: string;
    meso: string;
    micro: string;
    hexagram_binary?: string;
  };
  s15_volume: number;
  s15_delta: number;
  is_emperor_synchronized: boolean;
}

type PartialMarketData = Partial<MarketData> & {
  symbol?: string;
  status?: Partial<MarketData['tri_layer']>;
  tri_layer?: Partial<MarketData['tri_layer']>;
  data?: PartialMarketData;
  symbols?: Record<string, PartialMarketData>;
};

function normalizeMarketData(value: PartialMarketData, symbol?: string): MarketData | null {
  const payload = value.data ?? value;
  const resolvedSymbol = payload.symbol ?? symbol;
  if (!resolvedSymbol) return null;

  const triLayer: Partial<MarketData['tri_layer']> = payload.tri_layer ?? {};
  const status = payload.status ?? {};
  const hexagram = payload.hexagram_binary ?? triLayer.hexagram_binary ?? '000000';
  return {
    symbol: resolvedSymbol,
    major_arcana: payload.major_arcana ?? '',
    minor_arcana: payload.minor_arcana,
    wuxing_phase: (payload.wuxing_phase ?? 'EARTH').toUpperCase(),
    hexagram_binary: /^[01]{6}$/.test(hexagram) ? hexagram : '000000',
    tri_layer: {
      macro: triLayer.macro ?? status.macro ?? 'UNKNOWN',
      meso: triLayer.meso ?? status.meso ?? 'UNKNOWN',
      micro: triLayer.micro ?? status.micro ?? 'UNKNOWN',
    },
    s15_volume: payload.s15_volume ?? 0,
    s15_delta: payload.s15_delta ?? 0,
    is_emperor_synchronized: payload.is_emperor_synchronized ?? false,
  };
}

function parsePayload(payload: PartialMarketData): MarketData[] {
  const nested = payload.data ?? payload;
  if (nested.symbols) {
    return Object.entries(nested.symbols)
      .map(([symbol, value]) => normalizeMarketData(value, symbol))
      .filter((value): value is MarketData => value !== null);
  }
  const normalized = normalizeMarketData(nested);
  return normalized ? [normalized] : [];
}

export function useMarketStream(url: string) {
  const [marketDataMap, setMarketDataMap] = useState<Record<string, MarketData>>({});
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const stoppedRef = useRef(false);

  useEffect(() => {
    stoppedRef.current = false;
    let reconnectDelay = 1000;

    const clearReconnect = () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };

    const connect = () => {
      if (stoppedRef.current) return;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        reconnectDelay = 1000;
        setIsConnected(true);
      };
      ws.onmessage = (event) => {
        try {
          const updates = parsePayload(JSON.parse(event.data) as PartialMarketData);
          if (updates.length) {
            setMarketDataMap((previous) => {
              const next = { ...previous };
              updates.forEach((update) => { next[update.symbol] = update; });
              return next;
            });
          }
        } catch (error) {
          console.error('[Market Stream] Parse error:', error);
        }
      };
      ws.onerror = () => ws.close();
      ws.onclose = () => {
        if (wsRef.current === ws) wsRef.current = null;
        setIsConnected(false);
        if (stoppedRef.current) return;
        clearReconnect();
        reconnectTimeoutRef.current = setTimeout(connect, reconnectDelay);
        reconnectDelay = Math.min(reconnectDelay * 2, 10000);
      };
    };

    connect();
    return () => {
      stoppedRef.current = true;
      clearReconnect();
      wsRef.current?.close();
      wsRef.current = null;
      setIsConnected(false);
    };
  }, [url]);

  return { marketDataMap, isConnected };
}
