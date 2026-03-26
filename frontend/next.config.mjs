import createNextIntlPlugin from 'next-intl/plugin'

const withNextIntl = createNextIntlPlugin('./i18n/request.ts')

const nextConfig = {
  experimental: {
    optimizePackageImports: ['recharts', 'lucide-react'],
  },
}

export default withNextIntl(nextConfig)
