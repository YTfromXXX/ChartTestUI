"""Tests for the mana consumption and cast execution endpoint."""

import os
from unittest.mock import AsyncMock, patch

import bcrypt
from fastapi.testclient import TestClient

from database.magic_ledger import MagicLedgerDB

os.environ["JWT_SECRET_KEY"] = "test-secret"
os.environ["AUTH_EMAIL"] = "observer@example.com"
os.environ["AUTH_PASSWORD_HASH"] = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode()

from main import app


def test_cast_magic_consumes_mana_and_executes_integrations(tmp_path):
    ledger = MagicLedgerDB(tmp_path / "ledger.db")
    with ledger._connect() as connection:
        connection.execute(
            "UPDATE mana_pool SET current_mana = 250 WHERE element = 'FIRE'"
        )

    with (
        patch("main.magic_ledger", ledger),
        patch("main.execute_trade", new_callable=AsyncMock) as execute_trade,
        patch("main.post_to_sns", new_callable=AsyncMock) as post_to_sns,
    ):
        client = TestClient(app)
        token = client.post("/api/token", data={"username": "observer@example.com", "password": "password123"}).json()["access_token"]
        response = client.post(
            "/api/cast_magic",
            headers={"Authorization": f"Bearer {token}"},
            json={"element": "FIRE", "mana_cost": 100, "target_symbol": "BTCUSD"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["remaining_mana"] == 150
    execute_trade.assert_awaited_once_with("BTCUSD", "LONG")
    post_to_sns.assert_awaited_once()


def test_cast_magic_rejects_insufficient_mana(tmp_path):
    ledger = MagicLedgerDB(tmp_path / "ledger.db")

    with patch("main.magic_ledger", ledger):
        client = TestClient(app)
        token = client.post("/api/token", data={"username": "observer@example.com", "password": "password123"}).json()["access_token"]
        response = client.post(
            "/api/cast_magic",
            headers={"Authorization": f"Bearer {token}"},
            json={"element": "WATER", "mana_cost": 100, "target_symbol": "BTCUSD"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Insufficient mana for this cast."


def test_cast_magic_rejects_unknown_element(tmp_path):
    ledger = MagicLedgerDB(tmp_path / "ledger.db")

    with patch("main.magic_ledger", ledger):
        client = TestClient(app)
        token = client.post("/api/token", data={"username": "observer@example.com", "password": "password123"}).json()["access_token"]
        response = client.post(
            "/api/cast_magic",
            headers={"Authorization": f"Bearer {token}"},
            json={"element": "VOID", "mana_cost": 100, "target_symbol": "BTCUSD"},
        )

    assert response.status_code == 400
    assert "element must be one of" in response.json()["detail"]


def test_cast_magic_returns_mana_when_external_execution_fails_in_dry_run(tmp_path, monkeypatch):
    monkeypatch.setenv("DRY_RUN", "True")
    ledger = MagicLedgerDB(tmp_path / "ledger.db")
    with ledger._connect() as connection:
        connection.execute("UPDATE mana_pool SET current_mana = 250 WHERE element = 'FIRE'")

    with patch("main.magic_ledger", ledger), patch("main.post_to_sns", new_callable=AsyncMock, side_effect=RuntimeError("SNS unavailable")):
        client = TestClient(app)
        token = client.post("/api/token", data={"username": "observer@example.com", "password": "password123"}).json()["access_token"]
        response = client.post(
            "/api/cast_magic",
            headers={"Authorization": f"Bearer {token}"},
            json={"element": "FIRE", "mana_cost": 100, "target_symbol": "BTCUSD"},
        )

    assert response.status_code == 502
    with ledger._connect() as connection:
        assert connection.execute("SELECT current_mana FROM mana_pool WHERE element = 'FIRE'").fetchone()[0] == 250
        assert connection.execute("SELECT status FROM magic_casts").fetchone()[0] == "FAILED"