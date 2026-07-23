'use client'

import { Search, Bell, Moon, Sun, Menu, User, LogOut } from 'lucide-react'
import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'

export function Header() {
  const pathname = usePathname()
  const [searchOpen, setSearchOpen] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  
  return (
    <header className="fixed top-0 left-0 right-0 z-40 h-16 bg-nabu-bgSecondary/80 backdrop-blur-sm border-b border-nabu-border lg:ml-64">
      <div className="flex items-center justify-between h-full px-4 lg:px-6">
        {/* Mobile menu toggle */}
        <button
          className="lg:hidden p-2 rounded-lg hover:bg-nabu-bgTertiary"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        >
          <Menu className="h-6 w-6 text-nabu-text" />
        </button>
        
        {/* Search */}
        <div className={cn('flex-1 max-w-md', searchOpen && 'lg:max-w-xl')}>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-nabu-textSecondary" />
            <input
              type="search"
              placeholder="Search opportunities, protocols, wallets..."
              className={cn(
                'w-full pl-10 pr-4 py-2 bg-nabu-bgTertiary border border-nabu-border rounded-lg',
                'text-nabu-text placeholder-nabu-textSecondary',
                'focus:outline-none focus:ring-2 focus:ring-nabu-accent-blue focus:border-transparent',
                'transition-all'
              )}
              onFocus={() => setSearchOpen(true)}
              onBlur={() => setTimeout(() => setSearchOpen(false), 200)}
            />
          </div>
        </div>
        
        {/* Right side actions */}
        <div className="flex items-center gap-2">
          {/* Theme toggle */}
          <button className="p-2 rounded-lg hover:bg-nabu-bgTertiary transition-colors">
            <Moon className="h-5 w-5 text-nabu-textSecondary" />
          </button>
          
          {/* Notifications */}
          <button className="relative p-2 rounded-lg hover:bg-nabu-bgTertiary transition-colors">
            <Bell className="h-5 w-5 text-nabu-textSecondary" />
            <span className="absolute top-1 right-1 h-4 w-4 rounded-full bg-nabu-accent-red text-[10px] flex items-center justify-center font-bold">
              3
            </span>
          </button>
          
          {/* User menu */}
          <div className="relative">
            <button className="flex items-center gap-2 p-2 rounded-lg hover:bg-nabu-bgTertiary transition-colors">
              <div className="h-8 w-8 rounded-full bg-nabu-accent-blue flex items-center justify-center font-bold text-sm">
                HN
              </div>
              <span className="hidden sm:block text-sm font-medium text-nabu-text">Hernanda</span>
              <ChevronDown className="h-4 w-4 text-nabu-textSecondary" />
            </button>
          </div>
        </div>
      </div>
      
      {/* Mobile menu */}
      {mobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 z-50 bg-black/50" onClick={() => setMobileMenuOpen(false)} />
      )}
    </header>
  )
}