'use client'

import { 
  TrendingUp, 
  AlertTriangle, 
  Zap, 
  Clock, 
  DollarSign,
  BarChart3,
  ExternalLink,
  ChevronRight,
} from 'lucide-react'
import Link from 'next/link'
import { cn } from '@/lib/utils'

interface SummaryCardProps {
  title: string
  value: string | number
  change?: string
  changeType?: 'positive' | 'negative' | 'neutral'
  icon: React.ReactNode
  color: 'green' | 'yellow' | 'orange' | 'blue' | 'red'
  href?: string
}

export function SummaryCard({ title, value, change, changeType, icon, color, href }: SummaryCardProps) {
  const colorMap = {
    green: 'bg-green-500/20 text-green-400 border-green-500/30',
    yellow: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    orange: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
    blue: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    red: 'bg-red-500/20 text-red-400 border-red-500/30',
  }
  
  const iconBg = colorMap[color]
  
  return (
    <div className="bg-nabu-bgSecondary border border-nabu-border rounded-xl p-5 transition-all hover:border-nabu-border/50">
      {href && <Link href={href} className="block" />}
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-nabu-textSecondary uppercase tracking-wider mb-1">{title}</p>
          <p className="text-2xl font-bold text-nabu-text">{value}</p>
          {change && (
            <p className={cn(
              'text-xs font-medium mt-1 flex items-center gap-1',
              changeType === 'positive' && 'text-green-400',
              changeType === 'negative' && 'text-red-400',
              changeType === 'neutral' && 'text-nabu-textSecondary'
            )}>
              {change}
            </p>
          )}
        </div>
        <div className={cn('p-2 rounded-lg', iconBg)}>
          {icon}
        </div>
      </div>
      {href && (
        <div className="mt-4 pt-4 border-t border-nabu-border flex items-center justify-between text-sm text-nabu-textSecondary">
          <span>View details</span>
          <ExternalLink className="h-4 w-4" />
        </div>
      )}
    </div>
  )
}