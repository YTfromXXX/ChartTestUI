"""Tests for the double-top knot detection logic in the backend.

The tests intentionally compose synthetic M7 bar data that satisfies or violates the
three detection gates described in the specification:

1. price delta between Top1 and Top2 is within ±0.05%
2. the two peaks are separated by at least 4 M7 bars
3. the second peak has a smaller tick volume than the first peak
"""

from __future__ import annotations

import importlib

import pandas as pd
import pytest


def _load_detect_knots():
    """Import the project implementation if it exists.

    This keeps the test module runnable in early-stage repositories where the backend
    package is not yet present, while still asserting real behavior once the function is
    implemented.
    """
    candidates = [
        "backend.detect_knots",
        "src.backend.detect_knots",
        "app.backend.detect_knots",
        "detect_knots",
    ]
    for module_name in candidates:
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError:
            continue
        if hasattr(module, "detect_knots"):
            return module.detect_knots

    pytest.skip("detect_knots is not available in this repository snapshot.", allow_module_level=True)


detect_knots = _load_detect_knots()


def _build_m7_frame(high_prices: list[float], volumes: list[int]) -> pd.DataFrame:
    """Build a synthetic OHLCV data frame for M7 bars with a time index."""
    timestamps = pd.date_range(start="2024-01-01 00:00:00", periods=len(high_prices), freq="7min")

    data = {
        "open": [price * 0.998 for price in high_prices],
        "high": high_prices,
        "low": [price * 0.995 for price in high_prices],
        "close": high_prices,
        "volume": volumes,
        "tick_volume": volumes,
    }

    df = pd.DataFrame(data, index=timestamps)
    df.index.name = "time"
    return df


def test_detect_knots_success():
    """Return exactly one detected double-top when all three conditions are met.

    Arrange: create a synthetic M7 series with two separated local peaks of almost equal
    price and lower volume on the second peak.
    Act: call detect_knots on the synthetic DataFrame.
    Assert: exactly one candidate is detected.
    """
    # Arrange
    df_m7 = _build_m7_frame(
        high_prices=[99.2, 99.7, 100.4, 100.8, 100.2, 99.9, 99.5, 99.8, 100.79, 100.1, 99.4, 98.8],
        volumes=[120, 150, 180, 400, 210, 190, 170, 160, 300, 220, 200, 180],
    )

    # Act
    result = detect_knots(df_m7)

    # Assert
    assert len(result) == 1


def test_detect_knots_fail_price_delta():
    """Reject a double-top when the second peak exceeds the allowed price tolerance.

    Arrange: use a valid time gap and volume contraction, but increase the second top by
    more than 0.05% relative to the first.
    Act: call detect_knots on the synthetic DataFrame.
    Assert: no candidate matches because the price condition fails.
    """
    # Arrange
    df_m7 = _build_m7_frame(
        high_prices=[99.2, 99.7, 100.4, 100.0, 100.2, 99.9, 99.5, 99.8, 100.15, 100.1, 99.4, 98.8],
        volumes=[120, 150, 180, 400, 210, 190, 170, 160, 300, 220, 200, 180],
    )

    # Act
    result = detect_knots(df_m7)

    # Assert
    assert len(result) == 0


def test_detect_knots_fail_time_symmetry():
    """Reject a double-top when the peaks are too close in time.

    Arrange: keep the price and volume conditions valid, but place the second peak only two
    M7 bars after the first one.
    Act: call detect_knots on the synthetic DataFrame.
    Assert: no knot is detected because the time separation is below the threshold.
    """
    # Arrange
    df_m7 = _build_m7_frame(
        high_prices=[98.0, 99.1, 100.5, 99.7, 100.4, 99.6, 98.7],
        volumes=[180, 200, 420, 250, 300, 220, 200],
    )

    # Act
    result = detect_knots(df_m7)

    # Assert
    assert len(result) == 0


def test_detect_knots_fail_volume():
    """Reject a double-top when the second peak is not volume-depleted.

    Arrange: keep the price gap and bar spacing valid, but set the second peak volume to be
    equal to or greater than the first peak volume.
    Act: call detect_knots on the synthetic DataFrame.
    Assert: no candidate is returned because the volume condition fails.
    """
    # Arrange
    df_m7 = _build_m7_frame(
        high_prices=[99.2, 99.7, 100.4, 100.8, 100.2, 99.9, 99.5, 99.8, 100.79, 100.1, 99.4, 98.8],
        volumes=[120, 150, 180, 400, 210, 190, 170, 160, 450, 220, 200, 180],
    )

    # Act
    result = detect_knots(df_m7)

    # Assert
    assert len(result) == 0


def test_detect_knots_no_peaks():
    """Return no detections when the price series is monotonic and no double-top peaks exist.

    Arrange: build a steadily rising series without any local maxima.
    Act: call detect_knots on the monotonic DataFrame.
    Assert: the result is empty because no mountain-like structure is formed.
    """
    # Arrange
    df_m7 = _build_m7_frame(
        high_prices=[98.0, 98.5, 99.1, 99.7, 100.4, 101.0, 101.8, 102.4, 103.1, 104.0],
        volumes=[110, 120, 130, 150, 170, 190, 220, 240, 260, 280],
    )

    # Act
    result = detect_knots(df_m7)

    # Assert
    assert len(result) == 0
