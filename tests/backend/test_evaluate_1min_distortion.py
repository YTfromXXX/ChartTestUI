"""Tests for the single-minute distortion evaluation logic.

These tests validate the behavior of evaluate_1min_distortion(), which compares the
short-term S15 pressure window immediately after a detected knot against the eventual
M8 close direction to determine whether the prediction was correct.
"""

from __future__ import annotations

import importlib

import pandas as pd
import pytest


def _load_evaluate_1min_distortion():
    """Import the implementation if it exists in the backend package."""
    candidates = [
        "backend.evaluate_1min_distortion",
        "src.backend.evaluate_1min_distortion",
        "app.backend.evaluate_1min_distortion",
        "evaluate_1min_distortion",
    ]
    for module_name in candidates:
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError:
            continue
        if hasattr(module, "evaluate_1min_distortion"):
            return module.evaluate_1min_distortion

    pytest.skip("evaluate_1min_distortion is not available in this repository snapshot.", allow_module_level=True)


evaluate_1min_distortion = _load_evaluate_1min_distortion()


def _build_s15_df(start: pd.Timestamp, opens: list[float], closes: list[float]) -> pd.DataFrame:
    """Build a 15-second bar DataFrame for a short 1-minute window."""
    times = pd.date_range(start=start, periods=len(opens), freq="15s")
    df = pd.DataFrame(
        {
            "open": opens,
            "high": [max(o, c) + 0.2 for o, c in zip(opens, closes)],
            "low": [min(o, c) - 0.2 for o, c in zip(opens, closes)],
            "close": closes,
        },
        index=times,
    )
    df.index.name = "time"
    return df


def _build_m8_df(ts: pd.Timestamp, open_price: float, close_price: float) -> pd.DataFrame:
    """Build a single-row M8 OHLC frame used to compare the actual outcome."""
    df = pd.DataFrame(
        {
            "open": [open_price],
            "high": [max(open_price, close_price) + 0.2],
            "low": [min(open_price, close_price) - 0.2],
            "close": [close_price],
        },
        index=pd.DatetimeIndex([ts]),
    )
    df.index.name = "time"
    return df


def test_eval_distortion_correct_down():
    """Return a correct result when the S15 squeeze and M8 outcome both indicate a down move.

    Arrange: construct a 1-minute S15 window with a negative delta and an M8 bar that also
    closes below its open.
    Act: evaluate the distortion for a detected knot.
    Assert: the prediction and actual outcome are both down, and the result is marked correct.
    """
    # Arrange
    knot_time = pd.Timestamp("2024-01-01 00:00:00")
    s15_start = knot_time + pd.Timedelta(minutes=7)
    df_s15 = _build_s15_df(
        s15_start,
        opens=[100.0, 99.6, 99.2, 98.8],
        closes=[99.8, 99.1, 98.7, 98.4],
    )
    df_m8 = _build_m8_df(knot_time + pd.Timedelta(minutes=8), 100.3, 99.0)
    detected_knots = [{"knot_time": knot_time}]

    # Act
    result = evaluate_1min_distortion(detected_knots, df_s15, df_m8)

    # Assert
    assert not result.empty
    assert result.iloc[0]["is_predicting_down"] is True
    assert result.iloc[0]["actual_is_down"] is True
    assert result.iloc[0]["is_correct"] is True


def test_eval_distortion_correct_up():
    """Return a correct result when both S15 and M8 confirm a bullish break.

    Arrange: build a short S15 window with a positive delta and an M8 bar that closes above
    its open.
    Act: evaluate the distortion for the same knot.
    Assert: the result confirms an upward move and marks the prediction as correct.
    """
    # Arrange
    knot_time = pd.Timestamp("2024-01-01 00:00:00")
    s15_start = knot_time + pd.Timedelta(minutes=7)
    df_s15 = _build_s15_df(
        s15_start,
        opens=[100.0, 100.3, 100.7, 101.2],
        closes=[100.5, 101.0, 101.4, 101.8],
    )
    df_m8 = _build_m8_df(knot_time + pd.Timedelta(minutes=8), 100.1, 101.5)
    detected_knots = [{"knot_time": knot_time}]

    # Act
    result = evaluate_1min_distortion(detected_knots, df_s15, df_m8)

    # Assert
    assert not result.empty
    assert result.iloc[0]["is_predicting_down"] is False
    assert result.iloc[0]["actual_is_down"] is False
    assert result.iloc[0]["is_correct"] is True


def test_eval_distortion_incorrect_prediction():
    """Reject a false bearish prediction when the 8-minute bar actually repairs upward.

    Arrange: create an S15 window that leans bearish, but set the M8 close above the open.
    Act: run the evaluation.
    Assert: the prediction is marked as wrong because the actual result disagrees.
    """
    # Arrange
    knot_time = pd.Timestamp("2024-01-01 00:00:00")
    s15_start = knot_time + pd.Timedelta(minutes=7)
    df_s15 = _build_s15_df(
        s15_start,
        opens=[100.0, 99.7, 99.2, 98.9],
        closes=[99.8, 99.3, 98.8, 98.4],
    )
    df_m8 = _build_m8_df(knot_time + pd.Timedelta(minutes=8), 98.6, 99.9)
    detected_knots = [{"knot_time": knot_time}]

    # Act
    result = evaluate_1min_distortion(detected_knots, df_s15, df_m8)

    # Assert
    assert not result.empty
    assert result.iloc[0]["is_predicting_down"] is True
    assert result.iloc[0]["actual_is_down"] is False
    assert result.iloc[0]["is_correct"] is False


def test_eval_distortion_missing_s15_data():
    """Skip a node cleanly when the 1-minute S15 slice has no data at all.

    Arrange: define a knot whose target 1-minute window is completely absent from the S15 frame.
    Act: call evaluate_1min_distortion for that knot.
    Assert: the function does not raise and the result excludes the node.
    """
    # Arrange
    knot_time = pd.Timestamp("2024-01-01 00:00:00")
    df_s15 = _build_s15_df(
        pd.Timestamp("2024-01-01 00:00:00"),
        opens=[100.0, 100.2, 100.1, 100.3],
        closes=[100.4, 100.5, 100.7, 101.0],
    )
    df_m8 = _build_m8_df(knot_time + pd.Timedelta(minutes=8), 100.5, 99.4)
    detected_knots = [{"knot_time": knot_time}]

    # Act
    result = evaluate_1min_distortion(detected_knots, df_s15, df_m8)

    # Assert
    assert result.empty
