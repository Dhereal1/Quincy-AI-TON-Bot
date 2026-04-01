import os
import sqlite3
import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class Alert:
    chat_id: int
    target_price: float
    initial_price: float
    direction: str


class AlertStore:
    def __init__(self, db_path: str):
        self._db_path = db_path
        self._lock = threading.Lock()
        directory = os.path.dirname(self._db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        self._connection = sqlite3.connect(self._db_path, check_same_thread=False, timeout=30)
        self._connection.row_factory = sqlite3.Row
        self._initialize()

    def _initialize(self) -> None:
        with self._lock:
            with self._connection:
                self._connection.execute("PRAGMA journal_mode=WAL")
                self._connection.execute("PRAGMA synchronous=NORMAL")
                self._connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS alerts (
                        chat_id INTEGER PRIMARY KEY,
                        target_price REAL NOT NULL,
                        initial_price REAL NOT NULL,
                        direction TEXT NOT NULL CHECK(direction IN ('above', 'below')),
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

    def upsert_alert(self, alert: Alert) -> None:
        with self._lock:
            with self._connection:
                self._connection.execute(
                    """
                    INSERT INTO alerts (chat_id, target_price, initial_price, direction)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(chat_id) DO UPDATE SET
                        target_price = excluded.target_price,
                        initial_price = excluded.initial_price,
                        direction = excluded.direction
                    """,
                    (alert.chat_id, alert.target_price, alert.initial_price, alert.direction),
                )

    def list_alerts(self) -> list[Alert]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT chat_id, target_price, initial_price, direction FROM alerts"
            ).fetchall()
        return [
            Alert(
                chat_id=row["chat_id"],
                target_price=row["target_price"],
                initial_price=row["initial_price"],
                direction=row["direction"],
            )
            for row in rows
        ]

    def delete_alerts(self, chat_ids: list[int]) -> None:
        if not chat_ids:
            return
        placeholders = ",".join("?" for _ in chat_ids)
        with self._lock:
            with self._connection:
                self._connection.execute(
                    f"DELETE FROM alerts WHERE chat_id IN ({placeholders})",
                    chat_ids,
                )
