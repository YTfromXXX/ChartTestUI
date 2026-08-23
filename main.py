"""FastAPI entry point for the real-time MT5 signal stream."""

from __future__ import annotations

import asyncio
import logging
import os
import threading
import time
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from tarot_engine import (
    MAJOR_ARCANA_SYMBOLS,
    WATCHLIST_SYMBOLS,
    calculate_iching_weight,
    calculate_minor_arcana,
    calculate_iching_weight,
    evaluate_micro_distortion,
    evaluate_court_card,
)

try:
    import MetaTrader5 as mt5
except ImportError:  # Keep application imports usable in environments without MT5.
    mt5 = None  # type: ignore[assignment]

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ChartTestUI API")


def _cors_origins() -> list[str]:
    """Parse allowed browser origins from a comma-separated environment variable."""
    configured = os.getenv("BACKEND_CORS_ORIGINS", "*")
    return [origin.strip() for origin in configured.split(",") if origin.strip()] or ["*"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
MT5_SYMBOLS = tuple(WATCHLIST_SYMBOLS)
M7_BARS_REQUIRED = 100
M1_BARS_FOR_M7 = 750
SQUEEZE_WIDTH_RATIO = 0.01
MONITOR_CACHE_SECONDS = 5.0
MONITOR_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
MONITOR_CACHE_LOCK = threading.Lock()
COINGECKO_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
COINGECKO_CACHE_LOCK = threading.Lock()


def _mt5_login_settings() -> tuple[int | None, str, str]:
    """Read and validate MT5 credentials from the environment."""
    login_value = os.getenv("MT5_LOGIN", "").strip()
    password = os.getenv("MT5_PASSWORD", "").strip()
    server = os.getenv("MT5_SERVER", "").strip()

    if not login_value:
        return None, password, server

    try:
        return int(login_value), password, server
    except ValueError:
        logger.error("MT5_LOGIN must be a numeric account number.")
        return None, password, server


@app.on_event("startup")
def startup_mt5() -> None:
    """Initialize the MT5 terminal using credentials from the environment."""
    if mt5 is None:
        logger.error("MetaTrader5 package is not installed; MT5 connection unavailable.")
        return

    login, password, server = _mt5_login_settings()
    if login is None or not password or not server:
        logger.error("MT5 credentials are incomplete; set MT5_LOGIN, MT5_PASSWORD, and MT5_SERVER.")
        return

    try:
        initialized = mt5.initialize(login=login, password=password, server=server)
    except Exception:
        logger.exception("MT5 initialization raised an exception.")
        return

    if not initialized:
        logger.error("MT5 connection failed: %s", mt5.last_error())
        return

    logger.info("MT5 terminal initialized for account %s on server %s.", login, server)


@app.on_event("shutdown")
def shutdown_mt5() -> None:
    """Release the MT5 terminal connection when the application stops."""
    if mt5 is not None:
        try:
            mt5.shutdown()
        except Exception:
            logger.exception("MT5 shutdown raised an exception.")


def calculate_wuxing_phase(df_m7: pd.DataFrame) -> str | None:
    """Classify the latest M7 close into a Wu Xing Bollinger phase."""
    required_columns = {"close"}
    if not required_columns.issubset(df_m7.columns) or len(df_m7) < 20:
        return None

    close = pd.to_numeric(df_m7["close"], errors="coerce")
    sma20 = close.rolling(window=20).mean()
    std20 = close.rolling(window=20).std()
    latest = pd.DataFrame(
        {
            "close": close,
            "sma20": sma20,
            "upper1": sma20 + std20,
            "lower1": sma20 - std20,
            "upper2": sma20 + (2 * std20),
            "lower2": sma20 - (2 * std20),
            "upper3": sma20 + (3 * std20),
        }
    ).dropna().iloc[-1]

    current_close = float(latest["close"])
    sma_value = float(latest["sma20"])
    std_value = float(std20.dropna().iloc[-1])
    upper1 = float(latest["upper1"])
    lower1 = float(latest["lower1"])

    if std_value == 0 and current_close == sma_value:
        return "WATER"
    if current_close >= float(latest["upper3"]):
        return "FIRE"
    if current_close > float(latest["upper2"]):
        return "WOOD"
    if current_close < float(latest["lower2"]):
        return "METAL"

    band_width = upper1 - lower1
    is_squeeze = abs(sma_value) > 0 and band_width / abs(sma_value) <= SQUEEZE_WIDTH_RATIO
    if lower1 <= current_close <= upper1 and is_squeeze:
        return "WATER"
    if lower1 <= current_close <= upper1:
        return "EARTH"

    # A close between the inner and outer bands is not a named phase in the definition.
    return "EARTH" if current_close < sma_value else "WOOD"


def _fetch_wuxing_phase(symbol: str) -> str | None:
    """Fetch recent M7 rates and calculate the latest Wu Xing phase."""
    frame = _fetch_m7_frame(symbol)
    return calculate_wuxing_phase(frame) if frame is not None else None


def _fetch_m7_chart_data(symbol: str) -> dict[str, Any] | None:
    """Return the latest M7 candle and SMA20 for chart rendering."""
    return _chart_data_from_frame(_fetch_m7_frame(symbol))


def _chart_data_from_frame(frame: pd.DataFrame | None) -> dict[str, Any] | None:
    """Convert an already fetched M7 frame into the frontend chart payload."""
    if frame is None or len(frame) < 20:
        return None
    frame = frame.copy()
    frame["sma20"] = pd.to_numeric(frame["close"], errors="coerce").rolling(20).mean()
    latest = frame.dropna(subset=["sma20"]).iloc[-1]
    return {
        "time": int(latest.name.timestamp()),
        "open": float(latest["open"]),
        "high": float(latest["high"]),
        "low": float(latest["low"]),
        "close": float(latest["close"]),
        "sma20": float(latest["sma20"]),
    }


def _fetch_m7_frame(symbol: str) -> pd.DataFrame | None:
    """Aggregate standard MT5 M1 rates into seven-minute OHLC bars."""
    if mt5 is None or not hasattr(mt5, "copy_rates_from_pos") or not hasattr(mt5, "TIMEFRAME_M1"):
        return None
    try:
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, M1_BARS_FOR_M7)
        if rates is None or len(rates) == 0:
            logger.warning("No M1 rate data returned for %s.", symbol)
            return None
        frame = pd.DataFrame(rates)
        frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
        frame = frame.set_index("time")
        return frame.resample("7min", origin="epoch").agg(
            open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"),
            tick_volume=("tick_volume", "sum"),
        ).dropna(subset=["open", "high", "low", "close"]).tail(M7_BARS_REQUIRED)
    except Exception:
        logger.exception("Failed to aggregate M1 data into M7 bars for %s.", symbol)
        return None


