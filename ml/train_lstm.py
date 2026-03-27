"""Train LSTM+Attention models — main (t+0) plus forecast horizons (t+1h, t+3h, t+6h).

Includes:
  - Real sequence input with proper attention
  - Naive baseline comparison
  - Per-horizon model saving
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

from preprocess import FEATURE_COLUMNS, PREPROCESS_METADATA_PATH, TRAIN_READY_PATH, preprocess_full_dataset

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, TensorDataset
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit(
        "PyTorch is required for ml/train_lstm.py. Install torch before training the LSTM model."
    ) from exc

from app.services.lstm_model import LSTMAttentionRegressor  # noqa: E402

MODEL_DIR = ROOT / "backend" / "app" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

LSTM_MODEL_PATH = MODEL_DIR / "lstm_model.pt"
LSTM_SCALERS_PATH = MODEL_DIR / "lstm_scalers.pkl"
LSTM_METRICS_PATH = MODEL_DIR / "lstm_metrics.json"
FEATURE_METADATA_PATH = MODEL_DIR / "feature_metadata.json"

SEQUENCE_LENGTH = 12
BATCH_SIZE = 256
EPOCHS = 5
LEARNING_RATE = 1e-3
HORIZONS = {"t+1h": 1, "t+3h": 3, "t+6h": 6}


def _load_training_frame() -> tuple[pd.DataFrame, dict]:
    if TRAIN_READY_PATH.exists() and PREPROCESS_METADATA_PATH.exists():
        df = pd.read_csv(TRAIN_READY_PATH, parse_dates=["datetime"])
        metadata = json.loads(PREPROCESS_METADATA_PATH.read_text(encoding="utf-8"))
        return df, metadata
    return preprocess_full_dataset()


def _build_sequences(
    df: pd.DataFrame,
    target_col: str = "aqi",
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    unique_times = df["datetime"].sort_values().drop_duplicates().to_list()
    split_idx = max(1, int(len(unique_times) * 0.8))
    cutoff = unique_times[split_idx - 1]

    sequences: list[np.ndarray] = []
    targets: list[float] = []
    is_train_flags: list[bool] = []

    for _, group in df.groupby("city", observed=True):
        group = group.sort_values("datetime").reset_index(drop=True)
        feature_values = group[FEATURE_COLUMNS].to_numpy(dtype=np.float32, copy=False)
        target_values = group[target_col].to_numpy(dtype=np.float32, copy=False)
        datetimes = group["datetime"].to_numpy()

        for idx in range(SEQUENCE_LENGTH - 1, len(group)):
            if np.isnan(target_values[idx]):
                continue
            sequences.append(feature_values[idx - SEQUENCE_LENGTH + 1 : idx + 1])
            targets.append(float(target_values[idx]))
            is_train_flags.append(bool(datetimes[idx] <= cutoff.to_datetime64()))

    return (
        np.stack(sequences).astype(np.float32),
        np.asarray(targets, dtype=np.float32),
        np.asarray(is_train_flags, dtype=bool),
    )


def _train_single_lstm(
    df: pd.DataFrame,
    target_col: str,
    label: str,
) -> tuple[LSTMAttentionRegressor, StandardScaler, StandardScaler, dict]:
    X, y, train_mask = _build_sequences(df, target_col)

    X_train, X_val = X[train_mask], X[~train_mask]
    y_train, y_val = y[train_mask], y[~train_mask]
    if len(X_val) == 0:
        raise RuntimeError(f"Chronological split produced an empty validation set for {label}.")

    feature_scaler = StandardScaler()
    target_scaler = StandardScaler()
    X_train_scaled = feature_scaler.fit_transform(X_train.reshape(-1, X_train.shape[-1])).reshape(X_train.shape).astype(np.float32)
    X_val_scaled = feature_scaler.transform(X_val.reshape(-1, X_val.shape[-1])).reshape(X_val.shape).astype(np.float32)
    y_train_scaled = target_scaler.fit_transform(y_train.reshape(-1, 1)).astype(np.float32)

    train_loader = DataLoader(
        TensorDataset(torch.from_numpy(X_train_scaled), torch.from_numpy(y_train_scaled)),
        batch_size=BATCH_SIZE,
        shuffle=True,
    )
    val_loader = DataLoader(
        TensorDataset(torch.from_numpy(X_val_scaled), torch.from_numpy(np.zeros((len(X_val), 1), dtype=np.float32))),
        batch_size=BATCH_SIZE,
        shuffle=False,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = LSTMAttentionRegressor(input_size=len(FEATURE_COLUMNS), hidden_size=64).to(device)
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)

    for epoch in range(EPOCHS):
        model.train()
        epoch_loss = 0.0
        n_batches = 0
        for batch_x, batch_y in train_loader:
            batch_x = batch_x.to(device)
            batch_y = batch_y.to(device)
            optimizer.zero_grad(set_to_none=True)
            preds, _ = model(batch_x)
            loss = criterion(preds, batch_y)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
            n_batches += 1
        avg_loss = epoch_loss / max(n_batches, 1)
        print(f"  [{label}] epoch={epoch + 1}/{EPOCHS}, loss={avg_loss:.4f}")

    model.eval()
    predictions_scaled: list[np.ndarray] = []
    with torch.no_grad():
        for batch_x, _ in val_loader:
            preds, _ = model(batch_x.to(device))
            predictions_scaled.append(preds.cpu().numpy())

    predictions = target_scaler.inverse_transform(np.vstack(predictions_scaled)).ravel()

    # Naive baseline: persist previous AQI using lag-1 from the last timestep.
    lag_idx = FEATURE_COLUMNS.index("aqi_lag_1")
    naive_pred = X_val[:, -1, lag_idx]
    baseline_rmse = float(np.sqrt(mean_squared_error(y_val, naive_pred)))
    baseline_mae = float(mean_absolute_error(y_val, naive_pred))

    metrics = {
        "horizon": label,
        "rmse": float(np.sqrt(mean_squared_error(y_val, predictions))),
        "mae": float(mean_absolute_error(y_val, predictions)),
        "r2": float(r2_score(y_val, predictions)),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_val)),
        "baseline_rmse": baseline_rmse,
        "baseline_mae": baseline_mae,
    }
    return model.cpu(), feature_scaler, target_scaler, metrics


def train_lstm() -> dict:
    df, preprocess_metadata = _load_training_frame()

    # --- Main model (t+0) ---
    print("--- Training LSTM main model (t+0) ---")
    model, feature_scaler, target_scaler, metrics = _train_single_lstm(df, "aqi", "t+0")
    metrics["model_type"] = "lstm"
    metrics["n_features"] = len(FEATURE_COLUMNS)
    metrics["feature_columns"] = FEATURE_COLUMNS
    metrics["sequence_length"] = SEQUENCE_LENGTH
    metrics["epochs"] = EPOCHS

    torch.save(
        {
            "state_dict": model.state_dict(),
            "input_size": len(FEATURE_COLUMNS),
            "hidden_size": 64,
            "sequence_length": SEQUENCE_LENGTH,
        },
        LSTM_MODEL_PATH,
    )
    joblib.dump({"feature_scaler": feature_scaler, "target_scaler": target_scaler}, LSTM_SCALERS_PATH)
    LSTM_METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print(f"  t+0: RMSE={metrics['rmse']:.2f}, MAE={metrics['mae']:.2f}, R²={metrics['r2']:.4f}")

    # --- Forecast horizon models ---
    horizon_metrics = {}
    for label, shift_hours in HORIZONS.items():
        print(f"\n--- Training LSTM forecast model: {label} ---")
        df_forecast = df.copy()
        df_forecast["target_future"] = (
            df_forecast.groupby("city", observed=True)["aqi"].shift(-shift_hours)
        )
        df_forecast = df_forecast.dropna(subset=["target_future"]).reset_index(drop=True)

        h_model, h_fs, h_ts, h_metrics = _train_single_lstm(df_forecast, "target_future", label)
        tag = label.replace("+", "")
        torch.save(
            {
                "state_dict": h_model.state_dict(),
                "input_size": len(FEATURE_COLUMNS),
                "hidden_size": 64,
                "sequence_length": SEQUENCE_LENGTH,
            },
            MODEL_DIR / f"lstm_model_{tag}.pt",
        )
        joblib.dump({"feature_scaler": h_fs, "target_scaler": h_ts}, MODEL_DIR / f"lstm_scalers_{tag}.pkl")
        horizon_metrics[label] = h_metrics
        print(f"  {label}: RMSE={h_metrics['rmse']:.2f}, MAE={h_metrics['mae']:.2f}, R²={h_metrics['r2']:.4f}")

    metrics["horizon_metrics"] = horizon_metrics

    # --- Feature metadata ---
    existing_metadata = json.loads(FEATURE_METADATA_PATH.read_text(encoding="utf-8")) if FEATURE_METADATA_PATH.exists() else {}
    existing_metadata.update(
        {
            "feature_columns": FEATURE_COLUMNS,
            "sequence_feature_columns": FEATURE_COLUMNS,
            "target_column": "aqi",
            "sequence_length": SEQUENCE_LENGTH,
            "default_values": preprocess_metadata["default_values"],
            "timezone": "Asia/Kolkata",
        }
    )
    FEATURE_METADATA_PATH.write_text(json.dumps(existing_metadata, indent=2), encoding="utf-8")

    print(f"\n=== LSTM Training Complete ===")
    return metrics


def main() -> None:
    print(json.dumps(train_lstm(), indent=2))


if __name__ == "__main__":
    main()
