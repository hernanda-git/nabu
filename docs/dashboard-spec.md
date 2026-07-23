# 🖥️ Web Dashboard Specification

> *"The war room where intelligence becomes action."*

---

## 1. Stack

| Technology | Purpose |
|---|---|
| **Next.js 15** (App Router) | Framework |
| **Tailwind CSS** + **shadcn/ui** | Styling & components |
| **Recharts** | Charts & graphs |
| **TanStack Query** | Server state & caching |
| **TanStack Table** | Data tables |
| **Zustand** | Client state |
| **WebSocket/SSE** | Real-time data |
| **date-fns** | Date formatting |
| **react-hook-form** + **zod** | Forms & validation |
| **Lucide React** | Icons |

---

## 2. Pages & Routes

```
/                          → Dashboard (home / overview)
/opportunities             → Opportunity board (full list)
/opportunities/:slug       → Single opportunity detail
/wallets/:address          → Wallet dashboard
/analytics                 → Charts, trends, statistics
/calendar                  → Timeline view of upcoming claims
/settings                  → API keys, webhooks, preferences
/search                    → Global search
/machines                  → Mining machine fleet (status, assignments, abuse) [v2]
/watchlist                 → Predictive leads from anomaly detection [v2]
```

---

## 3. Page Wireframes

### 3.1 Dashboard (`/`)

