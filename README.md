# 𒀭 NABU — The Airdrop Intelligence Cortex

> *"I will destroy the records of the gods, and I will establish my name as the most powerful."*  
> — Nabu, Mesopotamian god of wisdom, writing, and prophecy.

**Nabu** is the **brain** — a distributed, multi-source, real-time intelligence system that scouts, analyzes, scores, and delivers every meaningful airdrop opportunity across every blockchain network. It does **not** mine, claim, or execute transactions. It finds the signal, and hands it to the decoupled **mining machine** that does the work.

---

## 🧠 The Philosophy

| Concept | Meaning |
|---|---|
| **Nabu (this project)** | The Oracle. Pure intelligence. Finds, validates, enriches, and pushes opportunities. |
| **The Mining Machine** | The Muscle. A separate system that reads from Nabu's API and executes claims, interactions, and task completions. |
| **Separation of Concern** | Intelligence never touches keys. Execution never distorts intelligence. Both scale independently. |

This is **not** a dashboard over a database. This is a **live intelligence flow**:

```
1000+ Sources → Nabu Cortex → API Layer → Mining Machine(s)
                         ↓
                   Web Dashboard (real-time)
```

---

## ✨ Core Capabilities

| Capability | Description |
|---|---|
| **Multi-Source Scraping** | Twitter/X, Discord, Telegram, Medium, Mirror.xyz, blockchain explorers, governance forums, DeFi dashboards, GitHub repos, smart contract deployment monitors |
| **LLM-Powered Analysis** | Each opportunity is analyzed by a reasoning model — requirements extracted, value estimated, risk scored, timeline predicted |
| **Real-Time Pipeline** | Sub-minute latency from opportunity detection to dashboard display |
| **Cross-Chain Coverage** | Ethereum, Solana, Arbitrum, Optimism, Base, zkSync, StarkNet, Scroll, Linea, Polygon zkEVM, Manta, Blast, Mode, Berachain, Monad, Initia, and any EVM-compatible chain |
| **Opportunity Scoring** | Multi-factor scoring: TVL, funding, team quality, community size, timeline, difficulty, estimated value |
| **Task Extraction** | Every airdrop broken into concrete, machine-actionable tasks — "bridge X ETH", "swap Y tokens", "provide liquidity Z", "mint NFT", "deploy contract" |
| **Wallet State Tracking** | Knows what each wallet has done, what it still needs, and re-scopes tasks per wallet |
| **Dashboard** | Real-time feed, wallet dashboard, analytics, search, filters, calendar |
| **Mining Machine API** | REST + WebSocket API for the decoupled miner to pull opportunities, get wallet-specific tasks, and report back status |
| **v2 Hardening** | On-chain wallet verification, dynamic scoring, cross-opportunity gas optimization, predictive discovery, per-machine abuse limits, fleet dashboard — see `docs/improvements-v2.md` |
| **Self-Evolution** | Speculative LLM pipeline, self-correction engine, historical pattern engine, adversary model, source authority scoring, gas-optimized routing — see `docs/nabu-self-evolution.md` |

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     NABU CORTEX                           │
│                                                           │
│  ┌──────────┐  ┌────────────┐  ┌──────────────────────┐  │
│  │ Scraper   │  │ Intelligence │  │ Opportunity Database │  │
│  │ Engine    │─▶│ Layer       │─▶│ (PostgreSQL + Redis)  │  │
│  │ (N nodes) │  │ (LLM + Rules)│  │                      │  │
│  └──────────┘  └────────────┘  └──────────────────────┘  │
│        │               │                   │              │
│        ▼               ▼                   ▼              │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                  API Layer (FastAPI)                  │  │
│  │   REST + WebSocket + Webhooks + Event Stream          │  │
│  └─────────────────────────────────────────────────────┘  │
│        │               │                   │              │
└────────────────────────┼───────────────────┼──────────────┘
                         │                   │
                         ▼                   ▼
                 ┌────────────┐    ┌──────────────────┐
                 │ Mining     │    │ Web Dashboard     │
                 │ Machine(s) │    │ (Next.js + shadcn)│
                 └────────────┘    └──────────────────┘
