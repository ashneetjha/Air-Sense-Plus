from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SensorPayload(BaseModel):
    sensor_id: str = Field(..., min_length=1, max_length=128)
    co: float = Field(..., ge=0, le=100)
    no2: float = Field(..., ge=0, le=5000)
    temperature: float = Field(..., ge=-40, le=70)
    humidity: float = Field(..., ge=0, le=100)


class ForecastPoint(BaseModel):
    horizon: str  # e.g. "t+1h", "t+3h", "t+6h"
    predicted_aqi: float
    category: Literal["Good", "Moderate", "Unhealthy", "Hazardous"]


class PredictionResponse(BaseModel):
    predicted_aqi: float
    category: Literal["Good", "Moderate", "Unhealthy", "Hazardous"]
    model_type: Literal["xgb", "lstm"]
    shap_values: dict[str, float] | None = None
    attention_weights: list[float] | None = None
    top_features: list[str] | None = None
    forecasts: list[ForecastPoint] = []
    warnings: list[str] = []


class SensorIngestResponse(BaseModel):
    status: str
    prediction: PredictionResponse


class HealthRisk(BaseModel):
    category: Literal["Good", "Moderate", "Unhealthy", "Hazardous"]
    color: str
    aqi_range: str
    advisory: str


class MetricsResponse(BaseModel):
    model_type: Literal["xgb", "lstm"]
    rmse: float = 0.0
    mae: float = 0.0
    r2: float = 0.0
    n_train: int = 0
    n_test: int = 0
    n_features: int = 0
    feature_columns: list[str] = []
    baseline_rmse: float | None = None
    baseline_mae: float | None = None
