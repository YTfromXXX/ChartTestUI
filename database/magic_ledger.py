"""SQLite ledger for court-card promotion events and extracted mana."""

from __future__ import annotations

from datetime import datetime, timezone
import sqlite3
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