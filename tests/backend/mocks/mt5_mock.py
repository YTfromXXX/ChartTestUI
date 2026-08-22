"""
Mock implementation of the MetaTrader5 API for pytest CI runs.

Provides a minimal subset of the MT5 functions used in tests:
- initialize()
- shutdown()
- copy_ticks_from_pos()
- copy_ticks_range()

Dummy ticks are dictionaries with keys:
  'time'   : int (UNIX timestamp)
  'bid'    : float
  'ask'    : float
  'last'   : float
  'volume' : float
  'flags'  : int
"""

from typing import Any, Dict, List, Union
import time
import math
import datetime

__all__ = ["initialize", "shutdown", "copy_ticks_from_pos", "copy_ticks_range"]


def initialize() -> bool:
    """Pretend to initialize the MT5 terminal. Always returns True."""
    return True


def shutdown() -> None:
    """Pretend to shutdown the MT5 terminal."""
    return None


def _make_tick(ts: int, idx: int, flags: int) -> Dict[str, Any]:
    """
    Create a deterministic dummy tick for a given timestamp and index.

    Uses a small deterministic formula so values vary but are reproducible.
    """
    base = 10000.0
    # deterministic oscillation for price
    bid = base + math.sin(idx / 10.0) * 10.0 + (idx % 100) * 0.01
    ask = bid + 0.5
    last = bid + (idx % 3) * 0.01
    volume = 1.0 + (idx % 10)
    return {
        "time": int(ts),
        "bid": float(round(bid, 5)),
        "ask": float(round(ask, 5)),
        "last": float(round(last, 5)),
        "volume": float(volume),
        "flags": int(flags),
    }


def copy_ticks_from_pos(
    symbol: str, pos: int, count: int, flags: int
) -> List[Dict[str, Any]]:
    """
    Return `count` dummy ticks starting from a position marker `pos`.

    Args:
        symbol: symbol name (ignored in mock but accepted).
        pos: position offset used to shift timestamps (int).
        count: number of ticks to generate.
        flags: flags to attach to each tick (stored in each tick dict).

    Returns:
        List of tick dictionaries with fields 'time','bid','ask','last','volume','flags'.
    """
    now = int(time.time())
    # Use pos to shift the base time backwards for reproducibility
    base_time = now - abs(int(pos))
    ticks: List[Dict[str, Any]] = []
    for i in range(count):
        ts = base_time + i
        ticks.append(_make_tick(ts, i + pos, flags))
    return ticks


def copy_ticks_range(
    symbol: str,
    date_from: Union[int, float, datetime.datetime],
    date_to: Union[int, float, datetime.datetime],
    flags: int,
) -> List[Dict[str, Any]]:
    """
    Return dummy ticks within a time range [date_from, date_to].

    Args:
        symbol: symbol name (ignored in mock).
        date_from/date_to: either UNIX timestamps (int/float) or datetime objects.
        flags: flags to attach to each tick.

    Returns:
        List of tick dictionaries. Ticks are generated at 1-second intervals.
        If date_from > date_to an empty list is returned.
        To avoid overly large responses, the returned list is capped at 10000 ticks.
    """
    def to_ts(v: Union[int, float, datetime.datetime]) -> int:
        if isinstance(v, datetime.datetime):
            return int(v.timestamp())
        return int(v)

    ts_from = to_ts(date_from)
    ts_to = to_ts(date_to)

    if ts_from > ts_to:
        return []

    max_count = 10000
    total_seconds = ts_to - ts_from + 1
    step = 1
    count = min(max_count, total_seconds // step)
    ticks: List[Dict[str, Any]] = []
    for i in range(int(count)):
        ts = ts_from + i * step
        ticks.append(_make_tick(ts, i, flags))
    return ticks