```

---

## 🔧 Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Go (high-throughput scraper workers) + Python/FastAPI (intelligence & API) |
| **Scraping** | Colly (Go), Playwright (headless browser), gRPC streams |
| **LLM** | Claude / GPT-4 / DeepSeek for opportunity analysis |
| **Database** | PostgreSQL (canonical), Redis (cache + queue + real-time) |
| **Queue** | RabbitMQ / Redis Streams |
| **Frontend** | Next.js 15, Tailwind, shadcn/ui, Recharts, TanStack Query |
| **Realtime** | WebSocket + Server-Sent Events |
| **Infra** | Docker Compose, Kubernetes, Prometheus + Grafana |

---

## 📂 Project Structure

```
nabu/
├── README.md
├── docs/
│   ├── architecture.md          # Full system architecture deep-dive
│   ├── scraper-engine.md        # Scraping strategies, sources, resilience
│   ├── intelligence-layer.md    # LLM analysis, scoring, task extraction
│   ├── api-spec.md              # Full API reference for mining machine
│   ├── dashboard-spec.md        # Dashboard UX, pages, components
│   └── deployment.md            # Docker, K8s, monitoring, scaling
├── crypto/                       # Crypto-specific helpers (signatures, RPC)
├── cmd/
│   ├── nabu-scraper/            # Scraper worker binary entrypoint
│   └── nabu-api/                # API server binary entrypoint
├── internal/
│   ├── scraper/                 # Scraper engine (Go)
│   ├── intelligence/            # Analysis & scoring (Python)
│   ├── db/                      # Database models & migrations
│   ├── api/                     # FastAPI application
│   └── types/                   # Shared data types
├── dashboard/                   # Next.js frontend
│   ├── app/
│   ├── components/
│   └── lib/
├── deploy/
│   ├── docker-compose.yml
│   ├── kubernetes/
│   └── prometheus/
└── scripts/
    ├── bootstrap.sh
    └── migrate.sh
```

---

## 🔗 The Mining Machine Interface

Nabu exposes a single, clean, versioned API that the decoupled mining machine consumes:

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/opportunities` | GET | List all active airdrop opportunities |
| `/api/v1/opportunities/:id` | GET | Single opportunity detail with all tasks |
| `/api/v1/opportunities/:id/tasks` | GET | Machine-actionable tasks for this airdrop |
| `/api/v1/wallets/:address/tasks` | GET | Personalized tasks for a specific wallet |
| `/api/v1/wallets/:address/status` | PATCH | Report task completion, tx hash, gas used |
| `/api/v1/events` | GET | Server-Sent Events stream for real-time updates |
| `ws://nabu/ws` | WS | Full-duplex real-time channel |

The mining machine is **stateless from Nabu's perspective** — it polls or streams, reports back, and Nabu updates the intelligence.

---

## 🚀 Getting Started

```bash
# Clone
git clone https://github.com/your-org/nabu.git
cd nabu

# Start infrastructure (PostgreSQL, Redis, RabbitMQ)
docker compose -f deploy/docker-compose.yml up -d infra

# Run database migrations
make migrate

# Start scraper workers (requires API keys in .env)
make run-scrapers

# Start intelligence layer
make run-intelligence

# Start API server
make run-api

# Start dashboard dev server
cd dashboard && npm install && npm run dev
```

---

## 🗺️ Roadmap

### Phase 1 — Foundation (Weeks 1-2)
- [ ] PostgreSQL schema: opportunities, tasks, wallets, events
- [ ] Scraper skeleton: Twitter/X API, Telegram client, Discord bot
- [ ] Basic LLM analysis pipeline
- [ ] Opportunity scoring v1
- [ ] Simple API: list + detail endpoints
- [ ] Dashboard MVP: real-time feed, search, filters

### Phase 2 — Intelligence (Weeks 3-4)
- [ ] Cross-chain coverage (15+ chains)
- [ ] Smart contract deployment monitors (Etherscan + custom RPC)
- [ ] GitHub repository watcher (new projects, audit reports)
- [ ] Governance proposal parser (Snapshot, Tally)
- [ ] Testnet deployment tracker
- [ ] Task extraction engine v2
- [ ] Wallet state tracking

### Phase 3 — Scale (Weeks 5-6)
- [ ] Distributed scraper fleet (Kubernetes)
- [ ] WebSocket + SSE for real-time delivery
- [ ] Mining machine client library (Python SDK)
- [ ] Analytics dashboard (charts, trends, value tracking)
- [ ] Alert system (Telegram, Discord webhook)
- [ ] Historical data warehouse
- [ ] Rate limit management & proxy rotation

### Phase4 — Autonomous (Week 7+)
- [ ] Predictive scoring: ML model on past airdrop outcomes
- [ ] Automated opportunity discovery (LLM agents browsing new protocols)
- [ ] Community sentiment analysis
- [ ] Gas cost estimation & ROI calculator
- [ ] Multi-wallet orchestration support in API
- [ ] Public dashboard (read-only) for community

### Phase6 — Self-Aware Oracle (Week 9+)
- [ ] Speculative analysis pipeline (parallel LLM, first-wins)
- [ ] Self-correction engine (feedback loop, gradient descent on weights)
- [ ] Historical pattern engine (outcome database, similar-opportunity lookup)
- [ ] Adversary model (scam likelihood scoring)
- [ ] Source authority scoring (credibility-weighted signals)
- [ ] Gas-optimized task routing (cheapest path per task)
- [ ] Continuous A/B testing of scoring models
> See `docs/nabu-self-evolution.md` for full design.

---

## 📜 License

MIT — This is the brain. Build your own muscle.

---

> *"Nabu holds the tablet of destiny. This project aims to do the same for airdrops."*
