"""
Pytest common fixtures for backend tests.

Fixtures:
- mock_mt5: automatically patches sys.modules so imports of 'MetaTrader5' resolve to the test mock.
- sample_ticks_df: returns a pandas.DataFrame containing several hours of 15-second ticks suitable for resampling tests.
"""

from typing import Generator, Optional
import sys
import importlib
import pytest
import pandas as pd
import numpy as np
import datetime


@pytest.fixture(scope="session", autouse=True)
def mock_mt5() -> Generator[None, None, None]:
    """
    Autouse fixture that injects the mt5 mock into sys.modules as 'MetaTrader5'.

    This allows code that does `import MetaTrader5 as mt5` to receive the mock implementation
    from tests.backend.mocks.mt5_mock, avoiding any real MT5 terminal dependency during CI.
    """
    module_name = "MetaTrader5"
    mock_module_name = "tests.backend.mocks.mt5_mock"

    # If a real MetaTrader5 module is already present, keep reference to restore later.
    original: Optional[object] = sys.modules.get(module_name)
    try:
        mock_mod = importlib.import_module(mock_module_name)
    except Exception as exc:
        raise RuntimeError(f"Failed to import mock module '{mock_module_name}': {exc}") from exc

    sys.modules[module_name] = mock_mod
    yield
    # Teardown: restore original module or remove the injected one
    if original is None:
        sys.modules.pop(module_name, None)
    else:
        sys.modules[module_name] = original


@pytest.fixture
def sample_ticks_df() -> pd.DataFrame:
    """
    Generate a sample ticks DataFrame with several hours of 15-second bars.

    The returned DataFrame:
    - index: DatetimeIndex named 'time'
    - columns: ['bid','ask','last','volume','flags']
    - contains continuous 15-second ticks for 4 hours (sufficient for 15s and 7min resampling tests)
    """
    hours = 4
    freq = "15S"
    periods = int((hours * 3600) / 15)

    end = pd.Timestamp.now().floor("S")
    start = end - pd.Timedelta(hours=hours)

    rng = pd.date_range(start=start, periods=periods, freq=freq)

    # Create deterministic synthetic price series
    base_price = 10000.0
    # small oscillation + gentle upward drift
    idx = np.arange(len(rng))
    bid = base_price + np.sin(idx / 30.0) * 5.0 + (idx * 0.001)
    ask = bid + 0.5
    last = bid + (idx % 3) * 0.01
    volume = 1 + (idx % 10)
    flags = np.zeros(len(rng), dtype=int)

    df = pd.DataFrame(
        {
            "bid": np.round(bid, 5),
            "ask": np.round(ask, 5),
            "last": np.round(last, 5),
            "volume": volume.astype(float),
            "flags": flags.astype(int),
        },
        index=rng,
    )
    df.index.name = "time"
    # Also expose unix timestamp column for tests that expect integer times
    df["time_unix"] = (df.index.view("int64") // 10 ** 9).astype(int)
    return df