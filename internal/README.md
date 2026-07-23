# nabu internal packages structure

internal/
├── scraper/           # Go scrapers
│   ├── base.go       # Base scraper, publisher, rate limiter
│   ├── twitter.go    # Twitter/X scraper
│   ├── telegram.go   # Telegram scraper (MTProto)
│   ├── discord.go    # Discord scraper
│   ├── blockchain.go # EVM RPC + event monitors
│   ├── github.go     # GitHub GraphQL scraper
│   └── web.go        # Playwright web scraper
├── intelligence/      # Python intelligence workers
│   ├── analysis.py   # LLM analysis pipeline
│   ├── scoring.py    # Scoring engine
│   ├── tasks.py      # Task extraction
│   ├── scam.py       # Scam detection
│   ├── patterns.py   # Historical patterns
│   ├── adversary.py  # Adversary model
│   ├── authority.py  # Source authority
│   ├── gas.py        # Gas optimization
│   ├── outcomes.py   # Outcome tracking
│   └── router.py     # Speculative LLM router
├── db/               # Database models + migrations
│   ├── models.py     # SQLAlchemy models
│   ├── migrations/   # Alembic migrations
│   └── repository.py # Data access layer
├── api/              # FastAPI application
│   ├── main.py       # App factory
│   ├── routes/       # API routes
│   │   ├── opportunities.py
│   │   ├── wallets.py
│   │   ├── machines.py
│   │   ├── events.py
│   │   └── analytics.py
│   ├── schemas.py    # Pydantic schemas
│   ├── auth.py       # JWT + IP allowlist
│   └── middleware.py # Rate limiting, logging
├── types/            # Shared types (generated)
│   ├── events.py     # RawEvent, NormalizedEvent
│   ├── opportunities.py
│   ├── tasks.py
│   └── scoring.py
└── cron/             # Cron job handlers
    ├── source_watch.py
    ├── deep_analysis.py
    ├── self_correction.py
    ├── market_regime.py
    ├── historical_patterns.py
    ├── gas_costs.py
    └── health_check.py