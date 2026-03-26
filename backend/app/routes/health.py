from __future__ import annotations

from fastapi import APIRouter, Query

from app.schemas import HealthRisk
from app.services.health import classify_aqi

router = APIRouter(tags=["Health"])


@router.get("/health-risk", response_model=HealthRisk)
def health_risk(aqi: float = Query(..., ge=0)) -> HealthRisk:
    return classify_aqi(aqi)
