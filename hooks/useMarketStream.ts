'use client';

import { useEffect, useRef, useState } from 'react';
import { useSession } from 'next-auth/react';

export type Vector3Tuple = [number, number, number];
export type OracleBranch = { id: string; probability: number; color?: string };

export interface MarketData {
  symbol: string;
  timestamp?: string;
  major_arcana: string;
  knot_type?: string;
  market_behavior?: string;
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
  rsi_tension?: number;
  tarot_attribute?: { element: string; polarity: string };
  elastic_energy?: number;
  volume_mass?: number;
  physics_event?: 'knot_burst' | 'stable';
  rendered_physics?: {
    thickness_r: number;
    tension_t: number;
    complexity_c: number;
    tornado_tilt_deg: number;
    gravity_g: number;
  };
  visual_triggers?: {
    knot_model: string;
    background_hex: string;
    trigger_firework: boolean;
    i_ching_hexagram_symbol: string;
  };
  chart_data?: {
    time: number;
    open: number;
    high: number;
    low: number;
    close: number;
    sma20: number;
  };
  coordinate?: Vector3Tuple;
  curvature?: number;
  torsion?: number;
  oracle_branches: OracleBranch[];
}

type PartialMarketData = Partial<MarketData> & {
  symbol?: string;
  event?: 'knot_burst' | 'stable';
  status?: Partial<MarketData['tri_layer']>;
  tri_layer?: Partial<MarketData['tri_layer']>;
  data?: PartialMarketData;
  symbols?: Record<string, PartialMarketData>;
  rendered_physics?: MarketData['rendered_physics'];
  visual_triggers?: MarketData['visual_triggers'];
  oracle_prediction?: {
    topology?: { kappa?: number; tau?: number };
    branches?: Array<{ id?: string; prob?: number; probability?: number; color_hex?: string; color?: string }>;
  };
  coordinates?: unknown;
  coordinate?: unknown;
  position?: unknown;
  latest_3d_coordinate?: unknown;
  curvature?: number;
  kappa?: number;
  torsion?: number;
  tau?: number;
};

function parseCoordinate(value: unknown): Vector3Tuple | undefined {
  if (Array.isArray(value) && value.length >= 3 && value.every((item) => typeof item === 'number' && Number.isFinite(item))) {
    return [value[0], value[1], value[2]];
  }
  if (value && typeof value === 'object') {
    const point = value as { x?: unknown; y?: unknown; z?: unknown };
    if ([point.x, point.y, point.z].every((item) => typeof item === 'number' && Number.isFinite(item))) {
      return [point.x as number, point.y as number, point.z as number];
    }
  }
  return undefined;
}

function normalizeMarketData(value: PartialMarketData, symbol?: string): MarketData | null {
  const payload = value.data ?? value;
  const resolvedSymbol = payload.symbol ?? symbol;
  if (!resolvedSymbol) return null;

  const triLayer: Partial<MarketData['tri_layer']> = payload.tri_layer ?? {};
  const status = payload.status ?? {};
  const hexagram = payload.hexagram_binary ?? triLayer.hexagram_binary ?? '000000';
  const oracle = payload.oracle_prediction ?? {};
  const topology = oracle.topology ?? {};
  const branches = (oracle.branches ?? []).map((branch, index) => ({
    id: branch.id ?? `branch-${index + 1}`,
    probability: Number(branch.probability ?? branch.prob ?? 0),
    color: branch.color ?? branch.color_hex,
  }));
  return {
    symbol: resolvedSymbol,
    timestamp: payload.timestamp,
    major_arcana: payload.major_arcana ?? '',
    knot_type: payload.knot_type,
    market_behavior: payload.market_behavior,
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
    rsi_tension: payload.rsi_tension,
    tarot_attribute: payload.tarot_attribute,
    elastic_energy: payload.elastic_energy,
    volume_mass: payload.volume_mass,
    physics_event: payload.event === 'knot_burst' || payload.event === 'stable' ? payload.event : undefined,
    rendered_physics: payload.rendered_physics,
    visual_triggers: payload.visual_triggers,
    chart_data: payload.chart_data,
    coordinate: parseCoordinate(payload.coordinate ?? payload.coordinates ?? payload.position ?? payload.latest_3d_coordinate),
    curvature: Number(payload.curvature ?? payload.kappa ?? topology.kappa ?? 0),
    torsion: Number(payload.torsion ?? payload.tau ?? topology.tau ?? 0),
    oracle_branches: branches,
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

export function useMarketStream(url: string, symbol?: string) {
  const { data: session } = useSession();
  const [marketDataMap, setMarketDataMap] = useState<Record<string, MarketData>>({});
  const [coordinateHistoryMap, setCoordinateHistoryMap] = useState<Record<string, Vector3Tuple[]>>({});
  const [isConnected, setIsConnected] = useState(false);
  const [burstEvent, setBurstEvent] = useState(false);
  const [burstId, setBurstId] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const stoppedRef = useRef(false);

  useEffect(() => {
    stoppedRef.current = false;
    let reconnectDelay = 1000;
    let burstResetTimeout: ReturnType<typeof setTimeout> | null = null;
    let fireworkWasActive = false;

    const clearReconnect = () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };

    const connect = () => {
      if (stoppedRef.current) return;
      const streamUrl = symbol
        ? `${url.replace(/\/ws\/(signals|live\/[^/]+|oracle\/v1\/stream\/[^/]+)\/?$/, '')}/ws/oracle/v1/stream/${encodeURIComponent(symbol.toUpperCase())}`
        : url;
      const ws = new WebSocket(streamUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        reconnectDelay = 1000;
        setIsConnected(true);
        if (symbol) {
          ws.send(JSON.stringify({
            action: 'subscribe',
            symbol: symbol.toUpperCase(),
            is_authenticated: Boolean(session),
          }));
        }
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
            setCoordinateHistoryMap((previous) => {
              const next = { ...previous };
              updates.forEach((update) => {
                if (!update.coordinate) return;
                next[update.symbol] = [...(previous[update.symbol] ?? []), update.coordinate].slice(-32);
              });
              return next;
            });
            const fireworkTriggered = updates.some((update) => {
              const active = update.visual_triggers?.trigger_firework === true;
              const risingEdge = active && !fireworkWasActive;
              fireworkWasActive = active;
              return risingEdge;
            });
            if (fireworkTriggered || updates.some((update) => update.physics_event === 'knot_burst')) {
              setBurstId((current) => current + 1);
              setBurstEvent(true);
              if (burstResetTimeout) clearTimeout(burstResetTimeout);
              burstResetTimeout = setTimeout(() => setBurstEvent(false), 140);
            }
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
      if (burstResetTimeout) clearTimeout(burstResetTimeout);
      wsRef.current?.close();
      wsRef.current = null;
      setIsConnected(false);
    };
  }, [url, symbol, session]);

  return { marketDataMap, coordinateHistoryMap, isConnected, burstEvent, burstId };
}
