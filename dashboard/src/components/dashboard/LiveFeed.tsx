'use client'

import { ChevronRight, TrendingUp, Target, Clock, DollarSign, Zap, Activity, ExternalLink, Link2, RefreshCw, Loader2 } from 'lucide-react'
import { useState, useEffect } from 'react'
import { cn } from '@/lib/utils'

interface LiveFeedProps {
  initialEvents?: any[]
}

interface LiveEvent {
  id: string
  type: string
  opportunity_id: string
  title: string
  score: number
  verdict: string
  timestamp: string
  old_score?: number
  new_score?: number
  reason?: string
}

export function LiveFeed({ initialEvents = [] }: LiveFeedProps) {
  const [events, setEvents] = useState<LiveEvent[]>(initialEvents)
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    // Simulate SSE connection
    const mockConnect = () => {
      setConnected(true)
      // Simulate live events
      const interval = setInterval(() => {
        const mockEvents: LiveEvent[] = [
          {
            id: `evt_${Date.now()}`,
            type: 'opportunity.new',
            opportunity_id: 'opp_new',
            title: 'New Protocol Launch',
            score: 68.5,
            verdict: 'speculative',
            timestamp: new Date().toISOString(),
          },
          {
            id: `evt_${Date.now() + 1}`,
            type: 'opportunity.score_changed',
            opportunity_id: 'opp_1',
            title: 'HyperScale L3 Airdrop',
            score: 79.2,
            verdict: 'worthwhile',
            old_score: 78.3,
            new_score: 79.2,
            reason: 'New audit report discovered',
            timestamp: new Date().toISOString(),
          },
        ]
        const event = mockEvents[Math.floor(Math.random() * mockEvents.length)]
        setEvents(prev => [event, ...prev].slice(0, 20))
      }
      
      mockConnect()
      return () => clearInterval(interval)
    }
  }, [])

  const formatTime = (iso: string) => {
    const date = new Date(iso)
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'opportunity.new': return <Activity className="h-4 w-4 text-green-400" />
      case 'opportunity.score_changed': return <TrendingUp className="h-4 w-4 text-yellow-400" />
      case 'opportunity.expired': return <Clock className="h-4 w-4 text-gray-400" />
      default: return <Activity className="h-4 w-4" />
    }
  }

  const getVerdictStyle = (verdict: string) => {
    const styles: Record<string, string> = {
      worthwhile: 'bg-green-500/20 text-green-400',
      speculative: 'bg-yellow-500/20 text-yellow-400',
      risky: 'bg-orange-500/20 text-orange-400',
      skip: 'bg-gray-500/20 text-gray-400',
      scam: 'bg-red-500/20 text-red-400',
    }
    return styles[verdict] || 'bg-gray-500/20 text-gray-400'
  }

  return (
    <div className="bg-nabu-bgSecondary border border-nabu-border rounded-xl overflow-hidden">
      <div className="p-4 border-b border-nabu-border flex items-center justify-between">
        <h3 className="text-lg font-semibold text-nabu-text">Live Feed</h3>
        <div className="flex items-center gap-2">
          <span className={cn(
            'flex h-2 w-2 rounded-full',
            connected ? 'bg-green-400 animate-pulse' : 'bg-red-400'
          )} />
          <span className="text-xs text-nabu-textSecondary">
            {connected ? 'Connected' : 'Connecting...'}
          </span>
        </div>
      </div>
      <div className="divide-y divide-nabu-border max-h-96 overflow-y-auto">
        {events.length === 0 ? (
          <div className="p-8 text-center text-nabu-textSecondary">
            <Loader2 className="h-8 w-8 mx-auto animate-spin text-nabu-accent-blue mb-2" />
            <p>Waiting for live events...</p>
          </div>
        ) : (
          events.map((event, index) => (
            <div key={event.id} className="p-4 hover:bg-nabu-bgTertiary/50 transition-colors border-b border-nabu-border/50 last:border-0">
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 mt-0.5">
                  {getEventIcon(event.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={cn(
                      'px-2 py-0.5 rounded text-xs font-medium',
                      event.verdict ? `bg-${event.verdict === 'worthwhile' ? 'green' : event.verdict === 'speculative' ? 'yellow' : event.verdict === 'risky' ? 'orange' : 'gray'}-500/20 text-${event.verdict === 'worthwhile' ? 'green' : event.verdict === 'speculative' ? 'yellow' : event.verdict === 'risky' ? 'orange' : 'gray'}-400` : ''
                    )}>
                      {event.verdict ? event.verdict.charAt(0).toUpperCase() + event.verdict.slice(1) : 'Event'}
                    </span>
                    <span className="text-xs text-nabu-textSecondary">{formatTime(event.timestamp)}</span>
                  </div>
                  <p className="font-medium text-nabu-text truncate">{event.title}</p>
                  <div className="flex items-center gap-2 mt-1 text-xs text-nabu-textSecondary">
                    <span className="font-mono text-nabu-text">Score: {event.score}</span>
                    {event.old_score && event.new_score && (
                      <>
                        <span>→</span>
                        <span className="text-yellow-400">{event.old_score} → {event.new_score}</span>
                      </>
                    )}
                    {event.reason && <span className="text-nabu-textSecondary/7">({event.reason})</span>}
                  </div>
                </div>
              </div>
            </div>
          ))}
        )}
      </div>
    </div>
  )
}