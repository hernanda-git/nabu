import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { NabuProvider } from './providers'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })

export const metadata: Metadata = {
  title: '𒀭 NABU — Airdrop Intelligence Cortex',
  description: 'The Oracle\'s API — Real-time airdrop intelligence for mining machines',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased bg-slate-950 text-slate-100`}>
        <NabuProvider>
          {children}
        </NabuProvider>
      </body>
    </html>
  )
}