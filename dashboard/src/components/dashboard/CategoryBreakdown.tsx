'use client'

import { cn } from '@/lib/utils'

interface CategoryBreakdownProps {
  data?: { category: string; count: number; color: string }[]
}

export function CategoryBreakdown({ 
  data = [
    { category: 'L2/L3', count: 45, color: '#3b82f6' },
    { category: 'DeFi', count: 82, color: '#8b5cf6' },
    { category: 'DEX', count: 38, color: '#22c55e' },
    { category: 'Bridge', count: 15, color: '#f97316' },
    { category: 'NFT', count: 12, color: '#ec4899' },
    { category: 'Infra', count: 30, color: '#6366f1' },
    { category: 'Gaming', count: 15, color: '#06b6d4' },
    { category: 'Other', count: 10, color: '#64748b' },
  ] 
}: CategoryBreakdownProps) {
  const max = Math.max(...data.map(d => d.count))

  return (
    <div className="bg-nabu-bgSecondary border border-nabu-border rounded-xl p-5">
      <h3 className="text-sm font-semibold text-nabu-text mb-4">Category Breakdown</h3>
      <div className="space-y-2">
        {data.map((item, index) => (
          <div key={index} className="flex items-center gap-3">
            <span className="text-xs text-nabu-textSecondary w-16 truncate">{item.category}</span>
            <div className="flex-1 h-4 bg-nabu-bg rounded overflow-hidden">
              <div 
                className="h-full rounded"
                style={{ width: `${(item.count / max) * 100}%`, backgroundColor: item.color }}
              />
            </div>
            <span className="text-xs font-mono text-nabu-textSecondary w-10 text-right">{item.count}</span>
          </div>
        ))}
      </div>
    </div>
  )
}