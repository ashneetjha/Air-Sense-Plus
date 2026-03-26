"""SQLite persistence layer for sensor readings and prediction history.

Replaces the in-memory deque history so data survives restarts.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from app import config

DB_PATH = Path(config.BASE_DIR) / "airsense.db"

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    """One connection per thread (SQLite is not thread-safe by default)."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        _local.conn = conn
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    conn = _get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_id   TEXT    NOT NULL,
            timestamp   TEXT    NOT NULL,
            co          REAL    NOT NULL,
            no2         REAL    NOT NULL,
            temperature REAL    NOT NULL,
            humidity    REAL    NOT NULL,
            predicted_aqi REAL  NOT NULL,
            feature_json TEXT   NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_sensor_ts
            ON sensor_readings(sensor_id, timestamp DESC);
        """
    )
    conn.commit()


def insert_reading(
    sensor_id: str,
    feature_row: dict[str, float],
    predicted_aqi: float,
) -> None:
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO sensor_readings
            (sensor_id, timestamp, co, no2, temperature, humidity, predicted_aqi, feature_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            sensor_id,
            now,
            feature_row.get("co", 0.0),
            feature_row.get("no2", 0.0),
            feature_row.get("temperature", 0.0),
            feature_row.get("humidity", 0.0),
            predicted_aqi,
            json.dumps(feature_row),
        ),
    )
    conn.commit()


def get_recent_aqi(sensor_id: str, limit: int = 6) -> list[float]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT predicted_aqi FROM sensor_readings WHERE sensor_id = ? ORDER BY timestamp DESC LIMIT ?",
        (sensor_id, limit),
    ).fetchall()
    return [r["predicted_aqi"] for r in reversed(rows)]


def get_recent_features(sensor_id: str, limit: int = 12) -> list[dict[str, float]]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT feature_json FROM sensor_readings WHERE sensor_id = ? ORDER BY timestamp DESC LIMIT ?",
        (sensor_id, limit),
    ).fetchall()
    return [json.loads(r["feature_json"]) for r in reversed(rows)]
