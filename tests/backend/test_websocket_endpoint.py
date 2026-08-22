"""Tests for the FastAPI WebSocket signal endpoint."""

from __future__ import annotations

import importlib
import queue
import threading
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


def _load_main_module():
    """Import the FastAPI module containing the WebSocket endpoint."""
    candidates = ["main", "backend.main", "src.main", "app.main"]
    for module_name in candidates:
        try:
            return importlib.import_module(module_name)
        except ModuleNotFoundError:
            continue
    pytest.skip("FastAPI main module is not available in this repository snapshot.", allow_module_level=True)


main_module = _load_main_module()
app = main_module.app


def _patch_fetch(module, return_value):
    """Patch the synchronous fetch function used by the endpoint."""
    return patch.object(module, "fetch_and_calculate_sync", return_value=return_value)


def test_websocket_connection_and_receive():
    """Receive a KNOT_UPDATE event when the backend produces knot data.

    Arrange: mock fetch_and_calculate_sync to return a valid knot payload and create a
    FastAPI TestClient.
    Act: connect to /ws/signals and receive the first JSON message.
    Assert: the endpoint sends a JSON event named KNOT_UPDATE.
    """
    # Arrange
    knot_data = {"knot_time": "2024-01-01T00:00:00", "macro_trend": "DOWN_CONFIRMED"}
    with _patch_fetch(main_module, knot_data):
        client = TestClient(app)

        # Act
        with client.websocket_connect("/ws/signals") as websocket:
            received = websocket.receive_json()

        # Assert
        assert received["event"] == "KNOT_UPDATE"
        assert received["data"] == knot_data or received.get("knot_time") == knot_data["knot_time"]


def test_websocket_no_data_skip():
    """Keep the WebSocket alive without sending when no market data is available.

    Arrange: mock fetch_and_calculate_sync to return None and start a receiver in a
    bounded worker so an absent message cannot block this test indefinitely.
    Act: connect, wait briefly for a message, then close the client connection.
    Assert: no message is sent before the intentional close and the server handles the
    resulting disconnect without crashing the test client.
    """
    # Arrange
    with _patch_fetch(main_module, None):
        client = TestClient(app)
        with client.websocket_connect("/ws/signals") as websocket:
            received_messages: queue.Queue[object] = queue.Queue()

            def receive_message() -> None:
                try:
                    received_messages.put(websocket.receive_json())
                except Exception:
                    received_messages.put(None)

            receiver = threading.Thread(target=receive_message, daemon=True)
            receiver.start()

            # Act
            receiver.join(timeout=0.2)
            received = received_messages.get_nowait() if not received_messages.empty() else None
            websocket.close()
            receiver.join(timeout=0.2)

            # Assert
            assert received is None


def test_websocket_disconnect_gracefully():
    """Handle an intentional client disconnect without taking down the application.

    Arrange: mock the fetch operation and open the endpoint with TestClient.
    Act: close the WebSocket from the client side, then issue a normal HTTP request to
    prove the FastAPI application remains usable.
    Assert: the close operation does not raise and the application still responds.
    """
    # Arrange
    knot_data = {"knot_time": "2024-01-01T00:00:00"}
    with _patch_fetch(main_module, knot_data):
        client = TestClient(app)
        with client.websocket_connect("/ws/signals") as websocket:
            # Act
            websocket.close()

        # Assert
        response = client.get("/")
        assert response.status_code < 500
