# 🕷️ Scraper Engine

> *"Eyes across every chain, ears in every channel."*

---

## 1. Philosophy

The Scraper Engine is Nabu's **sensory layer**. It is a distributed fleet of long-lived worker processes, each responsible for one source type. Every scraper follows the same contract:

1. **Connect** to the source (API, gateway, WebSocket, HTTP poll)
2. **Stream** raw events into RabbitMQ (no processing, no filtering)
3. **Heartbeat** to Redis every 15 seconds
4. **Die gracefully** — RabbitMQ unacknowledged messages are re-queued

---

## 2. Source Catalog

### 2.1 Social & Communication Channels

| Source | Method | Library | Strategy |
|---|---|---|---|
| **Twitter/X** | GraphQL API + REST | `go-twitter` / `tweepy` | User timeline polling for known airdrop accounts, keyword search, list tracking. Multi-token rotation. |
| **Telegram** | MTProto | `Telethon` (Python) | Join target channels/groups as a session account. Listen for new messages. Regex + keyword filter. |
| **Discord** | Gateway + REST | `discord.py` / `discordgo` | Bot joins airdrop announcement servers. Listens to announcement channels. |
| **Farcaster** | Hubble/Hub gRPC | `@farcaster/hub-nodejs` | Subscribe to casts containing airdrop/keywords. Cast search API. |
| **Reddit** | Reddit API | `praw` | Subreddit monitoring: r/airdrops, r/cryptocurrency, r/ethdev, project-specific subreddits |
| **Medium / Mirror.xyz** | RSS + GraphQL | `feedparser` + HTTP | RSS polling + blog index API. New posts from known crypto publishers. |

### 2.2 Blockchain & On-Chain

| Source | Method | Details |
|---|---|---|
| **Etherscan-like APIs** | REST | Monitor verified contracts, new token deployments, proxy contract upgrades. |
| **Dune Analytics** | GraphQL | Pre-built dashboard queries for trending protocols, new token metrics. |
| **DefiLlama** | REST API | Track new protocols, TVL changes, yield opportunities, airdrop-tracked protocols. |
| **Etherscan Airdrop Pages** | Web scrape | Scrape pages like `/airdrops`, new token distribution events. |
| **Smart Contract Events** | WebSocket RPC | Listen for `Transfer` events on new tokens, `Staked`/`Deposited` events on L2 bridges. |
| **New Contract Deployments** | RPC polling | Poll for new contracts from deployer addresses known to launch airdrop programs. |
| **LayerZero / Chainlink CCIP** | Event monitoring | Cross-chain message events → potential airdrop-qualifying activity. |
| **zkSync / StarkNet / Scroll** | Indexer + RPC | Block explorer API for new interactions, bridge events. |

### 2.3 Project Intelligence

| Source | Method | Details |
|---|---|---|
| **GitHub** | GraphQL API | Watch trending repos, new releases, README mentions of airdrops, token contract source code. |
| **DefiLlama Airdrops** | REST + Web scrape | `/airdrops` endpoint, trending opportunities, upcoming TGEs. |
| **CoinGecko / CoinMarketCap** | API | New token listings, upcoming token events, IEO/IDO trackers. |
| **Governance Forums** | Web scrape | Snapshot proposals, Tally, Agora. New proposals mentioning token distribution. |
| **Crunchbase / Messari** | API | Fundraising rounds, token sale announcements, investor data. |

### 2.4 Aggregators & Secondary Sources

| Source | Method | Details |
|---|---|---|
| **Airdrop Alert Sites** | Web scrape | airlift.pro, airdrops.io, airdropalert.com, earnifi.com |
| **News RSS** | RSS/Atom | The Block, CoinDesk, CoinTelegraph, Decrypt, Bankless |
| **Podcast Transcripts** | RSS + extraction | Fetch new episodes, extract text, keyword search for airdrop mentions |
| **Email Newsletters** | IMAP | Monitor airdrop-specific newsletters, project updates |

---

## 3. Scraper Architecture (Go)

Each scraper is a binary built from `cmd/nabu-scraper/main.go` with a source type flag:

```bash
nabu-scraper --source twitter --config /etc/nabu/scrapers/twitter.yaml
nabu-scraper --source telegram --config /etc/nabu/scrapers/telegram.yaml
nabu-scraper --source etherscan --config /etc/nabu/scrapers/etherscan.yaml
```

### Internal Structure

