# 🔌 API Specification — Mining Machine Interface

> *"The oracle speaks. The machine acts."*

---

## 1. Overview

Nabu exposes a **versioned REST API** + **WebSocket** + **Server-Sent Events** for the decoupled mining machine and dashboard. This is the sole interface through which the external world interacts with the intelligence.

**Base URL**: `https://nabu.internal:8443/api/v1`  
**Auth**: Bearer token (JWT, rotated monthly)  
**Content-Type**: `application/json`  

---

## 2. Authentication

### Request Header
```
Authorization: Bearer nbu_m1_eyJhbGciOiJIUzI1NiIs...
```

### API Key Levels

| Level | Access | Usage |
|---|---|---|
| `mining` | Full read + write (opportunities, tasks, wallet state) | Mining machines |
| `dashboard` | Read all + wallet status write | Web dashboard |
| `webhook` | Read events + subscribe to stream | External integrations |
| `admin` | Full CRUD, config, scraper management | Internal ops |

---

## 3. Endpoints

### 3.1 Opportunities

#### `GET /opportunities`

List all active airdrop opportunities with optional filtering.

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `status` | string | `active` | Filter: `active`, `completed`, `expired`, `scam`, `all` |
| `min_score` | number | `0` | Minimum overall score (0-100) |
| `max_difficulty` | number | `10` | Maximum difficulty (1-10) |
| `network` | string | — | Filter by chain (e.g. `ethereum`, `arbitrum`) |
| `category` | string | — | Filter by category (e.g. `l2`, `defi`, `dex`) |
| `verdict` | string | — | Filter: `worthwhile`, `speculative`, `risky`, `skip` |
| `search` | string | — | Full-text search in title & description |
| `sort_by` | string | `overall_score` | Sort: `overall_score`, `detected_at`, `estimated_value`, `claim_start` |
| `sort_order` | string | `desc` | `asc` or `desc` |
| `limit` | int | `50` | Items per page (max 200) |
| `offset` | int | `0` | Pagination offset |

**Response:**
```json
{
  "data": [
    {
      "id": "opp_a1b2c3d4",
      "slug": "hyperscale-airdrop",
      "title": "HyperScale L3 Airdrop Season 1",
      "protocol_name": "HyperScale",
      "category": "l3_rollup",
      "status": "active",
      "overall_score": 78.3,
      "difficulty_score": 6.5,
      "estimated_value_usd_min": 500,
      "estimated_value_usd_max": 5000,
      "confidence": "medium",
      "verdict": "worthwhile",
      "networks": ["ethereum", "arbitrum"],
      "risk_level": "medium",
      "detected_at": "2026-07-23T09:42:00Z",
      "claim_start": "2026-08-15T00:00:00Z",
      "claim_end": "2026-09-15T00:00:00Z",
      "tge_date": "2026-08-15T00:00:00Z",
      "task_count": 12,
      "total_gas_estimate_usd": 45,
      "sources": [
        {"type": "twitter", "url": "https://twitter.com/HyperScale/status/123456789"}
      ]
    }
  ],
  "pagination": {
    "total": 247,
    "limit": 50,
    "offset": 0,
    "next_offset": 50
  }
}
```

---

#### `GET /opportunities/:id`

Full detail of a single opportunity including all tasks.

