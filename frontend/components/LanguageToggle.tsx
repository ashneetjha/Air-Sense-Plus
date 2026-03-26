'use client'

import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'

export function LanguageToggle() {
    const t = useTranslations('lang')
    const router = useRouter()

    const getCurrentLocale = () => {
        if (typeof document !== 'undefined') {
            const match = document.cookie.match(/locale=([^;]+)/)
            return match?.[1] ?? 'en'
        }
        return 'en'
    }

    const toggle = () => {
        const current = getCurrentLocale()
        const next = current === 'en' ? 'hi' : 'en'
        document.cookie = `locale=${next}; path=/; max-age=${60 * 60 * 24 * 365}`
        router.refresh()
    }

    const current = typeof document !== 'undefined' ? getCurrentLocale() : 'en'

    return (
        <button
            onClick={toggle}
            aria-label="Toggle language"
            className="
        flex items-center gap-1
        px-3 py-1.5 rounded-full text-xs font-semibold
        bg-[var(--badge-bg)] border border-[var(--border-color)]
        text-[var(--accent)]
        hover:shadow-[0_0_10px_var(--accent-glow)]
        hover:border-[var(--accent)]
        transition-all duration-200
        focus:outline-none
      "
        >
            <span className={current === 'en' ? 'opacity-100' : 'opacity-40'}>{t('en')}</span>
            <span className="opacity-30 text-[var(--text-muted)]">/</span>
            <span className={current === 'hi' ? 'opacity-100' : 'opacity-40'}>{t('hi')}</span>
        </button>
    )
}
