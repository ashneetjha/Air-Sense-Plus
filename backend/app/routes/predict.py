from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import MetricsResponse, PredictionResponse, SensorIngestResponse, SensorPayload
from app.services.inference import metrics_payload, predict

router = APIRouter(tags=["Prediction"])

DEFAULT_SENSOR_PAYLOAD = SensorPayload(
    sensor_id="demo-sensor",
    co=0.7,
    no2=32.0,
    temperature=28.0,
    humidity=58.0,
)


@router.get("/predict", response_model=PredictionResponse)
def predict_default() -> PredictionResponse:
    try:
        return predict(DEFAULT_SENSOR_PAYLOAD)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/predict", response_model=PredictionResponse)
def predict_custom(payload: SensorPayload) -> PredictionResponse:
    try:
        return predict(payload)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/sensor-ingest", response_model=SensorIngestResponse)
def sensor_ingest(payload: SensorPayload) -> SensorIngestResponse:
    try:
        return SensorIngestResponse(status="ok", prediction=predict(payload))
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/metrics", response_model=MetricsResponse)
def get_metrics() -> MetricsResponse:
    return MetricsResponse(**metrics_payload())
