"""FastAPI entry point for the real-time MT5 signal stream."""

from __future__ import annotations

import asyncio
import logging
import math
import os
import random
import threading
import time
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

from auth import authenticate_user, get_current_user, issue_token
from database.magic_ledger import MagicLedgerDB
from market_aggregator import TarotMatrixManager
from mt5_executor import MT5Executor

from tarot_engine import (
    MAJOR_ARCANA_SYMBOLS,
    WATCHLIST_SYMBOLS,
    calculate_iching_weight,
    calculate_minor_arcana,
    evaluate_court_promotion,
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
matrix_manager = TarotMatrixManager()
magic_ledger = MagicLedgerDB(os.getenv("MAGIC_LEDGER_DB", "magic_ledger.db"))
mt5_executor = MT5Executor()
matrix_refresh_task: asyncio.Task[None] | None = None


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
LAST_PROMOTED_CARDS: dict[str, str] = {}


def _dummy_knot_payload(symbol: str) -> dict[str, Any]:
    """Create a lightweight one-second demo payload for a subscribed symbol."""
    price = 100.0 + random.uniform(-2.0, 2.0)
    delta = random.uniform(-1.0, 1.0)
    rsi = random.uniform(10.0, 90.0)
    physics = calculate_physics_parameters(rsi, random.uniform(100.0, 1000.0))
    return {
        "event": "KNOT_UPDATE", "symbol": symbol,
        "major_arcana": "0_THE_FOOL" if symbol.startswith("DOGE") else "4_THE_EMPEROR",
        "knot_type": "らせん結び", "market_behavior": "VOLATILE_DRIFT",
        "wuxing_phase": random.choice(["FIRE", "WATER", "WOOD", "EARTH", "METAL"]),
        "rsi_tension": physics["rsi_tension"], "volume_mass": physics["volume_mass"],
        "elastic_energy": physics["elastic_energy"], "event": physics["event"],
        "tarot_attribute": {"element": "FIRE", "polarity": "dynamic"},
        "hexagram_binary": format(random.randrange(64), "06b"),
        "tri_layer": {"macro": "TRENDING", "meso": "KNOT_FORMED", "micro": "PRESSURE"},
        "s15_volume": round(random.uniform(100.0, 1000.0), 2),
        "s15_delta": round(delta, 4), "is_emperor_synchronized": abs(delta) > 0.8,
        "chart_data": {"time": int(time.time()), "open": price - delta, "high": price + 0.5, "low": price - 0.5, "close": price, "sma20": price - 0.1},
    }


def calculate_physics_parameters(rsi: float, volume_weight: float) -> dict[str, Any]:
    """Calculate tension and elastic energy for a market knot."""
    tension = abs(rsi - 50.0)
    elastic_energy = 0.5 * volume_weight * math.pow(tension, 2)
    is_burst = (rsi > 85.0 or rsi < 15.0) and elastic_energy > 5000.0
    return {
        "rsi_tension": round(tension, 4),
        "volume_mass": round(volume_weight, 4),
        "elastic_energy": round(elastic_energy, 4),
        "event": "knot_burst" if is_burst else "stable",
    }


class MagicCastRequest(BaseModel):
    """Request payload for spending elemental mana on a market intervention."""

    element: str = Field(min_length=1)
    mana_cost: int = Field(gt=0)
    target_symbol: str = Field(min_length=1)


async def execute_trade(symbol: str, action: str) -> None:
    """Placeholder for the asynchronous broker integration."""
    await asyncio.to_thread(mt5_executor.execute, symbol, action)


async def post_to_sns(message: str) -> None:
    """Placeholder for the asynchronous SNS integration."""
    print(f"[CAST MAGIC] post_to_sns message={message}")


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
    global matrix_refresh_task
    matrix_refresh_task = asyncio.create_task(_matrix_refresh_loop())


async def _matrix_refresh_loop() -> None:
    """Refresh active candidates periodically while the MT5 session is alive."""
    while True:
        try:
            await matrix_manager.refresh_active_symbols(force=True)
            await asyncio.sleep(matrix_manager.refresh_seconds)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Tarot matrix refresh failed; retrying next interval.")
            await asyncio.sleep(matrix_manager.refresh_seconds)


@app.on_event("shutdown")
def shutdown_mt5() -> None:
    """Release the MT5 terminal connection when the application stops."""
    if mt5 is not None:
        if matrix_refresh_task is not None:
            matrix_refresh_task.cancel()
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
    assigned_symbols = tuple(
        assignment["active_symbol"] for assignment in matrix_manager.active_assignments().values()
    )
    symbols = (symbol,) if symbol else assigned_symbols or MT5_SYMBOLS
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
                promoted = evaluate_court_promotion(
                    s15_frame,
                    minor_card or "",
                    macro_trend,
                    iching["volatility_weight"] or 1.0,
                )
                signal["minor_arcana"] = promoted or minor_card
                signal["s15_delta"] = float(
                    (s15_frame["close"].tail(4) - s15_frame["open"].tail(4)).sum()
                ) if len(s15_frame) >= 4 else 0.0
                signal["s15_volume"] = float(s15_frame["volume"].tail(4).sum())
                signal["is_emperor_synchronized"] = signal["minor_arcana"].startswith("KING_") if isinstance(signal["minor_arcana"], str) else False
                if (
                    isinstance(promoted, str)
                    and promoted.startswith(("KNIGHT_", "QUEEN_", "KING_"))
                    and promoted != LAST_PROMOTED_CARDS.get(current_symbol)
                ):
                    ledger_result = magic_ledger.record_promotion_and_extract_mana({
                        "symbol": current_symbol,
                        "element": _element_for_symbol(current_symbol),
                        "wuxing_phase": signal.get("wuxing_phase"),
                        "hexagram": iching.get("hexagram_binary"),
                        "promoted_card": promoted,
                        "s15_volume": signal["s15_volume"],
                        "s15_delta": signal["s15_delta"],
                    })
                    logger.info("Mana extraction: %s", ledger_result["incantation"])
                    LAST_PROMOTED_CARDS[current_symbol] = promoted
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
    matrix_entry = next(
        (entry for entry in matrix_manager.active_assignments().values() if entry.get("active_symbol") == symbol),
        None,
    ) or next(
        (entry for entry in matrix_manager.matrix.values() if symbol in entry.get("symbol_pool", [])),
        {},
    )
    return {
        "event": "TAROT_SCREENER_UPDATE",
        "symbol": symbol,
        "major_arcana": _major_arcana_for_symbol(symbol),
        "minor_arcana": promoted_card,
        "knot_type": matrix_entry.get("knot_type"),
        "market_behavior": matrix_entry.get("market_behavior"),
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


@app.post("/api/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()) -> dict[str, str]:
    """Issue a short-lived JWT for the configured observer account."""
    try:
        valid = authenticate_user(form_data.username, form_data.password)
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        token = issue_token(form_data.username)
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    return {"access_token": token, "token_type": "bearer"}


@app.post("/api/cast_magic")
async def cast_magic(request: MagicCastRequest, current_user: str = Depends(get_current_user)) -> dict[str, Any]:
    """Consume elemental mana, then trigger the trade and story integrations."""
    element = request.element.strip().upper()
    target_symbol = request.target_symbol.strip().upper()
    if not target_symbol:
        raise HTTPException(status_code=400, detail="target_symbol is required.")

    message = (
        f"【魔力解放】観測者が{request.mana_cost}の{element} Manaを消費。"
        f"{target_symbol}の乱気流へ介入し、KING_OF_WANDSの加護のもと"
        "ロングエントリーを執行します。"
    )
    try:
        cast_result = magic_ledger.begin_cast(element, request.mana_cost, target_symbol, message)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    if cast_result is None:
        raise HTTPException(status_code=400, detail="Insufficient mana for this cast.")

    cast_id, remaining_mana = cast_result
    try:
        await asyncio.gather(execute_trade(target_symbol, "LONG"), post_to_sns(message))
    except Exception as error:
        magic_ledger.rollback_cast(cast_id)
        logger.exception("Cast %s failed for user %s; mana returned.", cast_id, current_user)
        raise HTTPException(status_code=502, detail="External cast execution failed; mana returned.") from error

    magic_ledger.complete_cast(cast_id, "SUCCESS")

    return {
        "status": "success",
        "consumed_mana": request.mana_cost,
        "message": message,
        "remaining_mana": remaining_mana,
        "cast_id": cast_id,
    }


@app.websocket("/ws/signals")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Stream legacy screener data or one-second demo data for a subscribed symbol."""
    await websocket.accept()
    try:
        try:
            request = await asyncio.wait_for(websocket.receive_json(), timeout=0.05)
        except asyncio.TimeoutError:
            request = None
        subscribed_symbol = str(request.get("symbol", "")).strip().upper() if isinstance(request, dict) and request.get("action", "subscribe") == "subscribe" else ""
        if subscribed_symbol:
            while True:
                await websocket.send_json(_dummy_knot_payload(subscribed_symbol))
                await asyncio.sleep(1.0)

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
