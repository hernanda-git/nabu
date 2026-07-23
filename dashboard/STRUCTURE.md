# nabu dashboard - Next.js 15 + TypeScript

dashboard/
├── package.json
├── tsconfig.json
├── next.config.js
├── tailwind.config.ts
├── postcss.config.js
├── .eslintrc.json
├── .prettierrc
├── public/
│   └── favicon.ico
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── globals.css
│   │   ├── providers.tsx
│   │   ├── opportunities/
│   │   │   ├── page.tsx
│   │   │   └── [slug]/
│   │   │       └── page.tsx
│   │   ├── wallets/
│   │   │   └── [address]/
│   │   │       └── page.tsx
│   │   ├── analytics/
│   │   │   └── page.tsx
│   │   ├── calendar/
│   │   │   └── page.tsx
│   │   ├── machines/
│   │   │   └── page.tsx
│   │   ├── watchlist/
│   │   │   └── page.tsx
│   │   ├── settings/
│   │   │   └── page.tsx
│   │   └── search/
│   │       └── page.tsx
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Header.tsx
│   │   │   └── MobileNav.tsx
│   │   ├── dashboard/
│   │   │   ├── SummaryCards.tsx
│   │   │   ├── LiveFeed.tsx
│   │   │   ├── ScoreDistribution.tsx
│   │   │   ├── CategoryBreakdown.tsx
│   │   │   └── TopOpportunities.tsx
│   │   ├── opportunities/
│   │   │   ├── OpportunityCard.tsx
│   │   │   ├── OpportunityTable.tsx
│   │   │   ├── OpportunityDetail.tsx
│   │   │   ├── TasksList.tsx
│   │   │   ├── Timeline.tsx
│   │   │   ├── RiskAssessment.tsx
│   │   │   └── SimilarOpportunities.tsx
│   │   ├── wallets/
│   │   │   ├── WalletSummary.tsx
│   │   │   ├── WalletOpportunities.tsx
│   │   │   ├── TaskProgress.tsx
│   │   │   ├── ActivityFeed.tsx
│   │   │   └── ExecutionPlan.tsx
│   │   ├── analytics/
│   │   │   ├── OpportunitiesChart.tsx
│   │   │   ├── TopProtocols.tsx
│   │   │   ├── SuccessRate.tsx
│   │   │   └── EarningsChart.tsx
│   │   ├── calendar/
│   │   │   └── CalendarView.tsx
│   │   ├── machines/
│   │   │   ├── MachineGrid.tsx
│   │   │   ├── MachineCard.tsx
│   │   │   └── MachineDetail.tsx
│   │   ├── search/
│   │   │   └── SearchResults.tsx
│   │   ├── shared/
│   │   │   ├── DataTable.tsx
│   │   │   ├── StatCard.tsx
│   │   │   ├── FilterBar.tsx
│   │   │   ├── ScoreBadge.tsx
│   │   │   ├── VerdictBadge.tsx
│   │   │   └── ChainIcon.tsx
│   │   └── providers/
│   │       ├── WebSocketProvider.tsx
│   │       └── ThemeProvider.tsx
│   ├── lib/
│   │   ├── api.ts
│   │   ├── websocket.ts
│   │   ├── queryClient.ts
│   │   ├── utils.ts
│   │   └── constants.ts
│   ├── hooks/
│   │   ├── useOpportunities.ts
│   │   ├── useWallet.ts
│   │   ├── useMachines.ts
│   │   ├── useWebSocket.ts
│   │   └── useRealtime.ts
│   ├── store/
│   │   ├── filters.ts
│   │   ├── wallet.ts
│   │   └── theme.ts
│   └── types/
│       ├── api.ts
│       ├── opportunity.ts
│       ├── wallet.ts
│       ├── machine.ts
│       └── event.ts