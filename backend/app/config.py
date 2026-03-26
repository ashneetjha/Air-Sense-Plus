from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_TYPE = os.getenv("MODEL_TYPE", "xgb").strip().lower()
TIMEZONE = os.getenv("AIRSENSE_TIMEZONE", "Asia/Kolkata")

XGB_MODEL_PATH = MODELS_DIR / "xgb_model.pkl"
LSTM_MODEL_PATH = MODELS_DIR / "lstm_model.pt"
LSTM_SCALERS_PATH = MODELS_DIR / "lstm_scalers.pkl"
FEATURE_METADATA_PATH = MODELS_DIR / "feature_metadata.json"
XGB_METRICS_PATH = MODELS_DIR / "xgb_metrics.json"
LSTM_METRICS_PATH = MODELS_DIR / "lstm_metrics.json"