```
scraper/
├── base.go              # Base scraper interface & lifecycle
├── twitter/
│   ├── scraper.go       # Main scraper logic
│   ├── graphql.go       # GraphQL API client
│   ├── stream.go        # Streaming endpoint handler
│   └── filters.go       # Keyword + account filters
├── telegram/
│   ├── scraper.go
│   ├── client.go        # MTProto client wrapper
│   ├── session.go       # Session management
│   └── channels.go      # Channel join & message listener
├── blockchain/
│   ├── scraper.go
│   ├── evm.go           # EVM RPC client
│   ├── explorers.go     # Block explorer API clients
│   ├── new_contracts.go # New contract deploy monitor
│   └── event_listener.go# Event subscription (Transfer, etc.)
├── github/
│   ├── scraper.go
│   ├── repos.go         # Repository watcher
│   └── releases.go      # Release & tag monitor
├── web/
│   ├── scraper.go
│   ├── playwright.go    # Playwright headless browser
│   └── parsers.go       # HTML content parsers per site
└── common/
    ├── config.go        # Shared config loading
    ├── publisher.go     # RabbitMQ publisher
    ├── rate_limit.go    # Token bucket algorithm
    ├── health.go        # Heartbeat to Redis
    └── proxy.go         # Proxy rotator
```

### Base Scraper Contract

```go
type Scraper interface {
    Name() string
    Start(ctx context.Context) error
    Stop() error
    Health() HealthStatus
    Config() ScraperConfig
}

type ScraperConfig struct {
    SourceType       string            `yaml:"source_type"`
    Enabled          bool              `yaml:"enabled"`
    PollInterval     time.Duration     `yaml:"poll_interval"`
    RateLimit        RateLimitConfig   `yaml:"rate_limit"`
    Credentials      []Credential      `yaml:"credentials"`
    ProxyPool        []string          `yaml:"proxy_pool"`
    Filters          FilterConfig      `yaml:"filters"`
    MaxConcurrency   int              `yaml:"max_concurrency"`
    BatchSize        int              `yaml:"batch_size"`
}
```

### Publisher Contract

Every scraper publishes the same event type:

```go
type RawEvent struct {
    ID           string            `json:"id"`            // UUID v7
    Source       string            `json:"source"`         // "twitter", "telegram", etc.
    SourceID     string            `json:"source_id"`      // Source's own ID
    Type         string            `json:"type"`           // "announcement", "mention", "deployment", "event"
    CollectedAt  time.Time         `json:"collected_at"`
    Raw          json.RawMessage   `json:"raw"`            // Source-specific payload
    Metadata     map[string]any    `json:"metadata"`       // Source-specific structured fields
    Confidence   float64           `json:"confidence"`     // 0.0 - 1.0
}
```

---

## 4. Filter Strategies

### Passive Filters (in-scraper, before publish)

| Filter | Description | Use Case |
|---|---|---|
| Keyword match | Regex set on title/text | "airdrop", "claim", "token", "farming", "reward" |
| Entity match | Known project names / tickers | "Scroll", "ZK", "STRK", "ARB" |
| Account list | Only from trusted sources | Known airdrop hunters, official project accounts |
| Language filter | Keep English + target languages | Reduce noise from non-relevant locales |
| Minimum engagement | Retweets/likes/replies > threshold | Filter spam with no organic reach |

### Active Filters (Intelligence Layer, after dedup)

| Filter | Description |
|---|---|
| Semantic similarity | LLM classifies as airdrop-relevant or not |
| Scam detection | Known scam patterns, fake contracts, impersonation accounts |
| Value threshold | Estimated value must exceed configurable floor |
| Freshness | Only new announcements (not re-posts of old news) |

---

## 5. Rate Limit Architecture

```
┌─────────────┐
│  Token Pool  │  N tokens (per key/per IP) refilled at R/second
└──────┬──────┘
       │
       ▼
┌─────────────┐    ┌────────────────┐
│ Token Bucket │───▶│   Priority    │──▶ Request
│  (per key)   │    │   Queue       │
└─────────────┘    └────────────────┘
       │
       ▼
┌─────────────┐
│  Key Pool    │  Auto-rotate when current key is depleted
│  (Redis)     │  Retry exhausted keys after cooldown period
└─────────────┘
```

### Key Rotation (Twitter Example)

