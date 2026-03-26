from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Iterable
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_PATH = ROOT / "data" / "raw" / "city_hour.csv"
WEATHER_CACHE_DIR = ROOT / "data" / "raw" / "weather"
PROCESSED_DIR = ROOT / "data" / "processed"
TRAIN_READY_PATH = PROCESSED_DIR / "train_ready.csv"
PREPROCESS_METADATA_PATH = PROCESSED_DIR / "preprocess_metadata.json"

REQUIRED_RAW_COLUMNS = {
    "City": "city",
    "Datetime": "datetime",
    "CO": "co",
    "NO2": "no2",
    "AQI": "aqi",
    "PM2.5": "pm25",
    "PM10": "pm10",
    "O3": "o3",
}

FEATURE_COLUMNS = [
    "co",
    "no2",
    "temperature",
    "humidity",
    "aqi_lag_1",
    "aqi_lag_3",
    "aqi_lag_6",
    "aqi_roll_mean_3",
    "aqi_roll_mean_6",
    "hour_of_day",
]

CITY_COORDINATES: dict[str, tuple[float, float]] = {
    "Ahmedabad": (23.0225, 72.5714),
    "Aizawl": (23.7271, 92.7176),
    "Amaravati": (16.5062, 80.6480),
    "Amritsar": (31.6340, 74.8723),
    "Bengaluru": (12.9716, 77.5946),
    "Bhopal": (23.2599, 77.4126),
    "Brajrajnagar": (21.8167, 83.9167),
    "Chandigarh": (30.7333, 76.7794),
    "Chennai": (13.0827, 80.2707),
    "Coimbatore": (11.0168, 76.9558),
    "Delhi": (28.6139, 77.2090),
    "Ernakulam": (9.9816, 76.2999),
    "Gurugram": (28.4595, 77.0266),
    "Guwahati": (26.1445, 91.7362),
    "Hyderabad": (17.3850, 78.4867),
    "Jaipur": (26.9124, 75.7873),
    "Jorapokhar": (23.7167, 86.4167),
    "Kochi": (9.9312, 76.2673),
    "Kolkata": (22.5726, 88.3639),
    "Lucknow": (26.8467, 80.9462),
    "Mumbai": (19.0760, 72.8777),
    "Patna": (25.5941, 85.1376),
    "Shillong": (25.5788, 91.8933),
    "Talcher": (20.9500, 85.2300),
    "Thiruvananthapuram": (8.5241, 76.9366),
    "Visakhapatnam": (17.6868, 83.2185),
}


def _ensure_paths() -> None:
    WEATHER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def _require_raw_dataset() -> Path:
    if not RAW_DATA_PATH.exists():
        raise FileNotFoundError(
            f"Missing canonical raw dataset at {RAW_DATA_PATH}. "
            "Stage the full city_hour.csv file before preprocessing."
        )
    return RAW_DATA_PATH


def load_raw_dataset(csv_path: Path | None = None) -> pd.DataFrame:
    path = csv_path or _require_raw_dataset()
    df = pd.read_csv(path, usecols=list(REQUIRED_RAW_COLUMNS.keys()))
    df = df.rename(columns=REQUIRED_RAW_COLUMNS)
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    df = df.drop(columns=["pm25", "pm10", "o3"], errors="ignore")
    for column in ("co", "no2", "aqi"):
        df[column] = pd.to_numeric(df[column], errors="coerce").astype("float32")
    df["city"] = df["city"].astype("string")
    return df.dropna(subset=["city", "datetime"]).reset_index(drop=True)


def _open_json(url: str) -> dict:
    with urlopen(url, timeout=120) as response:  # noqa: S310 - controlled endpoint
        return json.loads(response.read().decode("utf-8"))


def _city_ranges(df: pd.DataFrame) -> Iterable[tuple[str, str, str]]:
    grouped = df.groupby("city", observed=True)["datetime"].agg(["min", "max"]).reset_index()
    for row in grouped.itertuples(index=False):
        yield row.city, row.min.date().isoformat(), row.max.date().isoformat()


