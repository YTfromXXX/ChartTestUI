"""Unified market-data acquisition for the Major Arcana watchlist."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import pandas as pd
import requests

from config.archetype_matrix import ARCHETYPE_MATRIX

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None  # type: ignore[assignment]

try:
    import yfinance as yf
except ImportError:
    yf = None  # type: ignore[assignment]

try:
    import ccxt
except ImportError:
    ccxt = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

UNIFIED_SYMBOLS: dict[int, dict[str, str]] = {
    0: {"card": "THE_FOOL", "symbol": "DOGE", "source": "crypto", "name": "Dogecoin"},
    1: {"card": "THE_MAGICIAN", "symbol": "BTCUSD", "source": "crypto", "name": "Bitcoin"},
    2: {"card": "THE_HIGH_PRIESTESS", "symbol": "EURUSD", "source": "forex", "name": "Euro / US Dollar"},
    3: {"card": "THE_EMPRESS", "symbol": "XAUUSD", "source": "mt5", "name": "Gold"},
    4: {"card": "THE_EMPEROR", "symbol": "US500", "source": "mt5", "name": "S&P 500"},
    5: {"card": "THE_HIEROPHANT", "symbol": "GBPUSD", "source": "forex", "name": "British Pound / US Dollar"},
    6: {"card": "THE_LOVERS", "symbol": "ETH", "source": "crypto", "name": "Ethereum"},
    7: {"card": "THE_CHARIOT", "symbol": "USDJPY", "source": "forex", "name": "US Dollar / Japanese Yen"},
    8: {"card": "STRENGTH", "symbol": "AAPL", "source": "stock", "name": "Apple"},
    9: {"card": "THE_HERMIT", "symbol": "XAGUSD", "source": "mt5", "name": "Silver"},
    10: {"card": "WHEEL_OF_FORTUNE", "symbol": "TSLA", "source": "stock", "name": "Tesla"},
    11: {"card": "JUSTICE", "symbol": "AUDUSD", "source": "forex", "name": "Australian Dollar / US Dollar"},
    12: {"card": "THE_HANGED_MAN", "symbol": "PEPE", "source": "crypto", "name": "Pepe"},
    13: {"card": "DEATH", "symbol": "SOL", "source": "crypto", "name": "Solana"},
    14: {"card": "TEMPERANCE", "symbol": "USDCHF", "source": "forex", "name": "US Dollar / Swiss Franc"},
    15: {"card": "THE_DEVIL", "symbol": "NVDA", "source": "stock", "name": "NVIDIA"},
    16: {"card": "THE_TOWER", "symbol": "BTCXAU", "source": "mt5", "name": "Bitcoin / Gold"},
    17: {"card": "THE_STAR", "symbol": "MSFT", "source": "stock", "name": "Microsoft"},
    18: {"card": "THE_MOON", "symbol": "USDCAD", "source": "forex", "name": "US Dollar / Canadian Dollar"},
    19: {"card": "THE_SUN", "symbol": "AMZN", "source": "stock", "name": "Amazon"},
    20: {"card": "JUDGEMENT", "symbol": "ADA", "source": "crypto", "name": "Cardano"},
    21: {"card": "THE_WORLD", "symbol": "META", "source": "stock", "name": "Meta Platforms"},
}

_COMMON_COLUMNS = ["time", "open", "high", "low", "close", "volume"]
_CRYPTO_IDS = {
    "DOGE": "dogecoin",
    "DOGEUSD": "dogecoin",
    "BTCUSD": "bitcoin",
    "AVAXUSD": "avalanche-2",
    "ETH": "ethereum",
    "ETHUSD": "ethereum",
    "PEPE": "pepe",
    "PEPEUSD": "pepe",
    "SHIBUSD": "shiba-inu",
    "SOL": "solana",
    "SOLUSD": "solana",
    "MATICUSD": "matic-network",
    "LINKUSD": "chainlink",
    "ADA": "cardano",
    "ADAUSD": "cardano",
    "LTCUSD": "litecoin",
    "XRPUSD": "ripple",
    "USDTUSD": "tether",
    "USDC": "usd-coin",
    "USDCUSD": "usd-coin",
    "LUNAUSD": "terra-luna-2",
    "APTUSD": "aptos",
}
_FOREX_YF_TICKERS = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "JPY=X",
    "AUDUSD": "AUDUSD=X",
    "USDCHF": "CHF=X",
    "USDCAD": "CAD=X",
}
_MT5_SYMBOLS = {"XAUUSD", "US500", "USDJPY", "XAGUSD", "DAX40", "GER40", "BTCXAU"}
_STOCK_SYMBOLS = {"AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "SPY", "VIX"}


def _source_for_symbol(symbol: str) -> str:
    """Infer a provider for matrix candidates that only carry a symbol name."""
    if symbol in _MT5_SYMBOLS:
        return "mt5"
    if symbol in _STOCK_SYMBOLS:
        return "stock"
    if symbol in _FOREX_YF_TICKERS:
        return "forex"
    return "crypto"


def _empty_or_normalize(frame: pd.DataFrame | None) -> pd.DataFrame | None:
    """Normalize provider output into the six-column public schema."""
    if frame is None or frame.empty:
        return None
    result = frame.copy()
    if isinstance(result.columns, pd.MultiIndex):
        result.columns = [column[0] for column in result.columns]
    result = result.reset_index()
    time_column = next((column for column in ("time", "Datetime", "Date", "index") if column in result.columns), None)
    if time_column is None:
        return None
    result = result.rename(columns={time_column: "time", "Volume": "volume", "Open": "open", "High": "high", "Low": "low", "Close": "close"})
    if "volume" not in result:
        result["volume"] = 0.0
    missing = [column for column in _COMMON_COLUMNS if column not in result.columns]
    if missing:
        return None
    result = result[_COMMON_COLUMNS].copy()
    result["time"] = pd.to_datetime(result["time"], utc=True, errors="coerce")
    for column in _COMMON_COLUMNS[1:]:
        result[column] = pd.to_numeric(result[column], errors="coerce")
    result = result.dropna(subset=["time", "open", "high", "low", "close"]).sort_values("time")
    return result.reset_index(drop=True)


def _resample_to_7m(frame: pd.DataFrame, limit: int) -> pd.DataFrame | None:
    """Aggregate provider candles to the requested seven-minute approximation."""
    normalized = _empty_or_normalize(frame)
    if normalized is None:
        return None
    indexed = normalized.set_index("time")
    result = indexed.resample("7min", origin="epoch").agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"),
        close=("close", "last"), volume=("volume", "sum"),
    ).dropna(subset=["open", "high", "low", "close"])
    return result.reset_index()[_COMMON_COLUMNS].tail(limit).reset_index(drop=True)


def _fetch_mt5(symbol_info: dict[str, str], limit: int) -> pd.DataFrame | None:
    if mt5 is None or not hasattr(mt5, "copy_rates_from_pos"):
        return None
    timeframe = getattr(mt5, "TIMEFRAME_M1", None)
    if timeframe is None:
        return None
    rates = mt5.copy_rates_from_pos(symbol_info["symbol"], timeframe, 0, max(limit * 8, 100))
    return _resample_to_7m(pd.DataFrame(rates) if rates is not None else None, limit)


def _fetch_crypto(symbol_info: dict[str, str], limit: int) -> pd.DataFrame | None:
    symbol = symbol_info["symbol"]
    coin_id = _CRYPTO_IDS.get(symbol)
    if coin_id is None:
        return None
    response = requests.get(
        f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart",
        params={"vs_currency": "usd", "days": "1"},
        timeout=10,
    )
    response.raise_for_status()
    prices = response.json().get("prices", [])
    frame = pd.DataFrame(prices, columns=["time", "close"])
    if frame.empty:
        return None
    frame["time"] = pd.to_datetime(frame["time"], unit="ms", utc=True)
    frame["open"] = frame["close"]
    frame["high"] = frame["close"]
    frame["low"] = frame["close"]
    frame["volume"] = 0.0
    return _resample_to_7m(frame, limit)


def _fetch_stock(symbol_info: dict[str, str], limit: int) -> pd.DataFrame | None:
    if yf is None:
        return None
    ticker = _FOREX_YF_TICKERS.get(symbol_info["symbol"], symbol_info["symbol"])
    frame = yf.download(tickers=ticker, period="5d", interval="5m", progress=False, auto_adjust=False, threads=False)
    return _resample_to_7m(frame, limit)


async def fetch_unified_market_data(
    symbol_info: dict[str, str], timeframe: str = "7m", limit: int = 100
) -> pd.DataFrame | None:
    """Fetch market data from MT5, CoinGecko, or yfinance in a common format.

    Network and terminal APIs are synchronous, so they run in a worker thread. Any
    unsupported source, malformed response, provider error, or rate-limit failure returns
    ``None`` rather than propagating an exception into the monitoring loop.
    """
    if not isinstance(symbol_info, dict) or limit <= 0:
        return None
    source = symbol_info.get("source")
    try:
        if source == "mt5":
            frame = await asyncio.to_thread(_fetch_mt5, symbol_info, limit)
        elif source == "crypto":
            frame = await asyncio.to_thread(_fetch_crypto, symbol_info, limit)
        elif source in {"stock", "forex"}:
            frame = await asyncio.to_thread(_fetch_stock, symbol_info, limit)
        else:
            logger.warning("Unsupported market data source: %s", source)
            return None
    except Exception as exc:
        logger.warning("Market data fetch failed for %s: %s", symbol_info.get("symbol"), exc)
        return None

    if frame is None:
        return None
    if timeframe != "7m":
        logger.info("timeframe=%s requested; returning normalized provider data near 7m.", timeframe)
    return frame.tail(limit).reset_index(drop=True)


class TarotMatrixManager:
    """Keep one healthy active market assigned to every Major Arcana slot."""

    def __init__(self, matrix: dict[int, dict[str, Any]] | None = None, refresh_seconds: float = 30.0):
        self.matrix = matrix or ARCHETYPE_MATRIX
        self.refresh_seconds = max(refresh_seconds, 1.0)
        self.active_symbols: dict[int, dict[str, Any]] = {}
        self.last_refresh: float = 0.0
        self._lock = asyncio.Lock()

    async def refresh_active_symbols(self, force: bool = False) -> dict[int, dict[str, Any]]:
        """Probe each candidate pool in order and retain the first healthy candidate."""
        now = asyncio.get_running_loop().time()
        if not force and now - self.last_refresh < self.refresh_seconds:
            return self.active_symbols.copy()

        async with self._lock:
            now = asyncio.get_running_loop().time()
            if not force and now - self.last_refresh < self.refresh_seconds:
                return self.active_symbols.copy()
            used_symbols: set[str] = set()
            for arcana_number, archetype in self.matrix.items():
                assigned = None
                for candidate in archetype["symbol_pool"]:
                    if candidate in used_symbols:
                        logger.debug("Skipping already assigned symbol %s for Arcana %s", candidate, arcana_number)
                        continue
                    symbol_info = {
                        "symbol": candidate,
                        "source": _source_for_symbol(candidate),
                        "name": candidate,
                    }
                    try:
                        frame = await fetch_unified_market_data(symbol_info, limit=2)
                    except Exception as exc:
                        logger.warning("Health check failed for %s: %s", candidate, exc)
                        frame = None
                    if frame is not None and not frame.empty:
                        assigned = {**archetype, "active_symbol": candidate, "source": symbol_info["source"]}
                        used_symbols.add(candidate)
                        break

                if assigned is not None:
                    self.active_symbols[arcana_number] = assigned
                elif arcana_number in self.active_symbols:
                    previous_symbol = self.active_symbols[arcana_number].get("active_symbol")
                    if previous_symbol not in used_symbols:
                        used_symbols.add(previous_symbol)
                        logger.warning("Keeping previous active symbol for Arcana %s", arcana_number)
                    else:
                        logger.error("No unique healthy candidate available for Arcana %s", arcana_number)
                else:
                    logger.error("No healthy candidate available for Arcana %s", arcana_number)
            self.last_refresh = now
            return self.active_symbols.copy()

    def active_assignments(self) -> dict[int, dict[str, Any]]:
        """Return the latest assignments without triggering network calls."""
        return self.active_symbols.copy()
