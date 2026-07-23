# 🏗️ System Architecture Deep-Dive

> **Version:** 1.0  
> **Status:** Design Document  
> **Last Updated:** 2026-07-23

---

## 1. High-Level Architecture

Nabu is a **polyglot distributed system** built around a **pipeline architecture** with event-driven processing at every stage.

```
                     ┌──────────────────────────────────┐
                     │         INTERNET                  │
                     │  Twitter  Telegram  Discord  Web  │
                     │  Blockchains  GitHub  Forums      │
                     └──────────┬───────────────────────┘
                                │
              ┌─────────────────┼─────────────────────┐
              │                 │                      │
              ▼                 ▼                      ▼
      ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐
      │ Twitter      │ │ Telegram     │ │ Blockchain       │
      │ Scraper Node │ │ Scraper Node │ │ Scraper Node     │ ... N scrapers
      └──────┬───────┘ └──────┬───────┘ └────────┬─────────┘
             │                │                   │
             └────────────────┼───────────────────┘
                              │ Raw opportunity events
                              ▼
                    ┌──────────────────┐
                    │   RabbitMQ       │
                    │  (Event Queue)   │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
      ┌────────────┐ ┌────────────┐ ┌────────────┐
      │ Dedup &    │ │ Validation │ │ Enrichment │  Intelligence Workers
      │ Normalize  │ │ & Filter   │ │ & Scoring  │  (Python/FastAPI)
      └──────┬─────┘ └──────┬─────┘ └──────┬─────┘
             │              │              │
             └──────────────┼──────────────┘
                            │ Scored + Enriched
                            ▼
                  ┌──────────────────┐
                  │   PostgreSQL     │
                  │  (Canonical DB)  │
                  └────────┬─────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
      ┌──────────────┐       ┌──────────────────┐
      │  Redis Cache  │       │     API Layer     │
      │  (Hot data)   │       │  (FastAPI/Go)     │
      └──────────────┘       └────────┬─────────┘
                                      │
                         ┌────────────┼─────────────┐
                         │            │              │
                         ▼            ▼              ▼
                 ┌──────────┐  ┌──────────┐  ┌────────────┐
                 │ Dashboard│  │ Mining   │  │ Webhooks / │
                 │ (Next.js) │  │ Machine  │  │ Alerts     │
                 └──────────┘  │ API      │  └────────────┘
                               └──────────┘
```

---

## 2. Data Flow Pipeline

### Stage 1: Ingestion (Scraper Engine)

Each scraper is a **long-lived goroutine** (or process) that connects to a source and streams events into RabbitMQ.

**Scraper types:**

| Type | Protocol | Rate Limit Strategy |
|---|---|---|
| Twitter/X Scraper | GraphQL + REST API | Token bucket per account, proxy rotation |
| Telegram Scraper | MTProto (Telethon) | Session pooling, multi-account |
| Discord Scraper | Gateway API + REST | Shard-aware connection pooling |
| Blockchain RPC Scraper | JSON-RPC (WebSocket) | Connection pooling, batch requests |
| Etherscan Scraper | REST API | API key rotation, cached responses |
| GitHub Scraper | GraphQL API | Token rotation, conditional requests |
| Web Scraper | HTTP (Playwright) | Proxy rotation, fingerprint rotation |
| RSS/Feed Scraper | HTTP polling | Conditional GET, 5-min intervals |

**Raw event schema (RabbitMQ):**

```json
{
  "id": "evt_abc123def456",
  "source": "twitter",
  "source_id": "1857234567890123456",
  "collected_at": "2026-07-23T09:42:00Z",
  "raw": { "text": "...", "author": "...", "url": "...", "media": [] },
  "type": "announcement",
  "confidence": 0.85
}
```

### Stage 2: Deduplication & Normalization

A set of **Python workers** consuming from RabbitMQ:

1. **Exact dedup**: SHA-256 of normalized content → Redis bloom filter
2. **Semantic dedup**: Embedding cosine similarity on announcement text (threshold > 0.92)
3. **Cross-source dedup**: Same announcement from Twitter + Telegram → merged with multi-source metadata
4. **Normalization**: Standardized schema across all sources

**Normalized opportunity schema:**

```json
{
  "id": "opp_a1b2c3d4",
  "title": "Ethereum L3 Protocol Airdrop",
  "protocol_name": "HyperScale",
  "category": "l3_rollup",
  "sources": [
    {"type": "twitter", "url": "https://twitter.com/...", "collected_at": "..."},
    {"type": "telegram", "channel": "@hyperscale", "collected_at": "..."}
  ],
  "status": "pending_analysis",
  "detected_at": "2026-07-23T09:42:00Z",
  "confidence_score": 0.87,
  "network": ["ethereum", "arbitrum"],
  "requirements_hint": {"bridging": true, "min_tvl": "$100"}
}
```

### Stage 3: Intelligence Analysis (The Oracle)

