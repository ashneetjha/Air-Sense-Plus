from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.health import router as health_router
from app.routes.predict import router as predict_router
from app.services.database import init_db
from app.services.model_registry import load_artifacts


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    load_artifacts()
    yield


app = FastAPI(
    title="AirSense+ API",
    version="3.0.0",
    description="Production-grade AQI prediction with SHAP explainability, attention weights, and multi-horizon forecasting.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predict_router)
app.include_router(health_router)


@app.get("/", tags=["Info"])
def root() -> dict:
    return {
        "name": "AirSense+ API",
        "version": "3.0.0",
        "status": "ok",
        "model_inputs": ["sensor_id", "co", "no2", "temperature", "humidity"],
        "endpoints": ["/predict", "/sensor-ingest", "/metrics", "/health-risk"],
        "features": ["shap_explainability", "attention_weights", "multi_horizon_forecast", "sqlite_persistence"],
    }