**Response:**
```json
{
  "data": {
    "id": "opp_a1b2c3d4",
    "title": "HyperScale L3 Airdrop Season 1",
    "protocol_name": "HyperScale",
    "description": "HyperScale is a new Ethereum L3 rollup...",
    "category": "l3_rollup",
    "status": "active",
    "overall_score": 78.3,
    "difficulty_score": 6.5,
    "estimated_value_usd_min": 500,
    "estimated_value_usd_max": 5000,
    "confidence": "medium",
    "verdict": "worthwhile",
    "networks": ["ethereum", "arbitrum"],
    "risk_level": "medium",
    "risk_factors": [
      {"name": "team_anonymous", "risk": "high", "detail": "Team is pseudonymous"},
      {"name": "code_audited", "risk": "low", "detail": "Audited by Trail of Bits"},
      {"name": "vc_backing", "risk": "low", "detail": "Raised $15M from a16z, Paradigm"}
    ],
    "sources": [
      {"type": "twitter", "url": "...", "collected_at": "2026-07-23T09:42:00Z"},
      {"type": "telegram", "channel": "@hyperscale", "url": "...", "collected_at": "2026-07-23T09:42:05Z"}
    ],
    "timeline": {
      "snapshot_date": null,
      "claim_start": "2026-08-15T00:00:00Z",
      "claim_end": "2026-09-15T00:00:00Z",
      "tge_date": "2026-08-15T00:00:00Z"
    },
    "protocol_info": {
      "website": "https://hyperscale.io",
      "twitter": "@HyperScale",
      "discord": "discord.gg/hyperscale",
      "github": "github.com/hyperscale",
      "fundraising_total": 15000000,
      "investors": ["a16z", "Paradigm", "Coinbase Ventures"],
      "audit_reports": [
        {"firm": "Trail of Bits", "date": "2026-06-01", "url": "..."}
      ],
      "tvl": 42000000
    },
    "tasks": [
      {
        "id": "task_1",
        "type": "bridge",
        "description": "Bridge at least 0.5 ETH from Ethereum to HyperScale",
        "parameters": {
          "source_chain": "ethereum",
          "target_chain": "hyperscale",
          "min_amount_eth": 0.5,
          "bridge_contract": "0x1234...5678",
          "lz_endpoint_id": 30167
        },
        "is_optional": false,
        "estimated_gas_usd": 15,
        "estimated_time_minutes": 5,
        "difficulty": "easy",
        "sort_order": 1
      },
      {
        "id": "task_2",
        "type": "swap",
        "description": "Swap at least 2 ETH for HSC on HyperScale DEX",
        "parameters": {
          "chain": "hyperscale",
          "dex": "hyperscale-swap",
          "token_in": "ETH",
          "token_out": "HSC",
          "min_amount": 2.0,
          "router_address": "0x8765...4321"
        },
        "is_optional": false,
        "estimated_gas_usd": 5,
        "estimated_time_minutes": 2,
        "difficulty": "easy",
        "sort_order": 2
      }
    ],
    "created_at": "2026-07-23T09:43:15Z",
    "updated_at": "2026-07-23T09:43:15Z"
  }
}
```

---

### 3.2 Wallet Management

#### `GET /wallets/:address/tasks`

Get personalized task list for a specific wallet on all active opportunities.

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `status` | string | `pending` | `all`, `pending`, `in_progress`, `completed` |
| `min_score` | int | `50` | Minimum opportunity score |

**Response:**
```json
{
  "data": {
    "address": "0x1234...abcd",
    "total_gas_spent_usd": 145.32,
    "opportunities_engaged": 12,
    "opportunities": [
      {
        "opportunity_id": "opp_a1b2c3d4",
        "title": "HyperScale L3 Airdrop",
        "score": 78.3,
        "status": "in_progress",
        "tasks_total": 12,
        "tasks_completed": 5,
        "tasks_in_progress": 2,
        "tasks_pending": 5,
        "gas_spent_usd": 32.50,
        "last_activity": "2026-07-23T10:15:00Z",
        "tasks": [
          {"id": "task_1", "type": "bridge", "description": "...", "status": "completed", "tx_hash": "0xabc...", "completed_at": "2026-07-23T10:15:00Z"},
          {"id": "task_2", "type": "swap", "description": "...", "status": "in_progress", "tx_hash": null},
          {"id": "task_3", "type": "lp", "description": "...", "status": "pending", "tx_hash": null}
        ]
      }
    ]
  }
}
```

---

#### `PATCH /wallets/:address/status`

Report task completion from the mining machine.

**Request:**
```json
{
  "opportunity_id": "opp_a1b2c3d4",
  "task_id": "task_1",
  "status": "completed",
  "tx_hash": "0x7a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b",
  "gas_used": 0.005,
  "gas_price_gwei": 25,
  "gas_cost_usd": 3.75,
  "notes": "Bridged via HyperScale Bridge, confirmed in 3 blocks"
}
```

**Response:**
```json
{
  "success": true,
  "verified": true,
  "message": "Task completion verified on-chain"
}
```

**Response (verification failed):**
```json
{
  "success": false,
  "verified": false,
  "message": "Transaction hash not found on chain hyperscale",
  "detail": "Expected block range: 15000000-15001000, tx not found"
}
```

---

### 3.3 Events & Streaming

#### `GET /events`

List recent events (opportunity discovered, updated, expired).

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `since` | ISO8601 | 1h ago | Events after this time |
| `limit` | int | `50` | Max events |
| `type` | string | — | Filter by event type |

**Response:**
```json
{
  "data": [
    {
      "id": "evt_001",
      "type": "opportunity.new",
      "opportunity_id": "opp_a1b2c3d4",
      "title": "HyperScale L3 Airdrop",
      "score": 78.3,
      "timestamp": "2026-07-23T09:43:15Z"
    },
    {
      "id": "evt_002",
      "type": "opportunity.score_changed",
      "opportunity_id": "opp_a1b2c3d4",
      "old_score": 65.0,
      "new_score": 78.3,
      "reason": "New audit report discovered",
      "timestamp": "2026-07-23T10:00:00Z"
    }
  ]
}
```

