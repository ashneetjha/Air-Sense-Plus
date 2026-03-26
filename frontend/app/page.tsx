'use client'

import type { ElementType, ReactNode } from 'react'
import { useEffect, useRef, useState } from 'react'
import { Activity, Cpu, Layers } from 'lucide-react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { useTranslations } from 'next-intl'

import { HealthRiskBadge } from '@/components/HealthRiskBadge'
import { MetricsCard } from '@/components/MetricsCard'
import { PredictionPanel } from '@/components/PredictionPanel'
import { getDefaultPrediction, getMetrics, type MetricsResponse, type PredictionResponse } from '@/lib/api'

gsap.registerPlugin(ScrollTrigger)

function Card({
  title,
  icon: Icon,
  children,
}: {
  title: string
  icon?: ElementType
  children: ReactNode
}) {
  return (
    <div className="glass-card p-5">
      <div className="flex items-center gap-2 mb-4">
        {Icon && (
          <div className="w-7 h-7 rounded-lg flex items-center justify-center bg-[var(--badge-bg)] border border-[var(--border-color)]">
            <Icon size={14} className="text-[var(--accent)]" />
          </div>
        )}
        <h2 className="font-display font-semibold text-sm text-[var(--text-primary)] tracking-tight">{title}</h2>
      </div>
      {children}
    </div>
  )
}

export default function DashboardPage() {
  const t = useTranslations('dashboard')
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null)
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null)
  const [loadingPrediction, setLoadingPrediction] = useState(true)
  const [loadingMetrics, setLoadingMetrics] = useState(true)
  const [initError, setInitError] = useState<string | null>(null)

  const headerRef = useRef<HTMLDivElement>(null)
  const cardsRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    Promise.all([
      getDefaultPrediction().then(setPrediction).catch(e => setInitError(e.message)).finally(() => setLoadingPrediction(false)),
      getMetrics().then(setMetrics).catch(() => {}).finally(() => setLoadingMetrics(false)),
    ])
  }, [])

  useEffect(() => {
    if (!headerRef.current || !cardsRef.current) return
    const cards = cardsRef.current.querySelectorAll('.glass-card')
    gsap.fromTo(headerRef.current, { opacity: 0, y: -16 }, { opacity: 1, y: 0, duration: 0.6, ease: 'power2.out' })
    gsap.fromTo(cards, { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.5, stagger: 0.08, ease: 'power2.out', delay: 0.15 })
  }, [])

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-16 pt-8">
      <div ref={headerRef} className="mb-8">
        <div className="flex items-center gap-2 mb-2">
          <span className="metric-pill">Production Sensor Contract</span>
          <span className="metric-pill">{prediction?.model_type?.toUpperCase() ?? 'XGB'}</span>
        </div>
        <h1 className="font-display font-bold text-3xl sm:text-4xl text-[var(--text-primary)] tracking-tight">{t('title')}</h1>
        <p className="text-[var(--text-secondary)] mt-1 text-sm">{t('subtitle')}</p>
        {initError && <div className="mt-3 text-sm text-amber-400 bg-amber-400/10 border border-amber-400/20 rounded-lg px-4 py-2.5">{initError}</div>}
      </div>

      <div ref={cardsRef} className="space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card title={t('livePrediction')} icon={Activity}>
            <HealthRiskBadge category={prediction?.category ?? null} aqi={prediction?.predicted_aqi ?? null} loading={loadingPrediction} />
          </Card>
          <Card title={t('modelMetrics')} icon={Cpu}>
            <MetricsCard metrics={metrics} loading={loadingMetrics} />
          </Card>
          <Card title={t('currentModel')} icon={Layers}>
            <div className="space-y-3">
              <div className="rounded-2xl border border-[var(--border-color)] bg-[var(--badge-bg)] p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-[var(--text-muted)]">{t('activeModel')}</p>
                <p className="mt-2 font-display text-3xl text-[var(--accent)]">{prediction?.model_type?.toUpperCase() ?? 'N/A'}</p>
                <p className="mt-2 text-sm text-[var(--text-secondary)]">{t('modelDescription')}</p>
              </div>
            </div>
          </Card>
        </div>

        <Card title={t('inputTitle')} icon={Layers}>
          <p className="text-xs text-[var(--text-muted)] mb-4">{t('inputSubtitle')}</p>
          <PredictionPanel onResult={setPrediction} />
        </Card>
      </div>
    </div>
  )
}
