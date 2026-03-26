import type { Metadata } from 'next'
import { NextIntlClientProvider } from 'next-intl'
import { getLocale, getMessages } from 'next-intl/server'
import { ThemeProvider } from '@/components/ThemeProvider'
import { Navbar } from '@/components/Navbar'
import './globals.css'

export const metadata: Metadata = {
  title: 'AirSense+ | AI-Powered Air Quality Intelligence',
  description:
    'Real-time AQI forecasting powered by XGBoost ML + SHAP interpretability. Predict air quality 72 hours in advance.',
  keywords: ['AQI', 'air quality', 'machine learning', 'XGBoost', 'SHAP', 'pollution forecast'],
  openGraph: {
    title: 'AirSense+ | AI Air Quality Intelligence',
    description: 'Know what you\'re breathing — 72 hours in advance.',
    type: 'website',
  },
}

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const locale = await getLocale()
  const messages = await getMessages()

  return (
    <html lang={locale} suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="bg-theme min-h-screen antialiased">
        <NextIntlClientProvider messages={messages}>
          <ThemeProvider>
            <Navbar />
            <main className="flex-1">
              {children}
            </main>
          </ThemeProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  )
}