Each opportunity goes through a **multi-model LLM pipeline**:

```
Raw  ──► Context Builder ──► LLM Analysis ──► Structured Output
Data      (builds prompt     (Claude/GPT-4/    (JSON schema
          from normalized     DeepSeek)         validated by
          opportunity data)                     Pydantic)
```

**Analysis output:**

```json
{
  "opportunity_id": "opp_a1b2c3d4",
  "analysis_version": 2,
  "analyzed_at": "2026-07-23T09:43:15Z",
  "estimated_value": {
    "min_tokens": 100,
    "max_tokens": 500,
    "estimated_usd_min": 500,
    "estimated_usd_max": 5000,
    "confidence": "medium",
    "token_name": "HSC",
    "token_type": "governance"
  },
  "timeline": {
    "snapshot_date": null,
    "claim_start": "2026-08-15T00:00:00Z",
    "claim_end": "2026-09-15T00:00:00Z",
    "tge_date": "2026-08-15T00:00:00Z"
  },
  "requirements": [
    {"id": "req_1", "type": "bridge", "description": "Bridge >= 0.5 ETH from Ethereum to HyperScale", "optional": false, "estimated_gas_usd": 15},
    {"id": "req_2", "type": "swap", "description": "Swap >= 2 ETH for native token on HyperScale DEX", "optional": false, "estimated_gas_usd": 5},
    {"id": "req_3", "type": "lp", "description": "Provide liquidity ETH/HSC on HyperScale DEX", "optional": true, "estimated_gas_usd": 8},
    {"id": "req_4", "type": "mint_nft", "description": "Mint free Genesis NFT", "optional": true, "estimated_gas_usd": 2},
    {"id": "req_5", "type": "deploy_contract", "description": "Deploy one smart contract on HyperScale", "optional": false, "estimated_gas_usd": 10}
  ],
  "risk_assessment": {
    "overall_risk": "medium",
    "factors": [
      {"name": "team_anonymous", "risk": "high", "detail": "Team is pseudonymous with no doxxed founders"},
      {"name": "code_audited", "risk": "low", "detail": "Contracts audited by Trail of Bits"},
      {"name": "vc_backing", "risk": "low", "detail": "Raised $15M from a16z, Paradigm"},
      {"name": "honeypot_risk", "risk": "low", "detail": "Standard upgradeable proxy, timelock 48h"}
    ]
  },
  "difficulty_score": 6.5,
  "overall_score": 78.3,
  "verdict": "worthwhile"
}
```

### Stage 4: Scoring Engine

Multi-factor weighted scoring:

```
overall_score = (value_score × 0.30)
              + (confidence_score × 0.20)
              + (timeline_urgency × 0.15)
              + (difficulty_inverse × 0.10)
              + (reputation_score × 0.15)
              + (community_score × 0.10)
```

Each sub-score is 0-100. The final score determines:
- **80+** → Critical: immediate notification, push to mining machine
- **60-79** → High: standard notification
- **40-59** → Medium: listed but not pushed
- **<40** → Low: archival only

### Stage 5: API Delivery

The scored opportunity enters PostgreSQL and Redis (hot cache). The API layer exposes it through:
- REST endpoints (polling for mining machines)
- WebSocket stream (real-time for dashboard)
- Server-Sent Events (lightweight for browser)

---

## 3. Database Schema (PostgreSQL)

```sql
-- Core tables
CREATE TABLE opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(255) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    protocol_name VARCHAR(255),
    category VARCHAR(100),
    description TEXT,
    status VARCHAR(50) DEFAULT 'active',  -- active, completed, expired, scam
    overall_score DECIMAL(5,2),
    difficulty_score DECIMAL(3,1),
    estimated_value_usd_min DECIMAL(12,2),
    estimated_value_usd_max DECIMAL(12,2),
    confidence VARCHAR(20),
    verdict VARCHAR(50),
    networks TEXT[],  -- array of chain names
    risk_level VARCHAR(20),
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    snapshot_date TIMESTAMPTZ,
    claim_start TIMESTAMPTZ,
    claim_end TIMESTAMPTZ,
    tge_date TIMESTAMPTZ,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    opportunity_id UUID REFERENCES opportunities(id),
    type VARCHAR(50) NOT NULL,  -- bridge, swap, lp, mint_nft, deploy, stake, vote, etc.
    description TEXT NOT NULL,
    parameters JSONB,  -- chain-specific params (contract addresses, amounts, etc.)
    is_optional BOOLEAN DEFAULT false,
    estimated_gas_usd DECIMAL(10,2),
    estimated_time_minutes INTEGER,
    difficulty VARCHAR(20),
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE protocol_info (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    opportunity_id UUID REFERENCES opportunities(id),
    website VARCHAR(500),
    twitter VARCHAR(200),
    discord VARCHAR(200),
    telegram VARCHAR(200),
    github VARCHAR(200),
    whitepaper_url VARCHAR(500),
    fundraising_total DECIMAL(12,2),
    fundraising_rounds JSONB,
    investors TEXT[],
    team_info JSONB,
    audit_reports JSONB,
    tvl DECIMAL(16,2),
    tvl_source VARCHAR(100)
);

CREATE TABLE wallet_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    address VARCHAR(42) NOT NULL,
    opportunity_id UUID REFERENCES opportunities(id),
    tasks_completed TEXT[],  -- array of task IDs
    tasks_in_progress TEXT[],
    gas_spent_usd DECIMAL(10,2),
    status VARCHAR(50) DEFAULT 'not_started',
    last_activity TIMESTAMPTZ,
    notes TEXT,
    UNIQUE(address, opportunity_id)
);

CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    opportunity_id UUID REFERENCES opportunities(id),
    wallet_address VARCHAR(42),
    type VARCHAR(50) NOT NULL,
    data JSONB,
    occurred_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_opportunities_score ON opportunities(overall_score DESC);
CREATE INDEX idx_opportunities_status ON opportunities(status);
CREATE INDEX idx_opportunities_detected ON opportunities(detected_at DESC);
CREATE INDEX idx_tasks_opportunity ON tasks(opportunity_id);
CREATE INDEX idx_wallet_states_address ON wallet_states(address);
CREATE INDEX idx_wallet_states_status ON wallet_states(status);
CREATE INDEX idx_events_time ON events(occurred_at DESC);
```

