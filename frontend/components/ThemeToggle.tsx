'use client'

import { Moon, Sun } from 'lucide-react'
import { useTheme } from './ThemeProvider'
import { useTranslations } from 'next-intl'

export function ThemeToggle() {
    const { theme, toggleTheme } = useTheme()
    const t = useTranslations('theme')

    return (
        <button
            onClick={toggleTheme}
            aria-label={theme === 'dark' ? t('light') : t('dark')}
            className="
        relative flex items-center justify-center
        w-10 h-10 rounded-full
        bg-[var(--badge-bg)] border border-[var(--border-color)]
        text-[var(--text-secondary)]
        hover:text-[var(--accent)] hover:border-[var(--accent)]
        hover:shadow-[0_0_12px_var(--accent-glow)]
        transition-all duration-200
        focus:outline-none focus:ring-2 focus:ring-[var(--accent)]
      "
        >
            {theme === 'dark' ? (
                <Sun size={18} className="text-amber-400" />
            ) : (
                <Moon size={18} className="text-brand-500" />
            )}
        </button>
    )
}
