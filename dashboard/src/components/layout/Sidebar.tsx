'use client'

import { Suspense } from 'react'
import { 
  LayoutDashboard, 
  BarChart3, 
  Wallet, 
  Calendar, 
  Bot, 
  Eye, 
  Search, 
  Settings,
  TrendingUp,
  AlertTriangle,
  Zap,
} from 'lucide-react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Opportunities', href: '/opportunities', icon: BarChart3 },
  { name: 'Wallets', href: '/wallets', icon: Wallet },
  { name: 'Analytics', href: '/analytics', icon: TrendingUp },
  { name: 'Calendar', href: '/calendar', icon: Calendar },
  { name: 'Machines', href: '/machines', icon: Bot },
  { name: 'Watchlist', href: '/watchlist', icon: Eye },
  { name: 'Search', href: '/search', icon: Search },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()
  
  return (
    <aside className="fixed inset-y-0 left-0 z-50 w-64 bg-nabu-bgSecondary border-r border-nabu-border transform transition-transform duration-300 ease-in-out lg:translate-x-0">
      <div className="flex flex-col h-full">
        {/* Logo */}
        <div className="flex items-center justify-between h-16 px-4 border-b border-nabu-border">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-2xl font-bold text-nabu-accent-green">𒀭</span>
            <span className="text-lg font-semibold text-nabu-text">NABU</span>
          </Link>
        </div>
        
        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {navigation.map((item) => {
            const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href))
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-nabu-bgTertiary text-nabu-accent-green'
                    : 'text-nabu-textSecondary hover:bg-nabu-bgTertiary hover:text-nabu-text'
                )}
              >
                <item.icon className="h-5 w-5" aria-hidden="true" />
                {item.name}
              </Link>
            )
          })}
        </nav>
        
        {/* Status Bar */}
        <div className="p-4 border-t border-nabu-border">
          <div className="flex items-center justify-between text-xs">
            <span className="text-nabu-textSecondary">Status</span>
            <div className="flex items-center gap-2">
              <span className="flex h-2 w-2 rounded-full bg-nabu-accent-green animate-pulse" />
              <span className="text-nabu-accent-green font-medium">Live</span>
            </div>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
            <div className="bg-nabu-bg p-2 rounded">
              <div className="text-nabu-textSecondary">Opportunities</div>
              <div className="font-bold text-nabu-text">247</div>
            </div>
            <div className="bg-nabu-bg p-2 rounded">
              <div className="text-nabu-textSecondary">High Priority</div>
              <div className="font-bold text-nabu-accent-orange">42</div>
            </div>
          </div>
        </div>
      </div>
    </aside>
  )
}