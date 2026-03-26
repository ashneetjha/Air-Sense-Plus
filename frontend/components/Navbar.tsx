'use client'

import Link from 'next/link'
import { useTranslations } from 'next-intl'
import { ThemeToggle } from './ThemeToggle'
import { LanguageToggle } from './LanguageToggle'
import { Wind } from 'lucide-react'

export function Navbar() {
    const t = useTranslations('nav')

    return (
        <nav className="
      sticky top-0 z-50
      flex items-center justify-between
      px-4 sm:px-8 py-3
      border-b border-[var(--border-color)]
      bg-[var(--bg-card)] backdrop-blur-xl
    ">
            {/* Logo */}
            <Link href="/" className="flex items-center gap-2.5 group">
                <div className="
          w-8 h-8 rounded-xl flex items-center justify-center
          bg-gradient-to-br from-brand-500 to-violet-500
          shadow-glow-sm group-hover:shadow-glow transition-shadow duration-300
        ">
                    <Wind size={16} className="text-white" />
                </div>
                <div className="leading-none">
                    <span className="font-display font-bold text-base text-[var(--text-primary)]">
                        AirSense
                        <span className="gradient-badge ml-0.5">+</span>
                    </span>
                    <p className="text-[9px] text-[var(--text-muted)] font-medium tracking-widest uppercase">
                        AQI Intelligence
                    </p>
                </div>
            </Link>

            {/* Nav links */}
            <div className="hidden sm:flex items-center gap-1">
                {[
                    { href: '/', label: t('dashboard') },
                ].map(link => (
                    <Link
                        key={link.href}
                        href={link.href}
                        className="
              px-3 py-1.5 rounded-lg text-sm font-medium
              text-[var(--text-secondary)]
              hover:text-[var(--text-primary)] hover:bg-[var(--badge-bg)]
              transition-all duration-200
            "
                    >
                        {link.label}
                    </Link>
                ))}
            </div>

            {/* Controls */}
            <div className="flex items-center gap-2">
                <LanguageToggle />
                <ThemeToggle />
            </div>
        </nav>
    )
}