def _fetch_s15_frame(symbol: str) -> pd.DataFrame | None:
    """Aggregate recent MT5 ticks into 15-second OHLCV bars."""
    if mt5 is None or not hasattr(mt5, "copy_ticks_from_pos"):
        return None
    try:
        flags = getattr(mt5, "COPY_TICKS_ALL", 0)
        ticks = mt5.copy_ticks_from_pos(symbol, 0, 600, flags)
        if ticks is None or len(ticks) == 0:
            return None
        frame = pd.DataFrame(ticks)
        price_column = "last" if "last" in frame.columns else "bid"
        if price_column not in frame.columns or "time" not in frame.columns:
            return None
        frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
        frame["price"] = pd.to_numeric(frame[price_column], errors="coerce")
        frame["volume"] = pd.to_numeric(frame.get("volume", 0), errors="coerce").fillna(0)
        return frame.dropna(subset=["time", "price"]).set_index("time").resample("15s").agg(
            open=("price", "first"), high=("price", "max"), low=("price", "min"),
            close=("price", "last"), volume=("volume", "sum"),
        ).dropna(subset=["open", "high", "low", "close"])
    except Exception:
        logger.exception("Failed to aggregate S15 ticks for %s.", symbol)
        return None


def _coingecko_symbol(symbol: str) -> str | None:
    """Map supported terminal symbols to CoinGecko coin IDs."""
    return {"BTCUSD": "bitcoin", "BTCXAU": "bitcoin"}.get(symbol)


