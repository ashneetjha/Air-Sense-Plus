'use client'

import { useState } from 'react'
import { Loader2, Zap } from 'lucide-react'
import { useTranslations } from 'next-intl'

import { postPrediction, type PredictionResponse, type SensorPayload } from '@/lib/api'

interface Props {
  onResult: (result: PredictionResponse) => void
}

const DEFAULTS: SensorPayload = {
  sensor_id: 'demo-sensor',
  co: 0.7,
  no2: 32,
  temperature: 28,
  humidity: 58,
}

const FIELDS: Array<{ key: keyof SensorPayload; step: number; min: number; max: number }> = [
  { key: 'sensor_id', step: 1, min: 0, max: 0 },
  { key: 'co', step: 0.01, min: 0, max: 100 },
  { key: 'no2', step: 0.1, min: 0, max: 5000 },
  { key: 'temperature', step: 0.1, min: -40, max: 70 },
  { key: 'humidity', step: 0.1, min: 0, max: 100 },
]

export function PredictionPanel({ onResult }: Props) {
  const t = useTranslations('dashboard')
  const [values, setValues] = useState<SensorPayload>(DEFAULTS)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleNumberChange = (key: Exclude<keyof SensorPayload, 'sensor_id'>, value: string) => {
    setValues(prev => ({ ...prev, [key]: parseFloat(value) || 0 }))
  }

  const handlePredict = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await postPrediction(values)
      onResult(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Prediction failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        <div className="flex flex-col gap-1">
          <label htmlFor="sensor-id" className="text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
            {t('sensorId')}
          </label>
          <input
            id="sensor-id"
            type="text"
            value={values.sensor_id}
            onChange={e => setValues(prev => ({ ...prev, sensor_id: e.target.value }))}
            className="themed-input"
          />
        </div>

        {FIELDS.filter(field => field.key !== 'sensor_id').map(({ key, step, min, max }) => (
          <div key={key} className="flex flex-col gap-1">
            <label htmlFor={`input-${key}`} className="text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
              {t(key)}
            </label>
            <input
              id={`input-${key}`}
              type="number"
              step={step}
              min={min}
              max={max}
              value={values[key]}
              onChange={e => handleNumberChange(key as Exclude<keyof SensorPayload, 'sensor_id'>, e.target.value)}
              className="themed-input"
            />
          </div>
        ))}
      </div>

      {error && (
        <p className="text-xs text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">
          {error}
        </p>
      )}

      <button onClick={handlePredict} disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2">
        {loading ? (
          <>
            <Loader2 size={15} className="animate-spin" />
            {t('predicting')}
          </>
        ) : (
          <>
            <Zap size={15} />
            {t('predict')}
          </>
        )}
      </button>
    </div>
  )
}