```
┌──────────────────────────────────────────────────────────────────────┐
│ 🔍  Search...         ⚙️  Filters  📅 Calendar  📊 Analytics  👤 │
├──────────────────────────────────────────────────────────────────────┤
│ 📊 Summary Cards                                                        │
│ ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│ │ Active  │ │ High    │ │ Tasks    │ │ Est.     │ │ Gas      │    │
│ │ 247 opps│ │ Priority│ │ Remaining│ │ Total    │ │ Spent    │    │
│ │         │ │ 42🔥   │ │ 1,893   │ │ $125K-$1M│ │ $342     │    │
│ └─────────┘ └─────────┘ └──────────┘ └──────────┘ └──────────┘    │
├──────────────────────────────────────────────────────────────────────┤
│ 📡 Live Feed (SSE/WebSocket)    │ 📊 Score Distribution              │
│ ┌─────────────────────────────┐ │ ┌──────────────────────────────┐ │
│ │ 🔥 HyperScale L3   78.3    │ │ │   ██                          │ │
│ │   Just now · Worthwhile     │ │ │ ██████                        │ │
│ │─────────────────────────────│ │ │██████████                     │ │
│ │ ⚡ Nova Chain      72.1    │ │ │██████████████                  │ │
│ │   2m ago · Speculative      │ │ │████████████████████████       │ │
│ │─────────────────────────────│ │ │ 0  20  40  60  80  100       │ │
│ │ 🟡 Quantum DEX    68.5    │ │ └──────────────────────────────┘ │
│ │   5m ago · Worthwhile       │ │                                  │ │
│ │─────────────────────────────│ │ 📊 Category Breakdown           │ │
│ │ ⚪ Pulse Bridge   45.2    │ │ ┌──────────────────────────────┐ │
│ │   12m ago · Risky          │ │ │ L2      ████████████  45    │ │
│ └─────────────────────────────┘ │ │ DeFi    ████████████████ 82 │ │
│                                 │ │ DEX     ██████████     38  │ │
│                                 │ │ Bridge  ████          15  │ │
│                                 │ │ NFT     ███           12  │ │
│                                 │ └──────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────────┤
│ 🏆 Top Opportunities (Table)                                         │
│ ┌──────┬──────────┬──────┬───────┬────────┬──────────┬────────┐   │
│ │ Score│ Protocol │ Chain│ Value │ Tasks  │ Deadline │ Status │   │
│ ├──────┼──────────┼──────┼───────┼────────┼──────────┼────────┤   │
│ │ 78.3 │HyperScale│ ETH  │$500-5K│ 12/5   │ Aug 15   │ 🔥     │   │
│ │ 72.1 │Nova Chain│ SOL  │$200-2K│ 8/3    │ Jul 31   │ ⚡     │   │
│ │ 68.5 │Quantum   │ARB   │$300-3K│ 6/1    │ Aug 20   │ 🟡     │   │
│ │ 45.2 │Pulse Brdg│ETH   │$50-500│ 4/0    │ Sep 1    │ ⚪     │   │
│ └──────┴──────────┴──────┴───────┴────────┴──────────┴────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.2 Opportunity Detail (`/opportunities/:slug`)

```
┌──────────────────────────────────────────────────────────────────────┐
│ ← Back                                        ★ Save  🔗 Share       │
├──────────────────────────────────────────────────────────────────────┤
│ HyperScale L3 Airdrop Season 1                                       │
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │ Score: 78.3 │ Difficulty: 6.5/10 │ Verdict: Worthwhile ✅       │ │
│ │ Value: $500 - $5,000 │ Risk: Medium ⚠️  │ Confidence: Medium   │ │
│ └──────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│ 📋 Overview                                                          │
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │ HyperScale is a new Ethereum L3 rollup built on Arbitrum,        │ │
│ │ using Celestia for data availability. They've raised $15M from... │ │
│ │                                                                   │ │
│ │ 🔗 Website  🐦 Twitter  💬 Discord  📄 Docs  📂 GitHub          │ │
│ └──────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│ 📅 Timeline                                                        │
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │         ┌──────┐       ┌────────┐      ┌────────┐               │ │
│ │ Detected│      │ Claim │  Start │ Claim│  End   │  TGE          │ │
│ │ Jul 23  │──────│──────>│Aug 15  │──────│Sep 15  │  Aug 15       │ │
│ │         │      │       │        │      │        │               │ │
│ │         │  23d │       │  23d   │      │  31d   │               │ │
│ └──────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│ 📋 Tasks (12 total)                                                 │
│ ┌────┬─────────┬──────────────────────────────┬──────┬────────┬───┐  │
│ │ #  │ Type    │ Description                   │ Gas  │ Time   │ ⏺ │  │
│ ├────┼─────────┼──────────────────────────────┼──────┼────────┼───┤  │
│ │ 1  │ Bridge  │ Bridge 0.5 ETH → HyperScale │ $15  │ 5 min  │ ⬜ │  │
│ │ 2  │ Swap    │ Swap 2 ETH → HSC             │ $5   │ 2 min  │ ⬜ │  │
│ │ 3  │ LP      │ Provide ETH/HSC liquidity    │ $8   │ 3 min  │ ⬜ │  │
│ │ 4  │ NFT     │ Mint Genesis NFT             │ $2   │ 1 min  │ ⬜ │  │
│ │ 5  │ Deploy  │ Deploy a contract            │ $10  │ 10 min │ ⬜ │  │
│ │ 6  │ Stake   │ Stake 5 HSC                  │ $3   │ 2 min  │ ⬜ │  │
│ │ ...│         │                              │      │        │   │  │
│ └────┴─────────┴──────────────────────────────┴──────┴────────┴───┘  │
│                                                                        │
│ ⚠️ Risk Assessment                                                   │
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │ Overall Risk: Medium                                               │ │
│ │                                                                   │ │
│ │ 🟡 Team Anonymous       — Pseudonymous, no doxxed founders      │ │
│ │ 🟢 Code Audited         — Trail of Bits audit (Jun 2026)         │ │
│ │ 🟢 VC Backing           — $15M from a16z, Paradigm               │ │
│ │ 🟢 Low Honeypot Risk    — Standard upgradeable proxy, 48h TL    │ │
│ └──────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│ 📊 Similar Opportunities                                             │
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │ 🔥 Scroll L3 Airdrop    74.2  │ ⚡ zkSync Era        69.8       │ │
│ │ 🟡 Linea Park          62.1  │ ⚪ Manta Pacific     55.4       │ │
│ └──────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.3 Wallet Dashboard (`/wallets/:address`)

