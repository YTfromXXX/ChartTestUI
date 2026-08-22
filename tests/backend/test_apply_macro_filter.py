"""Tests for the H1 macro trend filter."""

from __future__ import annotations

import importlib

import pandas as pd
import pytest


def _load_apply_macro_filter():
    """Import the implementation if it exists in the backend package."""
    candidates = [
        "backend.apply_macro_filter",
        "src.backend.apply_macro_filter",
        "app.backend.apply_macro_filter",
        "apply_macro_filter",
    ]
    for module_name in candidates:
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError:
            continue
        if hasattr(module, "apply_macro_filter"):
            return module.apply_macro_filter

    pytest.skip("apply_macro_filter is not available in this repository snapshot.", allow_module_level=True)


apply_macro_filter = _load_apply_macro_filter()


def _build_h1_df(closes: list[float], start: pd.Timestamp = pd.Timestamp("2024-01-01 00:00:00")) -> pd.DataFrame:
    """Build a continuous H1 OHLC DataFrame with at least the requested history."""
    timestamps = pd.date_range(start=start, periods=len(closes), freq="1H")
    df = pd.DataFrame(
        {
            "open": closes,
            "high": [price + 1.0 for price in closes],
            "low": [price - 1.0 for price in closes],
            "close": closes,
            "tick_volume": [100] * len(closes),
        },
        index=timestamps,
    )
    df.index.name = "time"
    return df


def _downtrend_closes(periods: int = 60) -> list[float]:
    """Return a steadily falling series where SMA20 is below SMA50."""
    return [200.0 - (index * 1.5) for index in range(periods)]


def test_macro_filter_success_downtrend():
    """Keep a knot and annotate it when the latest confirmed H1 bar is bearish.

    Arrange: create 60 falling H1 closes so SMA20 is below SMA50 and close is below SMA20
    at the knot timestamp's latest confirmed bar.
    Act: apply the macro filter to one detected knot.
    Assert: the knot remains and receives the DOWN_CONFIRMED macro annotation.
    """
    # Arrange
    df_h1 = _build_h1_df(_downtrend_closes())
    knot_time = df_h1.index[-1] + pd.Timedelta(minutes=7)
    detected_knots = [{"knot_time": knot_time}]

    # Act
    filtered_knots = apply_macro_filter(detected_knots, df_h1)

    # Assert
    assert len(filtered_knots) == 1
    assert filtered_knots[0]["macro_trend"] == "DOWN_CONFIRMED"


def test_macro_filter_fail_uptrend():
    """Exclude a knot when the latest confirmed H1 bar does not confirm a downtrend.

    Arrange: create enough history for SMA50, then use a rising H1 series where close is
    above SMA20 and SMA20 is above SMA50.
    Act: apply the macro filter to one detected knot.
    Assert: no knot passes the bearish macro filter.
    """
    # Arrange
    df_h1 = _build_h1_df([100.0 + (index * 1.5) for index in range(60)])
    knot_time = df_h1.index[-1] + pd.Timedelta(minutes=7)
    detected_knots = [{"knot_time": knot_time}]

    # Act
    filtered_knots = apply_macro_filter(detected_knots, df_h1)

    # Assert
    assert filtered_knots == []


def test_macro_filter_insufficient_data():
    """Exclude a knot without raising when fewer than 50 H1 bars are available.

    Arrange: provide only 49 continuous H1 bars, leaving SMA50 undefined.
    Act: apply the macro filter to a knot after the available data.
    Assert: the incomplete macro history causes the knot to be skipped.
    """
    # Arrange
    df_h1 = _build_h1_df(_downtrend_closes(periods=49))
    knot_time = df_h1.index[-1] + pd.Timedelta(minutes=7)
    detected_knots = [{"knot_time": knot_time}]

    # Act
    filtered_knots = apply_macro_filter(detected_knots, df_h1)

    # Assert
    assert filtered_knots == []


def test_macro_filter_prevent_lookahead_bias():
    """Use the last completed H1 bar instead of a sharp future rally.

    Arrange: create a falling history through 09:00, then add a sharp rally at 10:00. The
    knot is at 10:07, so the 10:00 candle is still forming and must not affect the decision.
    Act: apply the macro filter to the knot.
    Assert: the 09:00 bearish confirmed bar is used and the knot remains annotated as down.
    """
    # Arrange
    start = pd.Timestamp("2024-01-01 00:00:00")
    timestamps = pd.date_range(start=start, periods=60, freq="1H")
    closes = _downtrend_closes(periods=60)
    closes[-2] = 110.0  # 09:00: last completed bearish bar before the knot.
    closes[-1] = 300.0  # 10:00: future/incomplete rally bar; must be ignored.
    df_h1 = _build_h1_df(closes, start=start)
    knot_time = timestamps[-1] + pd.Timedelta(minutes=7)
    detected_knots = [{"knot_time": knot_time}]

    # Act
    filtered_knots = apply_macro_filter(detected_knots, df_h1)

    # Assert
    assert len(filtered_knots) == 1
    assert filtered_knots[0]["macro_trend"] == "DOWN_CONFIRMED"
