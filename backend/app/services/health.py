from __future__ import annotations

from app.schemas import HealthRisk

AQI_BANDS = [
    ("Good", 50.0, "#1f9d55", "0-50", "Air quality is acceptable for normal outdoor activity."),
    ("Moderate", 100.0, "#e0a800", "51-100", "Sensitive people should reduce prolonged outdoor exertion."),
    ("Unhealthy", 200.0, "#d9480f", "101-200", "Limit outdoor activity and use masks if exposure is unavoidable."),
    ("Hazardous", float("inf"), "#b02a37", "200+", "Avoid outdoor exposure and keep indoor air protected."),
]


def classify_aqi(aqi_value: float) -> HealthRisk:
    value = max(0.0, float(aqi_value))
    for category, max_value, color, aqi_range, advisory in AQI_BANDS:
        if value <= max_value:
            return HealthRisk(category=category, color=color, aqi_range=aqi_range, advisory=advisory)
    return HealthRisk(category="Hazardous", color="#b02a37", aqi_range="200+", advisory="Avoid exposure.")
