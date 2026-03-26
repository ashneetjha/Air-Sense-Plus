"""Train XGBoost models — main (t+0) plus forecast horizons (t+1h, t+3h, t+6h).

Includes:
  - SHAP summary plot generation
  - Naive baseline comparison
  - Per-horizon model saving
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor

from preprocess import FEATURE_COLUMNS, PREPROCESS_METADATA_PATH, TRAIN_READY_PATH, preprocess_full_dataset

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "backend" / "app" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

XGB_MODEL_PATH = MODEL_DIR / "xgb_model.pkl"
FEATURE_METADATA_PATH = MODEL_DIR / "feature_metadata.json"
XGB_METRICS_PATH = MODEL_DIR / "xgb_metrics.json"

HORIZONS = {"t+1h": 1, "t+3h": 3, "t+6h": 6}

XGB_PARAMS = {
    "n_estimators": 400,
    "max_depth": 8,
    "learning_rate": 0.05,
    "subsample": 0.9,
    "colsample_bytree": 0.9,
    "objective": "reg:squarederror",
    "tree_method": "hist",
    "eval_metric": "rmse",
    "random_state": 42,
    "n_jobs": -1,
}


def _load_training_frame() -> tuple[pd.DataFrame, dict]:
    if TRAIN_READY_PATH.exists() and PREPROCESS_METADATA_PATH.exists():
        df = pd.read_csv(TRAIN_READY_PATH, parse_dates=["datetime"])
        metadata = json.loads(PREPROCESS_METADATA_PATH.read_text(encoding="utf-8"))
        return df, metadata
    return preprocess_full_dataset()


def _split_time_based(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    unique_times = df["datetime"].sort_values().drop_duplicates().to_list()
    split_idx = max(1, int(len(unique_times) * 0.8))
    cutoff = unique_times[split_idx - 1]
    train_df = df[df["datetime"] <= cutoff].copy()
    test_df = df[df["datetime"] > cutoff].copy()
    if test_df.empty:
        raise RuntimeError("Chronological split produced an empty test set.")
    return train_df, test_df


def _naive_baseline(y_test: pd.Series, df_test: pd.DataFrame) -> dict:
    """Naive baseline: predict aqi_lag_1 (last known value)."""
    naive_pred = df_test["aqi_lag_1"].values
    return {
        "baseline_rmse": float(np.sqrt(mean_squared_error(y_test, naive_pred))),
        "baseline_mae": float(mean_absolute_error(y_test, naive_pred)),
    }


def _train_single_model(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    target_col: str = "aqi",
    label: str = "t+0",
) -> tuple[XGBRegressor, dict]:
    X_train = train_df[FEATURE_COLUMNS]
    y_train = train_df[target_col]
    X_test = test_df[FEATURE_COLUMNS]
    y_test = test_df[target_col]

    model = XGBRegressor(**XGB_PARAMS)
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=50)

    predictions = model.predict(X_test)
    metrics = {
        "horizon": label,
        "rmse": float(np.sqrt(mean_squared_error(y_test, predictions))),
        "mae": float(mean_absolute_error(y_test, predictions)),
        "r2": float(r2_score(y_test, predictions)),
        "n_train": int(len(train_df)),
        "n_test": int(len(test_df)),
    }
    return model, metrics


def _generate_shap_plot(model: XGBRegressor, X_test: pd.DataFrame) -> None:
    try:
        import shap
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        explainer = shap.TreeExplainer(model)
        sample = X_test.sample(min(1000, len(X_test)), random_state=42)
        sv = explainer.shap_values(sample)
        shap.summary_plot(sv, sample, show=False)
        plt.tight_layout()
        plt.savefig(str(MODEL_DIR / "shap_summary.png"), dpi=150, bbox_inches="tight")
        plt.close()
        print("SHAP summary plot saved.")
    except ImportError:
        print("shap not installed — skipping SHAP summary plot.")
    except Exception as exc:
        print(f"SHAP plot generation failed: {exc}")


def train_xgb() -> dict:
    df, preprocess_metadata = _load_training_frame()
    train_df, test_df = _split_time_based(df)

    # --- Main model (t+0) ---
    model, metrics = _train_single_model(train_df, test_df, "aqi", "t+0")
    baseline = _naive_baseline(test_df["aqi"], test_df)
    metrics.update(baseline)
    metrics["model_type"] = "xgb"
    metrics["n_features"] = len(FEATURE_COLUMNS)
    metrics["feature_columns"] = FEATURE_COLUMNS
    metrics["xgb_params"] = XGB_PARAMS

    joblib.dump(model, XGB_MODEL_PATH)
    XGB_METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    # --- SHAP summary plot ---
    _generate_shap_plot(model, test_df[FEATURE_COLUMNS])

    # --- Forecast horizon models ---
    horizon_metrics = {}
    for label, shift_hours in HORIZONS.items():
        print(f"\n--- Training XGB forecast model: {label} ---")
        df_forecast = df.copy()
        df_forecast["target_future"] = (
            df_forecast.groupby("city", observed=True)["aqi"].shift(-shift_hours)
        )
        df_forecast = df_forecast.dropna(subset=["target_future"]).reset_index(drop=True)
        train_h, test_h = _split_time_based(df_forecast)
        h_model, h_metrics = _train_single_model(train_h, test_h, "target_future", label)
        tag = label.replace("+", "")
        joblib.dump(h_model, MODEL_DIR / f"xgb_model_{tag}.pkl")
        horizon_metrics[label] = h_metrics
        print(f"  {label}: RMSE={h_metrics['rmse']:.2f}, MAE={h_metrics['mae']:.2f}, R²={h_metrics['r2']:.4f}")

    metrics["horizon_metrics"] = horizon_metrics

    # --- Feature metadata ---
    FEATURE_METADATA_PATH.write_text(
        json.dumps(
            {
                "feature_columns": FEATURE_COLUMNS,
                "sequence_feature_columns": FEATURE_COLUMNS,
                "target_column": "aqi",
                "sequence_length": 12,
                "default_values": preprocess_metadata["default_values"],
                "timezone": "Asia/Kolkata",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"\n=== XGB Training Complete ===")
    print(f"  t+0: RMSE={metrics['rmse']:.2f}, MAE={metrics['mae']:.2f}, R²={metrics['r2']:.4f}")
    print(f"  Baseline (naive): RMSE={baseline['baseline_rmse']:.2f}, MAE={baseline['baseline_mae']:.2f}")
    return metrics


def main() -> None:
    print(json.dumps(train_xgb(), indent=2))


if __name__ == "__main__":
    main()