def _fetch_coingecko_signal(symbol: str) -> dict[str, Any] | None:
    """Build a synthetic M7 candle from cached CoinGecko price history."""
    coin_id = _coingecko_symbol(symbol)
    if coin_id is None:
        return None

    try:
        cache_seconds = max(float(os.getenv("COINGECKO_CACHE_SECONDS", "20")), 1.0)
    except ValueError:
        cache_seconds = 20.0

    now = time.monotonic()
    with COINGECKO_CACHE_LOCK:
        cached = COINGECKO_CACHE.get(symbol)
        if cached and now - cached[0] < cache_seconds:
            return cached[1]

    response = requests.get(
        f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart",
        params={"vs_currency": "usd", "days": "1"},
        timeout=8,
    )
    response.raise_for_status()
    prices = response.json().get("prices", [])
    if len(prices) < 20:
        logger.warning("CoinGecko returned insufficient price history for %s.", symbol)
        return None

    price_frame = pd.DataFrame(prices, columns=["time", "close"])
    price_frame["time"] = pd.to_datetime(price_frame["time"], unit="ms", utc=True)
    price_frame = price_frame.set_index("time")["close"].resample("7min").ohlc().dropna()
    if len(price_frame) < 20:
        return None

    price_frame["sma20"] = price_frame["close"].rolling(20).mean()
    latest = price_frame.iloc[-1]
    chart_data = {
        "time": int(price_frame.index[-1].timestamp()),
        "open": float(latest["open"]),
        "high": float(latest["high"]),
        "low": float(latest["low"]),
        "close": float(latest["close"]),
        "sma20": float(latest["sma20"]),
    }
    result = {
        "status": "OK",
        "symbol": symbol,
        "wuxing_phase": calculate_wuxing_phase(price_frame.reset_index().rename(columns={"time": "timestamp"})),
        "minor_arcana": calculate_minor_arcana(price_frame, symbol=symbol),
        "chart_data": chart_data,
    }
    with COINGECKO_CACHE_LOCK:
        COINGECKO_CACHE[symbol] = (now, result)
    return result


def fetch_and_calculate_sync(symbol: str | None = None) -> dict[str, Any] | None:
    """Fetch all Tarot watchlist symbols and calculate their M7 signals.

    The optional symbol argument is retained for focused diagnostics; normal calls scan
    all 22 symbols in one worker-thread batch. Results are cached briefly so the WebSocket
    loop does not repeatedly hit MT5 for unchanged M7 data.
    """
    symbols = (symbol,) if symbol else MT5_SYMBOLS
    use_mt5 = mt5 is not None and os.getenv("USE_MT5", "true").strip().lower() in {"1", "true", "yes", "on"}

    try:
        cache_seconds = max(float(os.getenv("MONITOR_CACHE_SECONDS", str(MONITOR_CACHE_SECONDS))), 1.0)
    except ValueError:
        cache_seconds = MONITOR_CACHE_SECONDS

    cache_key = ",".join(symbols)
    now = time.monotonic()
    with MONITOR_CACHE_LOCK:
        cached = MONITOR_CACHE.get(cache_key)
        if cached and now - cached[0] < cache_seconds:
            return cached[1]

    signals: dict[str, Any] = {}
    for current_symbol in symbols:
        if not use_mt5:
            fallback = _fetch_coingecko_signal(current_symbol)
            if fallback is not None:
                signals[current_symbol] = fallback
            continue
        try:
            tick = mt5.symbol_info_tick(current_symbol)
            if tick is None:
                logger.warning("No tick data returned for %s.", current_symbol)
                continue
            signal = _serialize_tick(tick)
            signal["symbol"] = current_symbol
            m7_frame = _fetch_m7_frame(current_symbol)
            signal["wuxing_phase"] = calculate_wuxing_phase(m7_frame) if m7_frame is not None else None
            minor_card = calculate_minor_arcana(m7_frame, symbol=current_symbol) if m7_frame is not None else None
            signal["minor_arcana"] = minor_card
            signal["chart_data"] = _chart_data_from_frame(m7_frame)
            s15_frame = _fetch_s15_frame(current_symbol)
            if m7_frame is not None and s15_frame is not None:
                iching = calculate_iching_weight(m7_frame, _element_for_symbol(current_symbol))
                s15_frame.attrs["volatility_weight"] = iching["volatility_weight"]
                macro_trend = "DOWN" if isinstance(minor_card, str) and minor_card.startswith("SWORDS_") else "UP" if isinstance(minor_card, str) and minor_card.startswith("WANDS_") else "NEUTRAL"
                promoted = evaluate_micro_distortion(s15_frame, minor_card, macro_trend)
                signal["minor_arcana"] = promoted or minor_card
                signal["s15_delta"] = float(s15_frame["close"].iloc[-1] - s15_frame["open"].iloc[0]) if len(s15_frame) >= 4 else 0.0
                signal["s15_volume"] = float(s15_frame["volume"].tail(4).sum())
                signal["is_emperor_synchronized"] = signal["minor_arcana"].startswith("KING_") if isinstance(signal["minor_arcana"], str) else False
            signals[current_symbol] = signal
        except Exception:
            logger.exception("Failed to fetch tick data for %s.", current_symbol)

    if not signals and use_mt5:
        for current_symbol in symbols:
            fallback = _fetch_coingecko_signal(current_symbol)
            if fallback is not None:
                signals[current_symbol] = fallback

    if not signals:
        return None

    result = {"status": "OK", "symbols": signals}
    with MONITOR_CACHE_LOCK:
        MONITOR_CACHE[cache_key] = (now, result)
    return result