def _fetch_weather_for_city(city: str, start_date: str, end_date: str) -> pd.DataFrame:
    if city not in CITY_COORDINATES:
        raise KeyError(f"Missing coordinates for city: {city}")

    latitude, longitude = CITY_COORDINATES[city]
    years = range(int(start_date[:4]), int(end_date[:4]) + 1)
    frames: list[pd.DataFrame] = []

    for year in years:
        cache_path = WEATHER_CACHE_DIR / f"{city.lower().replace(' ', '_')}_{year}.csv"
        if cache_path.exists():
            frames.append(pd.read_csv(cache_path, parse_dates=["datetime"]))
            continue

        year_start = max(start_date, f"{year}-01-01")
        year_end = min(end_date, f"{year}-12-31")
        query = urlencode(
            {
                "latitude": latitude,
                "longitude": longitude,
                "start_date": year_start,
                "end_date": year_end,
                "hourly": "temperature_2m,relative_humidity_2m",
                "timezone": "Asia/Kolkata",
            }
        )
        payload = _open_json(f"https://archive-api.open-meteo.com/v1/archive?{query}")
        hourly = payload.get("hourly", {})
        frame = pd.DataFrame(
            {
                "datetime": pd.to_datetime(hourly.get("time", []), errors="coerce"),
                "temperature": pd.to_numeric(hourly.get("temperature_2m", []), errors="coerce"),
                "humidity": pd.to_numeric(hourly.get("relative_humidity_2m", []), errors="coerce"),
            }
        )
        frame["city"] = city
        frame = frame.dropna(subset=["datetime"]).reset_index(drop=True)
        frame["temperature"] = frame["temperature"].astype("float32")
        frame["humidity"] = frame["humidity"].astype("float32")
        frame.to_csv(cache_path, index=False)
        frames.append(frame)
        time.sleep(0.2)

    weather = pd.concat(frames, ignore_index=True)
    weather = weather[(weather["datetime"] >= start_date) & (weather["datetime"] <= f"{end_date} 23:59:59")]
    return weather[["city", "datetime", "temperature", "humidity"]]


def build_weather_dataset(df: pd.DataFrame) -> pd.DataFrame:
    frames = [_fetch_weather_for_city(city, start_date, end_date) for city, start_date, end_date in _city_ranges(df)]
    weather = pd.concat(frames, ignore_index=True)
    weather = weather.drop_duplicates(subset=["city", "datetime"]).sort_values(["city", "datetime"])
    return weather.reset_index(drop=True)


def _engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["city", "datetime"]).reset_index(drop=True)
    group = df.groupby("city", observed=True)
    shifted = group["aqi"].shift(1)
    df["aqi_lag_1"] = group["aqi"].shift(1)
    df["aqi_lag_3"] = group["aqi"].shift(3)
    df["aqi_lag_6"] = group["aqi"].shift(6)
    df["aqi_roll_mean_3"] = (
        shifted.groupby(df["city"], observed=True).rolling(window=3, min_periods=3).mean().reset_index(level=0, drop=True)
    )
    df["aqi_roll_mean_6"] = (
        shifted.groupby(df["city"], observed=True).rolling(window=6, min_periods=6).mean().reset_index(level=0, drop=True)
    )
    df["hour_of_day"] = df["datetime"].dt.hour.astype("int16")
    return df


def preprocess_full_dataset() -> tuple[pd.DataFrame, dict]:
    _ensure_paths()
    df = load_raw_dataset()
    weather = build_weather_dataset(df)

    merged = df.merge(weather, on=["city", "datetime"], how="left", validate="many_to_one")
    merged = merged.sort_values(["city", "datetime"]).reset_index(drop=True)

    for column in ("co", "no2", "temperature", "humidity"):
        merged[column] = merged.groupby("city", observed=True)[column].transform(lambda s: s.ffill().bfill())

    merged = merged.dropna(subset=["aqi", "co", "no2", "temperature", "humidity"]).reset_index(drop=True)
    merged = _engineer_features(merged)
    merged = merged.dropna(subset=["aqi_lag_1", "aqi_lag_3", "aqi_lag_6", "aqi_roll_mean_3", "aqi_roll_mean_6"])
    merged = merged.reset_index(drop=True)

    for column in FEATURE_COLUMNS + ["aqi"]:
        merged[column] = pd.to_numeric(merged[column], errors="coerce").astype("float32")

    train_ready = merged[["city", "datetime", *FEATURE_COLUMNS, "aqi"]].copy()
    train_ready.to_csv(TRAIN_READY_PATH, index=False)

    metadata = {
        "rows": int(len(train_ready)),
        "cities": int(train_ready["city"].nunique()),
        "source_rows": int(len(df)),
        "feature_columns": FEATURE_COLUMNS,
        "target_column": "aqi",
        "train_ready_path": str(TRAIN_READY_PATH),
        "default_values": {
            "co": float(train_ready["co"].median()),
            "no2": float(train_ready["no2"].median()),
            "temperature": float(train_ready["temperature"].median()),
            "humidity": float(train_ready["humidity"].median()),
            "aqi": float(train_ready["aqi"].median()),
            "aqi_roll_mean_3": float(train_ready["aqi_roll_mean_3"].median()),
            "aqi_roll_mean_6": float(train_ready["aqi_roll_mean_6"].median()),
        },
        "generated_columns": ["city", "datetime", *FEATURE_COLUMNS, "aqi"],
    }
    PREPROCESS_METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return train_ready, metadata


def main() -> None:
    frame, metadata = preprocess_full_dataset()
    print(f"train_ready_rows={len(frame)}")
    print(f"train_ready_path={TRAIN_READY_PATH}")
    print(f"features={metadata['feature_columns']}")


if __name__ == "__main__":
    main()
