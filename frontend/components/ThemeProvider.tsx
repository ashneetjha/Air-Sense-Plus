'use client'

import { createContext, useContext, useEffect, useRef, useState } from 'react'
import gsap from 'gsap'

type Theme = 'light' | 'dark'

interface ThemeContextType {
    theme: Theme
    toggleTheme: () => void
}

const ThemeContext = createContext<ThemeContextType>({
    theme: 'dark',
    toggleTheme: () => { },
})

export const useTheme = () => useContext(ThemeContext)

export function ThemeProvider({ children }: { children: React.ReactNode }) {
    const [theme, setTheme] = useState<Theme>('dark')
    const overlayRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        const saved = (localStorage.getItem('airsense-theme') as Theme) ?? 'dark'
        setTheme(saved)
        document.documentElement.classList.toggle('dark', saved === 'dark')
    }, [])

    const toggleTheme = () => {
        const overlay = overlayRef.current
        if (!overlay) return

        // GSAP flashover animation
        gsap.timeline()
            .set(overlay, { opacity: 0, display: 'block' })
            .to(overlay, { opacity: 1, duration: 0.18, ease: 'power2.in' })
            .add(() => {
                const next = theme === 'dark' ? 'light' : 'dark'
                setTheme(next)
                localStorage.setItem('airsense-theme', next)
                document.documentElement.classList.toggle('dark', next === 'dark')
            })
            .to(overlay, { opacity: 0, duration: 0.25, ease: 'power2.out' })
            .set(overlay, { display: 'none' })
    }

    return (
        <ThemeContext.Provider value={{ theme, toggleTheme }}>
            {/* GSAP transition overlay */}
            <div
                ref={overlayRef}
                className="fixed inset-0 z-[9999] pointer-events-none hidden"
                style={{ background: 'var(--accent)', opacity: 0 }}
            />
            {children}
        </ThemeContext.Provider>
    )
}