```
┌──────────────────────────────────────────────────────────────────────┐
│ 💼 Wallet: 0x1234...abcd                    [🔗 Copy] [📊 Export]   │
├──────────────────────────────────────────────────────────────────────┤
│ Summary                                                              │
│ ┌───────────┐ ┌───────────┐ ┌──────────┐ ┌──────────┐             │
│ │ Engaged   │ │ Tasks Done│ │ Gas Spent│ │ Est. Earn│             │
│ │ 12 opps   │ │ 45/120    │ │ $342     │ │ $2K-15K  │             │
│ └───────────┘ └───────────┘ └──────────┘ └──────────┘             │
├──────────────────────────────────────────────────────────────────────┤
│ 📋 My Opportunities                                                  │
│ ┌──────┬──────────┬──────┬────────┬──────────┬─────────┬─────────┐ │
│ │ Score│ Protocol │Tasks │ Done % │ Est.     │ Deadline│ Status  │ │
│ ├──────┼──────────┼──────┼────────┼──────────┼─────────┼─────────┤ │
│ │ 78.3 │HyperScale│ 12   │ ████░░ │ $500-5K  │Aug 15   │ ▶️ 42%  │ │
│ │ 72.1 │Nova Chain│ 8    │ ██████ │ $200-2K  │Jul 31   │ ▶️ 75%  │ │
│ │ 68.5 │Quantum   │ 6    │ ██░░░░ │ $300-3K  │Aug 20   │ ▶️ 25%  │ │
│ │ 45.2 │Pulse Brdg│ 4    │ ░░░░░░ │ $50-500  │Sep 1    │ ⏹ 0%   │ │
│ └──────┴──────────┴──────┴────────┴──────────┴─────────┴─────────┘ │
│                                                                        │
│ ⏱️ Recent Activity                                                   │
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │ 2m ago  ✅ Bridged 0.5 ETH → HyperScale (tx: 0x7a1b...)        │ │
│ │ 15m ago ✅ Swapped 2 ETH → HSC on HyperScale DEX                │ │
│ │ 1h ago  🔴 Failed to mint Genesis NFT — insufficient gas       │ │
│ └──────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.4 Analytics (`/analytics`)

```
┌──────────────────────────────────────────────────────────────────────┐
│ 📊 Analytics               [7d ▼]  [All Chains ▼]                    │
├──────────────────────────────────────────────────────────────────────┤
│ ┌────────────────────────┐  ┌────────────────────────┐              │
│ │ 📈 Opportunities Over Time │ │ 🏆 Top Protocols by Value │          │
│ │                          │  │                        │              │
│ │    ██                    │  │ HyperScale    ████████ │              │
│ │  ██████                  │  │ Nova Chain    ██████   │              │
│ │ ██████████ ██            │  │ Quantum DEX   ████     │              │
│ │ ████████████████ ██████  │  │ ...                    │              │
│ │ Jul 14        Jul 23     │  │                        │              │
│ └────────────────────────┘  └────────────────────────┘              │
│                                                                        │
│ ┌────────────────────────┐  ┌────────────────────────┐              │
│ │ 🎯 Success Rate (Claimed) │ │ 💰 Est. Earnings by Month │          │
│ │                          │  │                          │          │
│ │ High: 78%    ████████   │  │ Jul     ████████  $2.5K  │          │
│ │ Med:  52%    █████      │  │ Aug     ████████████ $4K  │          │
│ │ Low:  18%    ██         │  │ Sep     ██ $500 (est)     │          │
│ └────────────────────────┘  └────────────────────────┘              │
│                                                                        │
│ 📋 All Opportunities (Table with column visibility)                  │
│ ┌──────┬──────────┬──────┬───────┬────────┬──────────┬────────┬────┐ │
│ │Score │Protocol  │Chain │Value  │Tasks   │Deadline  │Status  │   │ │
│ │78.3  │HyperScale│ETH   │$500-5K│12/5    │Aug 15    │🔥     │   │ │
│ │72.1  │Nova Chain│SOL   │$200-2K│8/3     │Jul 31    │⚡     │   │ │
│ │68.5  │Quantum   │ARB   │$300-3K│6/1     │Aug 20    │🟡     │   │ │
│ │...   │          │      │       │        │          │        │   │ │
│ └──────┴──────────┴──────┴───────┴────────┴──────────┴────────┴────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.5 Calendar (`/calendar`)