---

#### `GET /events/stream`

Server-Sent Events (SSE) stream.

```http
GET /api/v1/events/stream HTTP/1.1
Accept: text/event-stream
Authorization: Bearer nbu_m1_...
```

```text
event: opportunity.new
data: {"id":"opp_a1b2c3d4","title":"HyperScale L3 Airdrop","score":78.3}

event: opportunity.score_changed
data: {"id":"opp_a1b2c3d4","old_score":65.0,"new_score":78.3}

event: wallet.task_completed
data: {"address":"0x1234...","opportunity_id":"opp_a1b2c3d4","task_id":"task_1","tx_hash":"0x..."}
```

---

#### `ws://nabu.internal:8443/api/v1/ws`

Full-duplex WebSocket for real-time bidirectional communication.

**Client → Server messages:**
```json
// Subscribe to specific opportunities
{"type": "subscribe", "channels": ["opportunities:new", "opportunity:opp_a1b2c3d4:updates"]}

// Report task status
{"type": "task_update", "opportunity_id": "opp_a1b2c3d4", "task_id": "task_2", "status": "in_progress"}

// Request wallet refresh
{"type": "wallet_refresh", "address": "0x1234...abcd"}
```

**Server → Client messages:**
```json
{"type": "opportunity.new", "data": {...}}
{"type": "opportunity.updated", "data": {...}}
{"type": "wallet.sync", "data": {...}}
{"type": "heartbeat", "timestamp": "2026-07-23T10:00:00Z"}
```

---

### 3.4 Statistics & Analytics

#### `GET /stats/overview`

```json
{
  "data": {
    "total_opportunities": 847,
    "active_opportunities": 247,
    "high_priority": 42,
    "total_tasks": 5231,
    "estimated_pool_value_usd_min": 1250000,
    "estimated_pool_value_usd_max": 15000000,
    "average_score": 54.3,
    "by_category": {
      "l2": 45,
      "defi": 82,
      "dex": 38,
      "bridge": 15,
      "nft": 12,
      "infra": 30,
      "gaming": 15,
      "other": 10
    },
    "by_network": {
      "ethereum": 120,
      "arbitrum": 45,
      "solana": 38,
      "base": 30,
      "optimism": 22,
      "zkSync": 18,
      "scroll": 15,
      "others": 44
    },
    "new_today": 12,
    "expiring_this_week": 8
  }
}
```

---

## 4. Mining Machine Client SDK

```python
# pyproject.toml dependency
# nabu-sdk = { git = "https://github.com/your-org/nabu-sdk-python.git" }

from nabu import NabuClient

client = NabuClient(
    api_key="nbu_m1_...",
    base_url="https://nabu.internal:8443/api/v1"
)

# Get high-priority opportunities
opps = client.get_opportunities(min_score=70, limit=10)

# Get tasks for a wallet
tasks = client.get_wallet_tasks("0x1234...abcd", opportunistic="opp_a1b2c3d4")

# Report completion
client.report_task(
    wallet="0x1234...abcd",
    opportunity_id="opp_a1b2c3d4",
    task_id="task_1",
    status="completed",
    tx_hash="0x..."
)

# Stream live events
for event in client.stream_events():
    if event.type == "opportunity.new" and event.data.score > 80:
        print(f"🔥 {event.data.title} — Score: {event.data.score}")
```

---

## 5. Rate Limits

| Tier | Requests/min | Burst |
|---|---|---|
| `mining` | 600 | 100 |
| `dashboard` | 300 | 50 |
| `webhook` | 120 | 30 |
| `admin` | 60 | 20 |

**Response headers:**
```
X-RateLimit-Limit: 600
X-RateLimit-Remaining: 597
X-RateLimit-Reset: 1627050000
```

---

## 6. Webhooks

For push-based delivery to the mining machine or external systems.

```json
{
  "url": "https://mining-machine.internal:8443/webhooks/nabu",
  "events": ["opportunity.new", "opportunity.score_changed", "opportunity.expiring"],
  "secret": "whsec_abc123",
  "retry_policy": {
    "max_retries": 5,
    "backoff": "exponential",
    "initial_delay_ms": 1000
  }
}
```

**Webhook payload**:
```http
POST /webhooks/nabu HTTP/1.1
Content-Type: application/json
X-Nabu-Event: opportunity.new
X-Nabu-Signature: sha256=abc123def456...

{
  "opportunity_id": "opp_a1b2c3d4",
  "title": "HyperScale L3 Airdrop",
  "score": 78.3,
  "verdict": "worthwhile",
  "url": "https://nabu.internal:8443/api/v1/opportunities/opp_a1b2c3d4"
}
```