---

## 4. Caching Strategy (Redis)

| Key Pattern | TTL | Purpose |
|---|---|---|
| `opp:{id}` | 5 min | Single opportunity hot cache |
| `opp:top:50` | 2 min | Dashboard top opportunities |
| `wallet:{addr}:tasks` | 30 min | Wallet-specific task list |
| `dedup:bloom` | 24h | Bloom filter for opportunity dedup |
| `rate:{source}` | per-source | Rate limit counters |
| `scraper:health` | 30s | Scraper node heartbeats |
| `events:stream` | 1h | Recent event log for dashboard |

---

## 5. Scalability Design

### Horizontal Scaling

| Component | Scaling Strategy | Nodes |
|---|---|---|
| Scraper Workers | Shard by source type, then by topic/channel | 3-∞ per source |
| Intelligence Workers | Queue-based, stateless, auto-scale on queue depth | 2-20 |
| API Server | Stateless, behind Nginx/HAProxy | 2-10 |
| Dashboard | Static export + ISR on Vercel/Nginx | 1-∞ |
| PostgreSQL | Read replicas for dashboard queries, writer for ingestion | 1 writer + N readers |
| Redis | Cluster mode for sharded cache | 3-6 nodes |

### Rate Limit Management

Each scraper type has its own rate limit strategy:
- **Free APIs**: Token bucket per API key, automated key rotation from pool
- **Proxied**: Provider-rotated residential proxies with sticky sessions
- **Blockchain RPC**: Connection pool with load balancing across providers (Alchemy, Infura, QuickNode, public)
- **Browser rendering**: Browserless/Fingerprint rotation with Puppeteer stealth

---

## 6. Resilience & Fault Tolerance

| Failure Mode | Mitigation |
|---|---|
| Scraper dies | K8s liveness probe, auto-restart, RabbitMQ re-queues unacknowledged messages |
| LLM provider down | Fallback chain: Claude → GPT-4 → DeepSeek → local LLM |
| Database unreachable | Redis cache serves reads, writes queue in RabbitMQ for replay |
| Rate limited | Backoff with exponential jitter, key rotation, proxy rotation |
| Duplicate events | Bloom filter + semantic dedup before write |
| Corrupt data | Schema validation at every stage, dead-letter queue for malformed |

---

## 7. Actor Model (Internal Architecture)

Internally, Nabu uses an **actor-like model** where each component is a self-contained message-processing unit:

```
┌───────────────────────────────┐
│          Supervisor            │
│  (Health, config, lifecycle)   │
└────┬──────────┬──────────┬────┘
     │          │          │
     ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐
│ Twitter │ │ Telegram│ │ RPC    │  ... (Source Actors)
│ Actor   │ │ Actor   │ │ Actor  │
└────┬───┘ └────┬───┘ └────┬───┘
     │          │          │
     └──────────┼──────────┘
                │ (Event messages)
                ▼
         ┌────────────┐
         │   Mailbox   │  RabbitMQ Queue
         └────┬───────┘
              │
         ┌────┴───┐
         │  Analyzer  │
         │  Actors    │  (Intelligence Workers)
         └────┬───┘
              │
         ┌────┴────┐
         │ Database │
         │  Actors  │  (Write + Notify)
         └────┬────┘
              │
         ┌────┴────┐
         │  Stream  │
         │  Actors  │  (WebSocket + SSE)
         └─────────┘
```
