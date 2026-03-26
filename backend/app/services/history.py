"""Sensor history backed by SQLite.

Public API is unchanged from the original in-memory version so that
``inference.py`` does not need import changes.
"""
from __future__ import annotations

from app.services.database import get_recent_aqi, get_recent_features, insert_reading


def get_aqi_history(sensor_id: str) -> list[float]:
    return get_recent_aqi(sensor_id, limit=6)


def get_feature_history(sensor_id: str) -> list[dict[str, float]]:
    return get_recent_features(sensor_id, limit=12)


def record_prediction(sensor_id: str, feature_row: dict[str, float], predicted_aqi: float) -> None:
    insert_reading(sensor_id, feature_row, predicted_aqi)
