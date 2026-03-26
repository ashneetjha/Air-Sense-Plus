"""Core inference engine with SHAP, attention weights, forecasting, and input validation."""
from __future__ import annotations

import math
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from app import config
from app.schemas import ForecastPoint, PredictionResponse, SensorPayload
from app.services.health import classify_aqi
from app.services.history import get_aqi_history, get_feature_history, record_prediction
from app.services.model_registry import (
    get_feature_metadata,
    get_forecast_xgb_models,
    get_forecast_lstm_bundles,
    get_lstm_bundle,
    get_metrics,
    get_model_type,
    get_xgb_model,
)

try:
    import torch
except ModuleNotFoundError:  # pragma: no cover
    torch = None

try:
    from app.services.shap_utils import compute_shap_values
except Exception:  # pragma: no cover
    compute_shap_values = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

_SANE_RANGES = {
    "co": (0.0, 50.0),
    "no2": (0.0, 2000.0),
    "temperature": (-30.0, 55.0),
    "humidity": (5.0, 100.0),
}


def _validate_inputs(payload: SensorPayload) -> list[str]:
    """Return warnings for suspicious but technically valid inputs."""
    warnings: list[str] = []
    for field, (lo, hi) in _SANE_RANGES.items():
        val = getattr(payload, field)
        if math.isnan(val) or math.isinf(val):
            warnings.append(f"{field} is NaN/Inf — using default")
        elif val < lo or val > hi:
            warnings.append(f"{field}={val} outside typical range [{lo}, {hi}]")
    return warnings


def _safe_value(val: float, default: float) -> float:
    if math.isnan(val) or math.isinf(val):
        return default
    return val


# ---------------------------------------------------------------------------
# Feature construction
# ---------------------------------------------------------------------------

def _now_hour() -> int:
    return datetime.now(ZoneInfo(config.TIMEZONE)).hour


def _build_feature_row(payload: SensorPayload, sensor_id: str) -> dict[str, float]:
    metadata = get_feature_metadata()
    defaults = metadata["default_values"]
    history = get_aqi_history(sensor_id)

    lag_1 = history[-1] if len(history) >= 1 else defaults["aqi"]
    lag_3 = history[-3] if len(history) >= 3 else lag_1
    lag_6 = history[-6] if len(history) >= 6 else lag_3
    recent_3 = history[-3:] if len(history) >= 3 else [defaults["aqi"]] * 3
    recent_6 = history[-6:] if len(history) >= 6 else [defaults["aqi"]] * 6

    return {
        "co": _safe_value(float(payload.co), defaults["co"]),
        "no2": _safe_value(float(payload.no2), defaults["no2"]),
        "temperature": _safe_value(float(payload.temperature), defaults["temperature"]),
        "humidity": _safe_value(float(payload.humidity), defaults["humidity"]),
        "aqi_lag_1": float(lag_1),
        "aqi_lag_3": float(lag_3),
        "aqi_lag_6": float(lag_6),
        "aqi_roll_mean_3": float(np.mean(recent_3)),
        "aqi_roll_mean_6": float(np.mean(recent_6)),
        "hour_of_day": float(_now_hour()),
    }


# ---------------------------------------------------------------------------
# XGBoost prediction (with SHAP + forecasting)
# ---------------------------------------------------------------------------

def _predict_xgb(feature_row: dict[str, float]) -> tuple[float, dict[str, float] | None]:
    """Return (predicted_aqi, shap_values)."""
    features = get_feature_metadata()["feature_columns"]
    frame = pd.DataFrame([[feature_row[c] for c in features]], columns=features)
    model = get_xgb_model()
    prediction = float(model.predict(frame)[0])

    shap_vals = None
    if compute_shap_values is not None:
        try:
            shap_vals = compute_shap_values(model, feature_row, features)
        except Exception:
            pass

    return prediction, shap_vals


def _forecast_xgb(feature_row: dict[str, float]) -> list[ForecastPoint]:
    """Run XGB forecast models for t+1h, t+3h, t+6h if available."""
    forecast_models = get_forecast_xgb_models()
    if not forecast_models:
        return []

    features = get_feature_metadata()["feature_columns"]
    frame = pd.DataFrame([[feature_row[c] for c in features]], columns=features)
    results: list[ForecastPoint] = []

    for horizon_label, model in forecast_models.items():
        try:
            aqi = max(0.0, round(float(model.predict(frame)[0]), 2))
            cat = classify_aqi(aqi).category
            results.append(ForecastPoint(horizon=horizon_label, predicted_aqi=aqi, category=cat))
        except Exception:
            pass

    return results


# ---------------------------------------------------------------------------
# LSTM prediction (with attention weights + forecasting)
# ---------------------------------------------------------------------------

