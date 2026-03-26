'use client'

import { useEffect, useRef } from 'react'
import gsap from 'gsap'

const CATEGORY_META = {
  Good: { color: '#1f9d55', range: '0-50', advisory: 'Air quality is acceptable for normal outdoor activity.' },
  Moderate: { color: '#e0a800', range: '51-100', advisory: 'Sensitive people should reduce prolonged outdoor exertion.' },
  Unhealthy: { color: '#d9480f', range: '101-200', advisory: 'Limit outdoor activity and use masks if exposure is unavoidable.' },
  Hazardous: { color: '#b02a37', range: '200+', advisory: 'Avoid outdoor exposure and keep indoor air protected.' },
} as const

interface Props {
  category: keyof typeof CATEGORY_META | null
  aqi: number | null
  loading?: boolean
}

export function HealthRiskBadge({ category, aqi, loading }: Props) {
  const badgeRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!badgeRef.current || !category) return
    gsap.fromTo(badgeRef.current, { scale: 0.9, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.4, ease: 'power2.out' })
  }, [category])

  if (loading) return <div className="h-28 skeleton rounded-2xl" />
  if (!category || aqi === null) {
    return <div className="h-28 flex items-center justify-center text-[var(--text-muted)] text-sm rounded-2xl border border-[var(--border-color)]">No prediction yet.</div>
  }

  const meta = CATEGORY_META[category]

  return (
    <div
      ref={badgeRef}
      className="relative flex flex-col items-center justify-center gap-2 py-5 px-4 rounded-2xl overflow-hidden"
      style={{ background: `${meta.color}18`, border: `1.5px solid ${meta.color}55` }}
    >
      <p className="aqi-number text-5xl" style={{ color: meta.color }}>
        {Math.round(aqi)}
      </p>
      <span className="px-3 py-0.5 rounded-full text-xs font-bold uppercase tracking-widest" style={{ background: `${meta.color}25`, color: meta.color, border: `1px solid ${meta.color}55` }}>
        {category}
      </span>
      <p className="text-[10px] text-[var(--text-muted)] font-medium">AQI Range: {meta.range}</p>
      <p className="text-center text-xs text-[var(--text-secondary)] leading-relaxed mt-1 px-2">{meta.advisory}</p>
    </div>
  )
}
