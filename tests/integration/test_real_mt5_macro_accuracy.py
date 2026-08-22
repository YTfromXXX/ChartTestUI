"""Integration tests for H1 macro trend accuracy using a real MT5 terminal.

These tests intentionally perform network and terminal communication. They do not use
``tests.backend.mocks.mt5_mock`` and require a running MetaTrader 5 terminal with access
to BTCUSD and BTCXAU market data.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

mt5 = pytest.importorskip(
    "MetaTrader5",
    reason="A real MetaTrader5 Python package is required for integration tests.",
)

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def real_mt5_connection():
    """Initialize and shut down the real MT5 terminal for this module."""
    # Arrange
    if not mt5.initialize():
        pytest.skip(f"Unable to initialize MetaTrader5: {mt5.last_error()}")

    # Act
    yield

    # Assert / teardown
    mt5.shutdown()


@pytest.fixture(scope="module")
def real_h1_data(real_mt5_connection):
    """Fetch approximately ten days of H1 data for both integration symbols."""
    data = {}
    for symbol in ("BTCUSD", "BTCXAU"):
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 240)
        if rates is None or len(rates) == 0:
            pytest.skip(f"No real MT5 H1 data available for {symbol}: {mt5.last_error()}")

        frame = pd.DataFrame(rates)
        frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
        frame = frame.set_index("time")
        data[symbol] = frame
    return data


def test_real_h1_data_fetching(real_h1_data):
    """Fetch complete pandas H1 data for BTCUSD and BTCXAU from a real MT5 terminal.

    Arrange: initialize the real MT5 connection and request 240 H1 bars per symbol.
    Act: consume the module-scoped real_h1_data fixture.
    Assert: both symbols produce non-empty DataFrames with required OHLC columns and no
    missing values in the fetched records.
    """
    # Arrange
    required_columns = {"open", "high", "low", "close"}

    # Act
    btcusd = real_h1_data["BTCUSD"]
    btcxau = real_h1_data["BTCXAU"]

    # Assert
    for frame in (btcusd, btcxau):
        assert isinstance(frame, pd.DataFrame)
        assert len(frame) > 0
        assert required_columns.issubset(frame.columns)
        assert frame[list(required_columns)].notna().all().all()


def test_macro_trend_predictive_accuracy(real_h1_data, capsys):
    """Measure three-hour bearish accuracy after H1 macro downtrend signals.

    This test uses live network data from the real MT5 terminal. It calculates SMA20 and
    SMA50, evaluates only completed rows with a valid three-hour look-ahead, and compares
    the next bar's open with the close three bars later.

    Arrange: prepare the live BTCUSD H1 DataFrame and calculate the two moving averages.
    Act: calculate the three-hour direction after every valid bearish macro signal and
    print the resulting win rate.
    Assert: the sample has at least one signal and its bearish accuracy is above 40 percent.
    """
    # Arrange
    df_h1 = real_h1_data["BTCUSD"].copy()
    df_h1["sma20"] = df_h1["close"].rolling(window=20).mean()
    df_h1["sma50"] = df_h1["close"].rolling(window=50).mean()
    df_h1["is_downtrend"] = (df_h1["sma20"] < df_h1["sma50"]) & (df_h1["close"] < df_h1["sma20"])

    valid_signals = df_h1["is_downtrend"] & df_h1["open"].shift(-1).notna() & df_h1["close"].shift(-3).notna()
    signal_rows = df_h1.loc[valid_signals]
    three_hour_deltas = df_h1["close"].shift(-3).loc[valid_signals] - df_h1["open"].shift(-1).loc[valid_signals]

    # Act
    bearish_accuracy = (three_hour_deltas < 0).mean()
    print(f"[BTCUSD] マクロダウントレンド判定後の3時間勝率: {bearish_accuracy * 100:.1f}%")

    # Assert
    assert not signal_rows.empty
    assert bearish_accuracy > 0.40
