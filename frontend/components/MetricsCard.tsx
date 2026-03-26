'use client'

import { useTranslations } from 'next-intl'

import type { MetricsResponse } from '@/lib/api'

interface Props {
  metrics: MetricsResponse | null
  loading?: boolean
}

function MetricStat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex flex-col items-center gap-1 p-3 rounded-xl bg-[var(--badge-bg)] border border-[var(--border-color)]">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--text-muted)]">{label}</p>
      <p className="font-display font-bold text-xl text-[var(--accent)]">{value}</p>
    </div>
  )
}

export function MetricsCard({ metrics, loading }: Props) {
  const t = useTranslations('dashboard')

  if (loading) return <div className="h-40 skeleton rounded-2xl" />
  if (!metrics) {
    return <div className="h-40 flex items-center justify-center text-[var(--text-muted)] text-sm rounded-2xl border border-[var(--border-color)]">Metrics unavailable.</div>
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2">
        <MetricStat label={t('activeModel')} value={metrics.model_type.toUpperCase()} />
        <MetricStat label={t('features')} value={metrics.n_features} />
      </div>
      <div className="grid grid-cols-3 gap-2">
        <MetricStat label={t('rmse')} value={metrics.rmse.toFixed(2)} />
        <MetricStat label={t('mae')} value={metrics.mae.toFixed(2)} />
        <MetricStat label={t('r2')} value={`${(metrics.r2 * 100).toFixed(1)}%`} />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <MetricStat label={t('trainSamples')} value={metrics.n_train.toLocaleString()} />
        <MetricStat label={t('testSamples')} value={metrics.n_test.toLocaleString()} />
      </div>
    </div>
  )
}
