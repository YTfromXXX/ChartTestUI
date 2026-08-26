"""SQLite ledger for court-card promotion events and extracted mana."""

from __future__ import annotations

from datetime import datetime, timezone
import sqlite3
from uuid import uuid4
from pathlib import Path
from typing import Any


class MagicLedgerDB:
    """Persist promotion observations and maintain one mana balance per element."""

    ELEMENTS = ("FIRE", "WATER", "AIR", "EARTH", "METAL")

    def __init__(self, db_path: str | Path = "magic_ledger.db") -> None:
        self.db_path = str(db_path)
        self.initialize_tables()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize_tables(self) -> None:
        """Create the grimoire and mana pool tables, including empty elements."""
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS grimoire_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    wuxing_phase TEXT,
                    hexagram TEXT,
                    promoted_card TEXT NOT NULL,
                    s15_volume REAL NOT NULL,
                    s15_delta REAL NOT NULL,
                    generated_mana INTEGER NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS mana_pool (
                    element TEXT PRIMARY KEY,
                    current_mana INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS magic_casts (
                    cast_id TEXT PRIMARY KEY,
                    element TEXT NOT NULL,
                    mana_cost INTEGER NOT NULL,
                    target_symbol TEXT NOT NULL,
                    message TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                )
                """
            )
            connection.executemany(
                "INSERT OR IGNORE INTO mana_pool (element, current_mana) VALUES (?, 0)",
                ((element,) for element in self.ELEMENTS),
            )

    @staticmethod
    def _required_number(data_dict: dict[str, Any], key: str) -> float:
        try:
            return float(data_dict[key])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"{key} must be a numeric value") from error

    def record_promotion_and_extract_mana(self, data_dict: dict[str, Any]) -> dict[str, Any]:
        """Record one promotion, add its mana to the mapped element, and return its incantation."""
        symbol = str(data_dict.get("symbol", "")).strip()
        element = str(data_dict.get("element", "")).strip().upper()
        promoted_card = str(data_dict.get("promoted_card", "")).strip().upper()
        if not symbol or not promoted_card:
            raise ValueError("symbol and promoted_card are required")
        if element not in self.ELEMENTS:
            raise ValueError(f"element must be one of {', '.join(self.ELEMENTS)}")

        s15_volume = self._required_number(data_dict, "s15_volume")
        s15_delta = self._required_number(data_dict, "s15_delta")
        generated_mana = int((s15_volume * 0.1) + abs(s15_delta * 10))
        timestamp = str(data_dict.get("timestamp") or datetime.now(timezone.utc).isoformat())
        wuxing_phase = str(data_dict.get("wuxing_phase") or "UNKNOWN")
        hexagram = str(data_dict.get("hexagram") or data_dict.get("hexagram_binary") or "UNKNOWN")
        incantation = (
            f"魔術師の空間にて乱気流を観測。易経『{hexagram}』の魔力を抽出し、"
            f"{element}のManaが{generated_mana}増加。{promoted_card}が進軍を開始する。"
        )

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO grimoire_logs
                    (timestamp, symbol, wuxing_phase, hexagram, promoted_card,
                     s15_volume, s15_delta, generated_mana)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (timestamp, symbol, wuxing_phase, hexagram, promoted_card,
                 s15_volume, s15_delta, generated_mana),
            )
            connection.execute(
                "UPDATE mana_pool SET current_mana = current_mana + ? WHERE element = ?",
                (generated_mana, element),
            )

        return {
            "symbol": symbol,
            "element": element,
            "promoted_card": promoted_card,
            "generated_mana": generated_mana,
            "incantation": incantation,
            "message": incantation,
        }

    def consume_mana(self, element: str, mana_cost: int) -> int | None:
        """Atomically consume mana and return the remaining balance, if affordable."""
        normalized_element = str(element).strip().upper()
        if normalized_element not in self.ELEMENTS:
            raise ValueError(f"element must be one of {', '.join(self.ELEMENTS)}")
        if mana_cost <= 0:
            raise ValueError("mana_cost must be greater than zero")

        with self._connect() as connection:
            updated = connection.execute(
                """
                UPDATE mana_pool
                SET current_mana = current_mana - ?
                WHERE element = ? AND current_mana >= ?
                """,
                (mana_cost, normalized_element, mana_cost),
            ).rowcount
            if updated == 0:
                return None

            remaining = connection.execute(
                "SELECT current_mana FROM mana_pool WHERE element = ?",
                (normalized_element,),
            ).fetchone()

        return int(remaining["current_mana"])

    def begin_cast(self, element: str, mana_cost: int, target_symbol: str, message: str) -> tuple[str, int] | None:
        """Reserve mana and persist a PENDING cast in one transaction."""
        normalized_element = str(element).strip().upper()
        if normalized_element not in self.ELEMENTS:
            raise ValueError(f"element must be one of {', '.join(self.ELEMENTS)}")
        if mana_cost <= 0:
            raise ValueError("mana_cost must be greater than zero")
        cast_id = str(uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            updated = connection.execute(
                "UPDATE mana_pool SET current_mana = current_mana - ? WHERE element = ? AND current_mana >= ?",
                (mana_cost, normalized_element, mana_cost),
            ).rowcount
            if updated == 0:
                return None
            remaining = connection.execute(
                "SELECT current_mana FROM mana_pool WHERE element = ?", (normalized_element,)
            ).fetchone()["current_mana"]
            connection.execute(
                "INSERT INTO magic_casts (cast_id, element, mana_cost, target_symbol, message, status, created_at) VALUES (?, ?, ?, ?, ?, 'PENDING', ?)",
                (cast_id, normalized_element, mana_cost, target_symbol, message, timestamp),
            )
        return cast_id, int(remaining)

    def complete_cast(self, cast_id: str, status: str) -> None:
        """Mark a pending cast as SUCCESS or FAILED."""
        if status not in {"SUCCESS", "FAILED"}:
            raise ValueError("status must be SUCCESS or FAILED")
        with self._connect() as connection:
            updated = connection.execute(
                "UPDATE magic_casts SET status = ?, completed_at = ? WHERE cast_id = ? AND status = 'PENDING'",
                (status, datetime.now(timezone.utc).isoformat(), cast_id),
            ).rowcount
            if updated != 1:
                raise ValueError("cast is missing or already completed")

    def rollback_cast(self, cast_id: str) -> int:
        """Return reserved mana and mark a pending cast FAILED atomically."""
        with self._connect() as connection:
            cast = connection.execute(
                "SELECT element, mana_cost FROM magic_casts WHERE cast_id = ? AND status = 'PENDING'",
                (cast_id,),
            ).fetchone()
            if cast is None:
                raise ValueError("cast is missing or already completed")
            connection.execute(
                "UPDATE mana_pool SET current_mana = current_mana + ? WHERE element = ?",
                (cast["mana_cost"], cast["element"]),
            )
            connection.execute(
                "UPDATE magic_casts SET status = 'FAILED', completed_at = ? WHERE cast_id = ?",
                (datetime.now(timezone.utc).isoformat(), cast_id),
            )
            remaining = connection.execute(
                "SELECT current_mana FROM mana_pool WHERE element = ?", (cast["element"],)
            ).fetchone()["current_mana"]
        return int(remaining)