def _serialize_tick(tick: Any) -> dict[str, Any]:
    """Convert an MT5 namedtuple or mapping into JSON-compatible values."""
    if hasattr(tick, "_asdict"):
        values = tick._asdict()
    elif isinstance(tick, dict):
        values = tick
    else:
        values = {
            name: getattr(tick, name)
            for name in ("time", "bid", "ask", "last", "volume")
            if hasattr(tick, name)
        }

    return {
        key: value.isoformat() if hasattr(value, "isoformat") else value
        for key, value in values.items()
    }


def _major_arcana_for_symbol(symbol: str) -> str | None:
    """Return the configured Major Arcana card for a watchlist symbol."""
    for entry in MAJOR_ARCANA_SYMBOLS.values():
        if entry["symbol"] == symbol:
            return entry["card"]
    return None


def _element_for_symbol(symbol: str) -> str:
    """Resolve the mapped Wu Xing element for a monitored symbol."""
    for entry in MAJOR_ARCANA_SYMBOLS.values():
        if entry["symbol"] == symbol:
            return entry["element"]
    return "EARTH"


def _tarot_screener_payload(symbol: str, signal: dict[str, Any]) -> dict[str, Any]:
    """Combine a symbol signal with its tri-layer and court-card interpretation."""
    minor_card = signal.get("minor_arcana")
    phase = signal.get("wuxing_phase")
    if isinstance(minor_card, str) and minor_card.startswith("WANDS_"):
        micro_status = "FILLING"
    elif isinstance(minor_card, str) and minor_card.startswith("SWORDS_"):
        micro_status = "PRESSURE"
    else:
        micro_status = "STABLE"

    if isinstance(minor_card, str) and (minor_card.startswith("SWORDS_") or minor_card in {"WANDS_8", "WANDS_9", "WANDS_10"}):
        macro_status = "DOWN_CONFIRMED"
    elif phase in {"WOOD", "FIRE"}:
        macro_status = "UP_CONFIRMED"
    else:
        macro_status = "NEUTRAL"

    promoted_card = evaluate_court_card(minor_card, micro_status, macro_status)
    return {
        "event": "TAROT_SCREENER_UPDATE",
        "symbol": symbol,
        "major_arcana": _major_arcana_for_symbol(symbol),
        "minor_arcana": promoted_card,
        "tri_layer": {
            "macro": macro_status,
            "meso": minor_card,
            "micro": micro_status,
        },
        "chart_data": signal.get("chart_data"),
    }


@app.get("/")
def health_check() -> dict[str, str]:
    """Return a lightweight application health response."""
    return {"status": "ok"}


@app.websocket("/ws/signals")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Stream one Tarot screener update per watched symbol every five seconds."""
    await websocket.accept()
    try:
        while True:
            result = await asyncio.to_thread(fetch_and_calculate_sync)
            if result is not None:
                if "symbols" in result and isinstance(result["symbols"], dict):
                    for symbol, signal in result["symbols"].items():
                        await websocket.send_json(_tarot_screener_payload(symbol, signal))
                    await asyncio.sleep(5.0)
                else:
                    # Preserve the legacy response shape for existing knot tests/callers.
                    await websocket.send_json({"event": "KNOT_UPDATE", "data": result})
            else:
                await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception:
        logger.exception("WebSocket endpoint stopped unexpectedly.")