def _build_lstm_sequence(feature_row: dict[str, float], sensor_id: str, bundle: dict) -> np.ndarray:
    """Build the scaled (1, seq_len, n_features) tensor for LSTM inference."""
    metadata = get_feature_metadata()
    defaults = metadata["default_values"]
    sequence_features = metadata["sequence_feature_columns"]
    history_rows = get_feature_history(sensor_id)

    default_row = {
        "co": defaults["co"],
        "no2": defaults["no2"],
        "temperature": defaults["temperature"],
        "humidity": defaults["humidity"],
        "aqi_lag_1": defaults["aqi"],
        "aqi_lag_3": defaults["aqi"],
        "aqi_lag_6": defaults["aqi"],
        "aqi_roll_mean_3": defaults["aqi_roll_mean_3"],
        "aqi_roll_mean_6": defaults["aqi_roll_mean_6"],
        "hour_of_day": feature_row["hour_of_day"],
    }
    sequence_rows = history_rows[-(bundle["sequence_length"] - 1):] + [feature_row]
    while len(sequence_rows) < bundle["sequence_length"]:
        sequence_rows.insert(0, dict(default_row))

    sequence = np.asarray(
        [[row[c] for c in sequence_features] for row in sequence_rows],
        dtype=np.float32,
    )
    return bundle["feature_scaler"].transform(sequence).astype(np.float32)


def _predict_lstm(feature_row: dict[str, float], sensor_id: str) -> tuple[float, list[float] | None]:
    """Return (predicted_aqi, attention_weights)."""
    if torch is None:
        raise RuntimeError("PyTorch is not installed; LSTM inference is unavailable.")

    bundle = get_lstm_bundle()
    scaled = _build_lstm_sequence(feature_row, sensor_id, bundle)
    tensor = torch.from_numpy(scaled).unsqueeze(0)

    with torch.no_grad():
        prediction_scaled, attn_weights = bundle["model"](tensor)

    prediction = bundle["target_scaler"].inverse_transform(prediction_scaled.numpy()).ravel()[0]
    weights = attn_weights.squeeze(0).tolist() if attn_weights is not None else None
    return float(prediction), weights


def _forecast_lstm(feature_row: dict[str, float], sensor_id: str) -> list[ForecastPoint]:
    """Run LSTM forecast models for t+1h, t+3h, t+6h if available."""
    if torch is None:
        return []

    forecast_bundles = get_forecast_lstm_bundles()
    if not forecast_bundles:
        return []

    results: list[ForecastPoint] = []
    for horizon_label, bundle in forecast_bundles.items():
        try:
            scaled = _build_lstm_sequence(feature_row, sensor_id, bundle)
            tensor = torch.from_numpy(scaled).unsqueeze(0)
            with torch.no_grad():
                pred_scaled, _ = bundle["model"](tensor)
            aqi = max(0.0, round(
                float(bundle["target_scaler"].inverse_transform(pred_scaled.numpy()).ravel()[0]), 2
            ))
            cat = classify_aqi(aqi).category
            results.append(ForecastPoint(horizon=horizon_label, predicted_aqi=aqi, category=cat))
        except Exception:
            pass

    return results


# ---------------------------------------------------------------------------
# Main predict entrypoint
# ---------------------------------------------------------------------------

def predict(payload: SensorPayload) -> PredictionResponse:
    warnings = _validate_inputs(payload)
    feature_row = _build_feature_row(payload, payload.sensor_id)
    model_type = get_model_type()

    shap_vals = None
    attn_weights = None
    top_features = None

    if model_type == "xgb":
        predicted_aqi, shap_vals = _predict_xgb(feature_row)
        forecasts = _forecast_xgb(feature_row)
        if shap_vals:
            sorted_feats = sorted(shap_vals.items(), key=lambda x: abs(x[1]), reverse=True)
            top_features = [f[0] for f in sorted_feats[:3]]
    else:
        predicted_aqi, attn_weights = _predict_lstm(feature_row, payload.sensor_id)
        forecasts = _forecast_lstm(feature_row, payload.sensor_id)
        if attn_weights:
            features = get_feature_metadata()["feature_columns"]
            # top timesteps (most attended)
            top_indices = sorted(range(len(attn_weights)), key=lambda i: attn_weights[i], reverse=True)[:3]
            top_features = [f"t-{len(attn_weights) - 1 - i}" for i in top_indices]

    predicted_aqi = max(0.0, round(float(predicted_aqi), 2))
    category = classify_aqi(predicted_aqi)
    record_prediction(payload.sensor_id, feature_row, predicted_aqi)

    return PredictionResponse(
        predicted_aqi=predicted_aqi,
        category=category.category,
        model_type=model_type,
        shap_values=shap_vals,
        attention_weights=attn_weights,
        top_features=top_features,
        forecasts=forecasts,
        warnings=warnings,
    )


def metrics_payload() -> dict:
    metrics = get_metrics().copy()
    metrics.setdefault("model_type", get_model_type())
    return metrics