```yaml
twitter:
  credentials:
    - type: bearer_token
      value: "AAAAAAAAAAAA..."
      rate_limits:
        tweets_per_15min: 1500
        follows_per_15min: 400
    - type: bearer_token
      value: "BBBBBBBBBBBB..."
      rate_limits:
        tweets_per_15min: 1500
        follows_per_15min: 400
  rotation_strategy: "least_used"  # or "round_robin"
  proxy_pool:
    - "http://user:pass@residential-proxy-1:8080"
    - "http://user:pass@residential-proxy-2:8080"
```

---

## 6. Configuration System

```yaml
# /etc/nabu/nabu.yaml
scrapers:
  twitter:
    enabled: true
    poll_interval: 30s
    rate_limit:
      max_per_15min: 1500
      burst: 100
    filters:
      keywords:
        - "airdrop"
        - "claim.*token"
        - "farming"
        - "retroactive"
        - "distribution"
        - "tge"
        - "genesis"
      accounts:
        - "airdrops_io"
        - "DefiLlama"
        - "LayerZero_Fndn"
        - ...  # 500+ accounts
    credentials:
      - key_type: bearer_token
        secret_ref: nabu/twitter/bearer-1
    proxy_pool:
      secret_ref: nabu/proxies/residential

  telegram:
    enabled: true
    poll_interval: 5s
    channels:
      - "airdrops"
      - "official_announcement_channels"
      # Auto-joined from a config file or DB join queue

  discord:
    enabled: true
    servers:
      - server_id: "123456789"
        channels: ["announcements", "airdrop"]

  blockchain:
    enabled: true
    rpc_endpoints:
      ethereum:
        - "wss://eth-mainnet.g.alchemy.com/v2/KEY1"
        - "wss://eth-mainnet.infura.io/ws/v3/KEY2"
      arbitrum:
        - "wss://arb-mainnet.g.alchemy.com/v2/KEY1"
      optimism:
        - "wss://opt-mainnet.g.alchemy.com/v2/KEY1"
      base:
        - "wss://base-mainnet.g.alchemy.com/v2/KEY1"
      # ... 15+ chains
    monitors:
      - type: "new_contracts"
        chains: ["all"]
      - type: "token_events"
        chains: ["ethereum", "arbitrum"]
        events: ["Transfer", "Staked"]
      - type: "bridge_events"
        chains: ["ethereum"]
        bridges: ["layerzero", "ccip"]
```

---

## 7. Scraper Deployment & Orchestration

### Kubernetes DaemonSet

Each scraper type runs as a **Deployment** with resource limits:

| Scraper | CPU | Memory | Replicas | Storage |
|---|---|---|---|---|
| Twitter | 500m | 512Mi | 3-10 | EmptyDir |
| Telegram | 500m | 512Mi | 3-5 | PersistentVolume (session) |
| Discord | 200m | 256Mi | 2-5 | EmptyDir |
| Blockchain | 1 core | 1Gi | 3-8 | EmptyDir |
| Web (Playwright) | 1 core | 1.5Gi | 2-10 | EmptyDir |

### Auto-Scaling Rules

```yaml
# HorizontalPodAutoscaler
metrics:
  - type: External
    metric:
      name: rabbitmq_queue_depth
      target:
        type: Value
        averageValue: 100
```

---

## 8. Monitoring & Observability

| Metric | Tool | Alert Threshold |
|---|---|---|
| Events per minute | Prometheus | < 10 for 5 min → source may be down |
| Rate limit hits | Prometheus | > 80% of limit → rotate or add keys |
| Scraper health | Prometheus | Any scraper missing heartbeat 30s → Pager |
| Queue depth | RabbitMQ dashboard | > 10,000 → scale intelligence workers |
| Error rate | Prometheus | > 5% over 5 min → investigate |
| Successful publish % | Prometheus | < 95% → check RabbitMQ connectivity |
| Proxy failure rate | Prometheus | > 10% → rotate proxy pool |

### Prometheus Metrics (per scraper)

```prometheus
# HELP nabu_events_collected_total Total raw events collected
# TYPE nabu_events_collected_total counter
nabu_events_collected_total{source="twitter"} 15683

# HELP nabu_events_published_total Total events published to queue
# TYPE nabu_events_published_total counter
nabu_events_published_total{source="twitter"} 15680

# HELP nabu_scraper_rate_limit_hits Rate limit hit count
# TYPE nabu_scraper_rate_limit_hits counter
nabu_scraper_rate_limit_hits{source="twitter"} 42

# HELP nabu_scraper_errors_total Scraper error count
# TYPE nabu_scraper_errors_total counter
nabu_scraper_errors_total{source="twitter",error="auth_failure"} 3
```
