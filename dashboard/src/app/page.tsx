'use client'

import { Suspense } from 'react'
import { 
  TrendingUp, AlertTriangle, Zap, Clock, DollarSign, 
  BarChart3, Target, Activity, ExternalLink, Link2 
} from 'lucide-react'
import { SummaryCard } from '@/components/dashboard/SummaryCard'
import { LiveFeed } from '@/components/dashboard/LiveFeed'
import { ScoreDistribution } from '@/components/dashboard/ScoreDistribution'
import { CategoryBreakdown } from '@/components/dashboard/CategoryBreakdown'
import { TopOpportunities } from '@/components/dashboard/TopOpportunities'

export default function DashboardPage() {
  return (
    <div className="pt-16 lg:ml-64 min-h-screen bg-nabu-bgPrimary">
      <main className="p-4 lg:p-6 space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl lg:text-3xl font-bold text-nabu-text">Dashboard</h1>
            <p className="text-nabu-textSecondary mt-1">Real-time airdrop intelligence overview</p>
          </div>
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1 text-xs text-nabu-accent-green">
              <span className="h-1.5 w-1.5 rounded-full bg-nabu-accent-green animate-pulse" />
              Live
            </span>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <SummaryCard
            title="Active Opportunities"
            value="247"
            change="+12 today"
            changeType="positive"
            icon={<Target className="h-5 w-5" />}
            color="blue"
            href="/opportunities"
          />
          <SummaryCard
            title="High Priority"
            value="42"
            change="+5 this hour"
            changeType="positive"
            icon={<AlertTriangle className="h-5 w-5" />}
            color="orange"
            href="/opportunities?min_score=80"
          />
          <SummaryCard
            title="Tasks Remaining"
            value="1,893"
            change="-234 completed"
            changeType="positive"
            icon={<Zap className="h-5 w-5" />}
            color="green"
            href="/wallets"
          />
          <SummaryCard
            title="Est. Total Value"
            value="$125K - $1.5M"
            change="+$12K this week"
            changeType="positive"
            icon={<DollarSign className="h-5 w-5" />}
            color="yellow"
            href="/analytics"
          />
          <SummaryCard
            title="Gas Spent"
            value="$342"
            change="This session"
            changeType="neutral"
            icon={<Clock className="h-5 w-5" />}
            color="red"
            href="/wallets"
          />
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Live Feed + Score Distribution */}
          <div className="lg:col-span-2 space-y-6">
            <Suspense fallback={<div className="h-96 animate-pulse bg-nabu-bgSecondary rounded-xl" />}>
              <LiveFeed />
            </Suspense>
            
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <Suspense fallback={<div className="h-64 animate-pulse bg-nabu-bgSecondary rounded-xl" />}>
                <ScoreDistribution />
              </Suspense>
              <Suspense fallback={<div className="h-64 animate-pulse bg-nabu-bgSecondary rounded-xl" />}>
                <CategoryBreakdown />
              </Suspense>
            </div>
          </div>

          {/* Right Column - Top Opportunities */}
          <div className="space-y-6">
            <Suspense fallback={<div className="h-96 animate-pulse bg-nabu-bgSecondary rounded-xl" />}>
              <TopOpportunities />
            </Suspense>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          <Link href="/opportunities?status=active" className={cn(
            'p-4 bg-nabu-bgSecondary border border-nabu-border rounded-xl',
            'hover:border-nabu-accent-blue/50 transition-colors',
            'flex flex-col items-center text-center gap-2'
          )}>
            <BarChart3 className="h-8 w-8 text-nabu-accent-blue" />
            <span className="font-medium text-nabu-text">All Opportunities</span>
            <span className="text-xs text-nabu-textSecondary">247 active</span>
          </Link>
          <Link href="/opportunities?min_score=80" className={cn(
            'p-4 bg-nabu-bgSecondary border border-nabu-border rounded-xl',
            'hover:border-nabu-accent-orange/50 transition-colors',
            'flex flex-col items-center text-center gap-2'
          )}>
            <Target className="h-8 w-8 text-nabu-accent-orange" />
            <span className="font-medium text-nabu-text">High Priority</span>
            <span className="text-xs text-nabu-textSecondary">42 opps</span>
          </Link>
          <Link href="/wallets" className={cn(
            'p-4 bg-nabu-bgSecondary border border-nabu-border rounded-xl',
            'hover:border-nabu-accent-green/50 transition-colors',
            'flex flex-col items-center text-center gap-2'
          )}>
            <Activity className="h-8 w-8 text-nabu-accent-green" />
            <span className="font-medium text-nabu-text">My Wallets</span>
            <span className="text-xs text-nabu-textSecondary">12 engaged</span>
          </Link>
          <Link href="/analytics" className={cn(
            'p-4 bg-nabu-bgSecondary border border-nabu-border rounded-xl',
            'hover:border-nabu-accent-blue/50 transition-colors',
            'flex flex-col items-center text-center gap-2'
          )}>
            <ExternalLink className="h-8 w-8 text-nabu-accent-blue" />
            <span className="font-medium text-nabu-text">Analytics</span>
            <span className="text-xs text-nabu-textSecondary">Deep dive</span>
          </Link>
        </div>
      </main>
    </div>
  )
}