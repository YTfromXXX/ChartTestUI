"""Tests for MT5 execution safety guards."""

import pytest

from mt5_executor import MT5Executor


def test_dry_run_does_not_require_mt5(monkeypatch, capsys):
    monkeypatch.setenv("DRY_RUN", "True")
    executor = MT5Executor()
    result = executor.execute("BTCUSD", "LONG", 0.01)
    assert result["status"] == "dry_run"
    assert "[DRY_RUN]" in capsys.readouterr().out


def test_executor_blocks_unknown_symbol_and_oversized_lot(monkeypatch):
    monkeypatch.setenv("DRY_RUN", "True")
    monkeypatch.setenv("MAX_LOT_SIZE", "0.01")
    executor = MT5Executor()
    with pytest.raises(ValueError):
        executor.execute("UNKNOWN", "LONG", 0.01)
    with pytest.raises(ValueError):
        executor.execute("BTCUSD", "LONG", 0.02)


def test_executor_blocks_duplicate_symbol(monkeypatch):
    monkeypatch.setenv("DRY_RUN", "True")
    monkeypatch.setenv("ORDER_COOLDOWN_SECONDS", "5")
    executor = MT5Executor()
    executor.execute("BTCUSD", "LONG", 0.01)
    with pytest.raises(RuntimeError):
        executor.execute("BTCUSD", "LONG", 0.01)