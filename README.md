# AirSense+

AirSense+ is a hardware-aligned AQI prediction system rebuilt around the full `city_hour.csv` dataset and the only supported live inputs:

- `co`
- `no2`
- `temperature`
- `humidity`

The runtime path is intentionally simple:

`CSV -> preprocessing -> feature engineering -> model -> FastAPI -> Next.js`

## Project Layout

```text
AirSense+/
├── data/
│   ├── raw/city_hour.csv
│   ├── raw/weather/
│   └── processed/train_ready.csv
├── backend/app/
│   ├── main.py
│   ├── routes/
│   ├── services/
│   ├── models/
│   └── schemas.py
├── ml/
│   ├── preprocess.py
│   ├── train_xgb.py
│   └── train_lstm.py
└── frontend/
```

## Training

1. Stage the full `city_hour.csv` file at `data/raw/city_hour.csv`.
2. Run preprocessing:

```bash
cd ml
python preprocess.py
```

3. Train XGBoost:

```bash
python train_xgb.py
```

4. Train the LSTM model after installing PyTorch:

```bash
python train_lstm.py
```

Artifacts are written to `backend/app/models/`.

## Backend API

Start the API from `backend/`:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Request contract

```json
{
  "sensor_id": "sensor-01",
  "co": 0.7,
  "no2": 32.0,
  "temperature": 28.0,
  "humidity": 58.0
}
```

### Endpoints

- `GET /predict`
- `POST /predict`
- `POST /sensor-ingest`
- `GET /metrics`
- `GET /health-risk?aqi=...`

## Frontend

From `frontend/`:

```bash
npm install
npm run build
npm run dev
```

Set `NEXT_PUBLIC_API_URL` if the API is not running on `http://localhost:8000`.
