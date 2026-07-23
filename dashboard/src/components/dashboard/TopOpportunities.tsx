'use client'

import { ChevronRight, TrendingUp, Target, Clock, DollarSign, Zap, Activity } from 'lucide-react'
import Link from 'next/link'
import { cn } from '@/lib/utils'

interface OpportunityCardProps {
  opportunity: {
    id: string
    slug: string
    title: string
    protocol_name: string
    category: string
    overall_score: number
    difficulty_score: number
    estimated_value_usd_min: number | null
    estimated_value_usd_max: number | null
    verdict: string
    networks: string[]
    risk_level: string
    detected_at: string
    claim_start: string | null
    claim_end: string | null
    task_count: number
    total_gas_estimate_usd: number
  }
}

const VERDICT_STYLES = {
  worthwhile: 'bg-green-500/20 text-green-400 border-green-500/30',
  speculative: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  risky: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  skip: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  scam: 'bg-red-500/20 text-red-400 border-red-500/30',
}

const VERDICT_LABELS = {
  worthwhile: 'Worthwhile',
  speculative: 'Speculative',
  risky: 'Risky',
  skip: 'Skip',
  scam: 'Scam',
}

export function TopOpportunities() {
  const opportunities = [
    {
      id: 'opp_1',
      slug: 'hyperscale-l3-airdrop',
      title: 'HyperScale L3 Airdrop Season 1',
      protocol_name: 'HyperScale',
      category: 'l3_rollup',
      overall_score: 78.3,
      difficulty_score: 6.5,
      estimated_value_usd_min: 500,
      estimated_value_usd_max: 5000,
      verdict: 'worthwhile',
      networks: ['ethereum', 'arbitrum'],
      risk_level: 'medium',
      detected_at: '2026-07-23T09:42:00Z',
      claim_start: '2026-08-15T00:00:00Z',
      claim_end: '2026-09-15T00:00:00Z',
      task_count: 12,
      total_gas_estimate_usd: 45,
    },
    {
      id: 'opp_2',
      slug: 'nova-chain-airdrop',
      title: 'Nova Chain Mainnet Incentive',
      protocol_name: 'Nova Chain',
      category: 'l1',
      overall_score: 72.1,
      difficulty_score: 5.2,
      estimated_value_usd_min: 200,
      estimated_value_usd_max: 2000,
      verdict: 'speculative',
      networks: ['solana'],
      risk_level: 'medium',
      detected_at: '2026-07-23T09:40:00Z',
      claim_start: '2026-07-31T00:00:00Z',
      claim_end: '2026-08-31T00:00:00Z',
      task_count: 8,
      total_gas_estimate_usd: 28,
    },
    {
      id: 'opp_3',
      slug: 'quantum-dex-airdrop',
      title: 'Quantum DEX Genesis Rewards',
      protocol_name: 'Quantum',
      category: 'dex',
      overall_score: 68.5,
      difficulty_score: 4.8,
      estimated_value_usd_min: 300,
      estimated_value_usd_max: 3000,
      verdict: 'worthwhile',
      networks: ['arbitrum'],
      risk_level: 'low',
      detected_at: '2026-07-23T09:35:00Z',
      claim_start: '2026-08-20T00:00:00Z',
      claim_end: '2026-09-20T00:00:00Z',
      task_count: 6,
      total_gas_estimate_usd: 15,
    },
    {
      id: 'opp_4',
      slug: 'pulse-bridge-rewards',
      title: 'Pulse Bridge Early Adopter Program',
      protocol_name: 'Pulse Bridge',
      category: 'bridge',
      overall_score: 45.2,
      difficulty_score: 3.1,
      estimated_value_usd_min: 50,
      estimated_value_usd_max: 500,
      verdict: 'risky',
      networks: ['ethereum'],
      risk_level: 'high',
      detected_at: '2026-07-23T09:30:00Z',
      claim_start: '2026-09-01T00:00:00Z',
      claim_end: '2026-10-01T00:00:00Z',
      task_count: 4,
      total_gas_estimate_usd: 12,
    },
  ]

  return (
    <div className="bg-nabu-bgSecondary border border-nabu-border rounded-xl overflow-hidden">
      <div className="p-4 border-b border-nabu-border flex items-center justify-between">
        <h2 className="text-lg font-semibold text-nabu-text">Top Opportunities</h2>
        <Link href="/opportunities" className="text-xs text-nabu-accent-blue hover:underline">
          View All
        </Link>
      </div>
      <div className="divide-y divide-nabu-border">
        {opportunities.map((opp) => (
          <Link key={opp.id} href={`/opportunities/${opp.slug}`} className="block">
            <div className="p-4 hover:bg-nabu-bgTertiary/50 transition-colors">
              <div className="flex items-center justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-2">
                    <h3 className="font-semibold text-nabu-text truncate">{opp.title}</h3>
                    <span className={cn(
                      'px-2 py-0.5 rounded text-xs font-medium',
                      VERDICT_STYLES[opp.verdict as keyof typeof VERDICT_STYLES]
                    )}>
                      {VERDICT_LABELS[opp.verdict as keyof typeof VERDICT_LABELS]}
                    </span>
                    <span className="px-2 py-0.5 rounded text-xs font-medium bg-nabu-bgTertiary text-nabu-textSecondary">
                      {opp.category.replace('_', ' ').toUpperCase()}
                    </span>
                  </div>
                  <p className="text-sm text-nabu-textSecondary mb-2">{opp.protocol_name}</p>
                  <div className="flex items-center gap-4 text-xs text-nabu-textSecondary">
                    <span className="flex items-center gap-1">
                      <TrendingUp className="h-3 w-3" />
                      Score: {opp.overall_score}
                    </span>
                    <span className="flex items-center gap-1">
                      <Zap className="h-3 w-3" />
                      Difficulty: {opp.difficulty_score}/10
                    </span>
                    <span className="flex items-center gap-1">
                      <Target className="h-3 w-3" />
                      {opp.task_count} tasks
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      ~${opp.total_gas_estimate_usd}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <div className="text-right">
                    <p className="font-semibold text-nabu-text">
                      ${opp.estimated_value_usd_min?.toLocaleString() || '?'} - ${opp.estimated_value_usd_max?.toLocaleString() || '?'}
                    </p>
                    <p className="text-xs text-nabu-textSecondary">Est. Value</p>
                  </div>
                </div>
              </div>
            </div>
          </Link>
        ))}
      </div>
      <div className="p-4 border-t border-nabu-border">
        <Link href="/opportunities" className="text-sm text-nabu-accent-blue hover:underline flex items-center justify-center gap-1">
          View all 247 opportunities
        </Link>
      </div>
    </div>
  )
}