```
┌──────────────────────────────────────────────────────────────────────┐
│ 📅 Airdrop Calendar          August 2026                   [Month ▼] │
├──────────────────────────────────────────────────────────────────────┤
│ Mo    Tu    We    Th    Fr    Sa    Su                                 │
│                                  1     2                              │
│  3     4     5     6     7     8     9                               │
│ 10    11    12    13    14    15████ 16                               │
│                             │HyperScale│                              │
│                             │Claim Open│                             │
│ 17    18    19    20████  21    22    23                              │
│                │Quantum   │                                           │
│                │Snapshot  │                                           │
│ 24    25    26    27    28    29    30                               │
│ 31                                                                     │
├──────────────────────────────────────────────────────────────────────┤
│ 📋 Upcoming This Month                                               │
│ ┌──────┬──────────────┬──────────┬──────────┬─────────┐             │
│ │ Date │ Event        │ Protocol │ Type     │ Value   │             │
│ ├──────┼──────────────┼──────────┼──────────┼─────────┤             │
│ │ Aug15│ 🔥 Claim Open│HyperScale│ L3       │ $500-5K │             │
│ │ Aug20│ 🟡 Snapshot   │Quantum   │ DEX      │ $300-3K │             │
│ │ Aug28│ ⚪ TGE        │Pulse     │ Bridge   │ $50-500 │             │
│ └──────┴──────────────┴──────────┴──────────┴─────────┘             │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 4. Component Tree

```
app/
├── layout.tsx                  # Root layout (sidebar, header, theme)
├── page.tsx                    # Dashboard (redirect from / or main page)
├── opportunities/
│   ├── page.tsx                # Full opportunity table + filters
│   └── [slug]/
│       └── page.tsx            # Single opportunity detail
├── wallets/
│   └── [address]/
│       └── page.tsx            # Wallet dashboard
├── analytics/
│   └── page.tsx                # Charts and statistics
├── calendar/
│   └── page.tsx                # Calendar view
├── settings/
│   └── page.tsx                # Settings
└── search/
    └── page.tsx                # Global search results

components/
├── layout/
│   ├── sidebar.tsx             # Navigation sidebar
│   ├── header.tsx              # Top bar (search, notifications, profile)
│   └── mobile-nav.tsx          # Mobile navigation
├── dashboard/
│   ├── summary-cards.tsx       # Summary stat cards (5)
│   ├── live-feed.tsx           # Real-time opportunity feed
│   ├── score-distribution.tsx  # Score distribution chart
│   ├── category-breakdown.tsx  # Category pie/bar chart
│   └── top-opportunities.tsx   # Top opportunities table
├── opportunities/
│   ├── opportunity-card.tsx    # Card for feed view
│   ├── opportunity-table.tsx   # Sortable/filterable table
│   ├── opportunity-detail.tsx  # Full detail view
│   ├── tasks-list.tsx          # Task list with progress
│   ├── timeline.tsx            # Visual timeline
│   ├── risk-assessment.tsx     # Risk factor display
│   └── similar-opportunities.tsx # Related opportunities
├── wallets/
│   ├── wallet-summary.tsx      # Wallet stat cards
│   ├── wallet-opportunities.tsx# Wallet's opportunity list
│   ├── task-progress.tsx       # Per-opportunity task progress bar
│   └── activity-feed.tsx       # Recent activities
├── analytics/
│   ├── opportunities-chart.tsx # Time series chart
│   ├── top-protocols.tsx       # Top protocols by value
│   ├── success-rate.tsx        # Success rate by difficulty
│   └── earnings-chart.tsx      # Earnings over time
├── calendar/
│   └── calendar-view.tsx       # Full calendar component
├── search/
│   └── search-results.tsx      # Search results display
├── shared/
│   ├── data-table.tsx          # TanStack Table wrapper
│   ├── stat-card.tsx           # Single stat card
│   ├── filter-bar.tsx          # Reusable filter controls
│   ├── score-badge.tsx         # Color-coded score badge
│   ├── verdict-badge.tsx       # Verdict label (worthwhile/speculative/etc)
│   └── chain-icon.tsx          # Blockchain network icon
└── providers/
    ├── websocket-provider.tsx   # WebSocket connection context
    └── theme-provider.tsx       # Theme (dark/light)
```

---

## 5. Real-Time Architecture

```typescript
// WebSocket Provider
function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const [ws] = useState(() => new WebSocket('wss://nabu.internal:8443/api/v1/ws'));

  useEffect(() => {
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      // Dispatch to TanStack Query invalidation
      queryClient.invalidateQueries({ queryKey: ['opportunities'] });
      // Or push to Zustand store for live feed
      useLiveFeedStore.getState().pushEvent(msg);
    };
    return () => ws.close();
  }, []);

  return <WebSocketContext.Provider value={ws}>{children}</WebSocketContext.Provider>;
}

