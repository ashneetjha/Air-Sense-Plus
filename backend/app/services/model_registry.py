"""Model registry — loads and serves all ML artifacts (XGB, LSTM, forecast models)."""
from __future__ import annotations

import json
from pathlib import Path

import joblib

from app import config

try:
    import torch
except ModuleNotFoundError:  # pragma: no cover
    torch = None

_xgb_model = None
_lstm_bundle: dict | None = None
_feature_metadata: dict = {}
_metrics: dict[str, dict] = {}
_forecast_xgb: dict[str, object] = {}  # {"t+1h": model, "t+3h": model, "t+6h": model}
_forecast_lstm: dict[str, dict] = {}    # {"t+1h": bundle, ...}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def load_artifacts() -> None:
    global _xgb_model, _lstm_bundle, _feature_metadata, _metrics, _forecast_xgb, _forecast_lstm
    _feature_metadata = _load_json(config.FEATURE_METADATA_PATH)
    _metrics = {"xgb": _load_json(config.XGB_METRICS_PATH), "lstm": _load_json(config.LSTM_METRICS_PATH)}

    # --- Main XGB model ---
    if config.XGB_MODEL_PATH.exists():
        _xgb_model = joblib.load(config.XGB_MODEL_PATH)

    # --- Forecast XGB models ---
    _forecast_xgb.clear()
    for horizon in ("t+1h", "t+3h", "t+6h"):
        path = config.MODELS_DIR / f"xgb_model_{horizon.replace('+', '')}.pkl"
        if path.exists():
            _forecast_xgb[horizon] = joblib.load(path)

    # --- Main LSTM model ---
    if config.LSTM_MODEL_PATH.exists() and config.LSTM_SCALERS_PATH.exists() and torch is not None:
        from app.services.lstm_model import LSTMAttentionRegressor

        checkpoint = torch.load(config.LSTM_MODEL_PATH, map_location="cpu", weights_only=True)
        model = LSTMAttentionRegressor(checkpoint["input_size"], checkpoint["hidden_size"])
        model.load_state_dict(checkpoint["state_dict"])
        model.eval()
        scalers = joblib.load(config.LSTM_SCALERS_PATH)
        _lstm_bundle = {
            "model": model,
            "feature_scaler": scalers["feature_scaler"],
            "target_scaler": scalers["target_scaler"],
            "sequence_length": checkpoint["sequence_length"],
        }

    # --- Forecast LSTM models ---
    _forecast_lstm.clear()
    if torch is not None:
        from app.services.lstm_model import LSTMAttentionRegressor

        for horizon in ("t+1h", "t+3h", "t+6h"):
            tag = horizon.replace("+", "")
            pt_path = config.MODELS_DIR / f"lstm_model_{tag}.pt"
            sc_path = config.MODELS_DIR / f"lstm_scalers_{tag}.pkl"
            if pt_path.exists() and sc_path.exists():
                cp = torch.load(pt_path, map_location="cpu", weights_only=True)
                m = LSTMAttentionRegressor(cp["input_size"], cp["hidden_size"])
                m.load_state_dict(cp["state_dict"])
                m.eval()
                sc = joblib.load(sc_path)
                _forecast_lstm[horizon] = {
                    "model": m,
                    "feature_scaler": sc["feature_scaler"],
                    "target_scaler": sc["target_scaler"],
                    "sequence_length": cp["sequence_length"],
                }


def get_model_type() -> str:
    if config.MODEL_TYPE not in {"xgb", "lstm"}:
        raise RuntimeError("MODEL_TYPE must be either 'xgb' or 'lstm'.")
    return config.MODEL_TYPE


def get_feature_metadata() -> dict:
    if not _feature_metadata:
        raise RuntimeError("Feature metadata not loaded. Train the model artifacts first.")
    return _feature_metadata


def get_metrics() -> dict:
    return _metrics.get(get_model_type(), {})


def get_xgb_model():
    if _xgb_model is None:
        raise FileNotFoundError(f"Missing XGBoost artifact at {config.XGB_MODEL_PATH}")
    return _xgb_model


def get_lstm_bundle() -> dict:
    if _lstm_bundle is None:
        raise FileNotFoundError(
            f"Missing LSTM artifacts at {config.LSTM_MODEL_PATH} and {config.LSTM_SCALERS_PATH}"
        )
    return _lstm_bundle


def get_forecast_xgb_models() -> dict[str, object]:
    return _forecast_xgb


def get_forecast_lstm_bundles() -> dict[str, dict]:
    return _forecast_lstm
