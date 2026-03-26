"""SHAP explainability utilities for XGBoost predictions."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

try:
    import shap
except ModuleNotFoundError:  # pragma: no cover
    shap = None  # type: ignore[assignment]

from app import config


def compute_shap_values(
    model,
    feature_row: dict[str, float],
    feature_columns: list[str],
) -> dict[str, float] | None:
    """Return per-feature SHAP values for a single XGBoost prediction."""
    if shap is None:
        return None
    frame = pd.DataFrame([[feature_row[c] for c in feature_columns]], columns=feature_columns)
    explainer = shap.TreeExplainer(model)
    sv = explainer.shap_values(frame)
    values = sv[0] if isinstance(sv, np.ndarray) else np.asarray(sv)[0]
    return {col: round(float(v), 4) for col, v in zip(feature_columns, values)}


def generate_shap_summary_plot(
    model,
    X_test: pd.DataFrame,
    output_path: Path | None = None,
) -> Path:
    """Generate and save a SHAP summary plot (beeswarm) for the XGBoost model."""
    if shap is None:
        raise RuntimeError("shap package is required. Install with: pip install shap")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    explainer = shap.TreeExplainer(model)
    sv = explainer.shap_values(X_test.sample(min(1000, len(X_test)), random_state=42))
    save_path = output_path or (config.MODELS_DIR / "shap_summary.png")
    shap.summary_plot(sv, X_test.sample(min(1000, len(X_test)), random_state=42), show=False)
    plt.tight_layout()
    plt.savefig(str(save_path), dpi=150, bbox_inches="tight")
    plt.close()
    return save_path