// SSE Fallback for browsers without WebSocket
function useSSE() {
  useEffect(() => {
    const source = new EventSource('/api/v1/events/stream');
    source.addEventListener('opportunity.new', (e) => {
      queryClient.invalidateQueries({ queryKey: ['opportunities'] });
    });
    return () => source.close();
  }, []);
}
```

**Query Invalidation Strategy:**
```typescript
// TanStack Query configuration
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,        // 30s before background refetch
      gcTime: 5 * 60_000,       // 5min cache
      refetchOnWindowFocus: true,
    },
  },
});

// WebSocket messages selectively invalidate
const EVENT_MAP = {
  'opportunity.new':       [['opportunities']],
  'opportunity.updated':   [['opportunities'], ['opportunity', slug]],
  'opportunity.expired':   [['opportunities']],
  'wallet.task_completed': [['wallet', address]],
  'wallet.updated':        [['wallet', address]],
  'score.changed':         [['opportunities'], ['analytics']],
};
```

---

## 6. Theme & Design System

**Color Palette** (Dark-first, light optional):

| Token | Value | Usage |
|---|---|---|
| `--bg-primary` | `#0a0a0f` | Main background |
| `--bg-secondary` | `#14141f` | Card background |
| `--bg-tertiary` | `#1c1c2e` | Elevated surfaces |
| `--border` | `#2a2a3e` | Borders |
| `--text-primary` | `#e8e8f0` | Main text |
| `--text-secondary` | `#8888a0` | Secondary text |
| `--accent-green` | `#22c55e` | Worthwhile / success |
| `--accent-yellow` | `#eab308` | Speculative |
| `--accent-orange` | `#f97316` | Risky |
| `--accent-red` | `#ef4444` | Scam / critical risk |
| `--accent-blue` | `#3b82f6` | Score bar, links |
| `--score-high` | `#22c55e` | Score ≥ 80 |
| `--score-mid` | `#eab308` | Score 60-79 |
| `--score-low` | `#f97316` | Score 40-59 |
| `--score-trash` | `#ef4444` | Score < 40 |

**Typography**:
- Font: `'Inter', system-ui, sans-serif`
- Monospace: `'JetBrains Mono', monospace` (for addresses, tx hashes, code)

---

## 7. State Management

```typescript
// Zustand stores
interface LiveFeedStore {
  events: LiveEvent[];
  pushEvent: (event: LiveEvent) => void;
  clear: () => void;
}

interface FilterStore {
  filters: OpportunityFilters;
  setFilter: (key: string, value: any) => void;
  resetFilters: () => void;
}

interface WalletStore {
  activeWallet: string | null;
  wallets: string[];
  setActiveWallet: (address: string) => void;
  addWallet: (address: string) => void;
}
```

---

## 8. API Integration Patterns

```typescript
// TanStack Query hooks
function useOpportunities(filters: OpportunityFilters) {
  return useQuery({
    queryKey: ['opportunities', filters],
    queryFn: () => fetch(`/api/v1/opportunities?${buildQuery(filters)}`).then(r => r.json()),
    staleTime: 30_000,
  });
}

function useWalletTasks(address: string) {
  return useQuery({
    queryKey: ['wallet', address, 'tasks'],
    queryFn: () => fetch(`/api/v1/wallets/${address}/tasks`).then(r => r.json()),
    staleTime: 60_000,
  });
}

function useReportTaskMutation() {
  return useMutation({
    mutationFn: (data: TaskReport) =>
      fetch(`/api/v1/wallets/${data.address}/status`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['wallet', variables.address] });
    },
  });
}
```

---

## 9. Dashboard Auto-Refresh Policy

| Section | Poll Interval | Real-time |
|---|---|---|
| Live Feed | N/A | WebSocket push |
| Summary Cards | 30s | SSE event on change |
| Top Opportunities | 30s | SSE event on change |
| Opportunity Detail | 15s | WebSocket per-opp updates |
| Wallet Dashboard | 60s | WebSocket on task report |
| Analytics | 5min | Manual refresh button |
| Calendar | 5min | On navigation |
