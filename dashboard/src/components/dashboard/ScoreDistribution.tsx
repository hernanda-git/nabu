'use client'

import { cn } from '@/lib/utils'

interface ScoreDistributionProps {
  data?: number[]
}

export function ScoreDistribution({ data = [12, 8, 15, 22, 18, 14, 10, 6, 4, 3] }: ScoreDistributionProps) {
  const max = Math.max(...data)
  
  return (
    <div className="bg-nabu-bgSecondary border border-nabu-border rounded-xl p-5">
      <h3 className="text-sm font-semibold text-nabu-text mb-4">Score Distribution</h3>
      <div className="space-y-2">
        {data.map((value, index) => {
          const range = `${index * 10}-${(index + 1) * 10 - 1}`
          if (index === 9) range = '90-100'
          const height = (value / max) * 100
          return (
            <div key={index} className="flex items-center gap-3">
              <span className="text-xs text-nabu-textSecondary w-14 text-right font-mono">{range}</span>
              <div className="flex-1 h-4 bg-nabu-bg rounded overflow-hidden">
                <div 
                  className="h-full bg-nabu-accent-blue transition-all duration-500"
                  style={{ width: `${height}%` }}
                />
              </div>
              <span className="text-xs font-mono text-nabu-textSecondary w-10 text-right">{value}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}