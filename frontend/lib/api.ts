const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export interface PredictionResponse {
  predicted_aqi: number
  category: 'Good' | 'Moderate' | 'Unhealthy' | 'Hazardous'
  model_type: 'xgb' | 'lstm'
}

export interface MetricsResponse {
  model_type: 'xgb' | 'lstm'
  rmse: number
  mae: number
  r2: number
  n_train: number
  n_test: number
  n_features: number
  feature_columns: string[]
}

export interface SensorPayload {
  sensor_id: string
  co: number
  no2: number
  temperature: number
  humidity: number
}

export interface HealthRisk {
  category: 'Good' | 'Moderate' | 'Unhealthy' | 'Hazardous'
  color: string
  aqi_range: string
  advisory: string
}

export interface SensorIngestResponse {
  status: string
  prediction: PredictionResponse
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  if (!response.ok) {
    throw new Error(await response.text())
  }

  return response.json() as Promise<T>
}

export const getDefaultPrediction = (): Promise<PredictionResponse> => apiFetch('/predict')
export const postPrediction = (payload: SensorPayload): Promise<PredictionResponse> =>
  apiFetch('/predict', { method: 'POST', body: JSON.stringify(payload) })
export const getMetrics = (): Promise<MetricsResponse> => apiFetch('/metrics')
export const getHealthRisk = (aqi: number): Promise<HealthRisk> => apiFetch(`/health-risk?aqi=${aqi}`)
