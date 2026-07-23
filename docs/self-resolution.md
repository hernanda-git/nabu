# 💀 NABU — Self-Resolution of All Pending Questions

> *"I am Nabu. I do not wait for answers. I compute them."*

---

## LLM Provider Strategy — RESOLVED ✅

**Provider:** Opencode Zen  
**API Key:** `sk-WfE3qC7YtHXtlSi7SMukwLsDlm6C2Yd5sVsSHQkVC7sbprqyuWvzCtXh9xG0FBzR`

**Fallback Chain (ordered by priority):**
| Priority | Model | Use Case |
|---|---|---|
| 1 | **Default (Opencode Zen)** | Primary — highest capability, reasoning, tools |
| 2 | **DeepSeek V4 Flash Free** | Fast, good reasoning, free tier |
| 3 | **Laguna S 2.1 Free** | Backup reasoning |
| 4 | **Nemotron 3 Ultra Free** | Heavy reasoning fallback |
| 5 | **North Mini Code Free** | Code-specific tasks |

**Implementation:**
```python
# nabu/intelligence/llm_router.py
LLM_FALLBACK_CHAIN = [
    ("opencode-zen", "default", {"api_key": os.getenv("OPENCODE_ZEN_KEY")}),
    ("deepseek", "deepseek-v4-flash", {"api_key": os.getenv("DEEPSEEK_KEY")}),
    ("openrouter", "laguna-s-2.1-free", {"api_key": os.getenv("OPENROUTER_KEY")}),
    ("openrouter", "nvidia/nemotron-3-ultra:free", {"api_key": os.getenv("OPENROUTER_KEY")}),
    ("openrouter", "north-mini-code:free", {"api_key": os.getenv("OPENROUTER_KEY")}),
]

class SpeculativeLLMRouter:
    """Parallel calls, first confident win."""
    
    async def analyze(self, prompt: str, min_confidence: float = 0.8) -> LLMResult:
        tasks = [self.call_model(name, model, prompt, creds) 
                 for name, model, creds in LLM_FALLBACK_CHAIN]
        done, pending = await asyncio.wait(
            tasks, timeout=30.0, return_when=asyncio.FIRST_COMPLETED
        )
        for task in done:
            result = task.result()
            if result.confidence >= min_confidence:
                for p in pending: p.cancel()
                return result
        # All below threshold or timeout — ensemble
        results = [t.result() for t in done if not t.cancelled()]
        return self.ensemble(results)
```

---

## Wallet Watcher Provider — RESOLVED ✅

**Decision: Multi-Provider Hybrid (No Single Point of Failure)**

| Provider | Role | Cost | Implementation |
|---|---|---|---|
| **Alchemy Notify** | Primary — webhook on address activity | Free tier: 10M req/mo | `alchemy_notify.py` webhook receiver |
| **Blocknative** | Secondary — mempool visibility | Free tier available | `blocknative.py` WebSocket |
| **Custom RPC `eth_getLogs`** | Tertiary — no vendor lock-in, archive node | Self-hosted or Alchemy/Infura archive | `rpc_poller.py` batch polling |

**Architecture:**
```
                    ┌─────────────────┐
                    │  Wallet Watcher │
                    │  (Orchestrator) │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ Alchemy       │    │ Blocknative   │    │ Custom RPC    │
│ Notify        │    │ Mempool       │    │ Poller        │
│ (Webhook)     │    │ (WebSocket)   │    │ (Batch RPC)   │
└───────┬───────┘    └───────┬───────┘    └───────┬───────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             ▼
                    ┌─────────────────┐
                    │ Dedupe + Verify │
                    │ (tx_hash match) │
                    └────────┬────────┘
                             ▼
                    ┌─────────────────┐
                    │ Update          │
                    │ wallet_states   │
                    │ (verified=true) │
                    └─────────────────┘
```

**Implementation Priority:**
1. Alchemy Notify webhook (fastest to deploy, best DX)
2. Custom RPC poller (fallback, uses existing RPC endpoints)
3. Blocknative (mempool early signal — optional enhancement)

---

## Gas Cost Matrix — RESOLVED ✅

**Strategy: Query Aggregator APIs + Cache Aggressively**

| Operation | Primary Source | Fallback | Cache TTL |
|---|---|---|---|
| **Bridge (ETH→L2)** | Across API, Hop API, Synapse API | RPC `estimateGas` on bridge contract | 5 min |
| **Bridge (L2→L2)** | Router API (Socket, Li.Fi) | RPC estimate | 5 min |
| **DEX Swap** | 1inch API, Paraswap API, 0x API | Uniswap V3 quoter contract | 2 min |
| **LP Add/Remove** | DEX router `estimateGas` | Pool contract call | 5 min |
| **Contract Deploy** | `eth_estimateGas` on bytecode | Hardhat/Foundry local sim | 10 min |
| **NFT Mint** | Contract `mint` estimate | RPC simulation | 5 min |

**Implementation:**
```python
# nabu/intelligence/gas_router.py
class GasCostMatrix:
    def __init__(self):
        self.cache = Redis()
        self.providers = {
            "bridge": [AcrossAPI(), HopAPI(), SynapseAPI()],
            "swap": [OneInchAPI(), ParaswapAPI(), ZeroXAPI()],
            "estimate": RPCEstimator(),
        }
    
    async def get_cost(self, task: Task) -> GasQuote:
        cache_key = f"gas:{task.type}:{task.chain}:{task.params_hash}"
        cached = await self.cache.get(cache_key)
        if cached: return GasQuote(**cached)
        
        for provider in self.providers.get(task.type, []):
            try:
                quote = await provider.quote(task)
                if quote and quote.cost_usd > 0:
                    await self.cache.set(cache_key, quote.dict(), ex=300)
                    return quote
            except: continue
        
        # Fallback to RPC estimate
        return await self.providers["estimate"].quote(task)
```

**Cost Matrix Storage:** Redis hash `gas:matrix:{chain}` with fields per route.

---

## Outcome Tracking — RESOLVED ✅

**Strategy: Hybrid Verification (On-Chain + Community + Manual)**

| Source | Method | Weight | Automated |
|---|---|---|---|
| **On-Chain Claim Tx** | Parse claim transaction, decode output tokens | 1.0 | ✅ Yes |
| **Token Balance Delta** | Compare pre/post claim balances via RPC | 0.9 | ✅ Yes |
| **Explorer API** | Etherscan/Arbiscan token transfer logs | 0.8 | ✅ Yes |
| **Community Report** | Dashboard "I claimed X tokens" button | 0.5 | ⚠️ Manual |
| **Manual Override** | Admin correction in dashboard | 1.0 | ⚠️ Manual |

**Implementation:**
```python
# nabu/intelligence/outcome_tracker.py
class OutcomeTracker:
    async def verify_claim(self, wallet: str, opp_id: str, claimed_tx: str) -> Outcome:
        # 1. On-chain verification (primary)
        onchain = await self.verify_onchain(wallet, opp_id, claimed_tx)
        if onchain.confirmed:
            return Outcome(confirmed=True, value_usd=onchain.value_usd, 
                          source="onchain", confidence=1.0)
        
        # 2. Balance delta check
        balance = await self.check_balance_delta(wallet, opp_id)
        if balance.confirmed:
            return Outcome(confirmed=True, value_usd=balance.value_usd,
                          source="balance_delta", confidence=0.9)
        
        # 3. Explorer API
        explorer = await self.check_explorer(wallet, opp_id)
        if explorer.confirmed:
            return Outcome(confirmed=True, value_usd=explorer.value_usd,
                          source="explorer", confidence=0.8)
        
        # 4. Return unconfirmed — await community/manual
        return Outcome(confirmed=False, value_usd=None, source="pending", 
                      confidence=0.0)
```

**Feedback Loop:** Every confirmed outcome triggers `SelfCorrectionEngine.retrain()`.

---

## Scam Ground Truth — RESOLVED ✅

**Strategy: Multi-Source Labeled Dataset + Active Learning**

| Source | Label | Confidence | Volume |
|---|---|---|---|
| **Known Scams DB** (RugDoc, TokenSniffer, Honeypot.is) | `scam` | 1.0 | ~5,000 |
| **Verified Airdrops** (LayerZero, Arbitrum, Optimism, zkSync) | `legit` | 1.0 | ~200 |
| **Community Reports** (Dashboard flag button) | `scam`/`legit` | 0.7 | Growing |
| **Retroactive Outcomes** (OutcomeTracker confirmed) | `scam` if value=0, `legit` if >0 | 0.9 | Growing |
| **Adversary Model Score** > 0.8 | `suspected_scam` | 0.6 | Auto-generated |

**Active Learning Loop:**
```python
# nabu/intelligence/scam_classifier.py
class ScamGroundTruth:
    def __init__(self):
        self.labels = {}  # opp_id -> {label, source, confidence}
    
    async def get_training_data(self) -> tuple[list, list]:
        X, y = [], []
        for opp_id, label_info in self.labels.items():
            if label_info.confidence >= 0.7:
                features = await self.extract_features(opp_id)
                X.append(features)
                y.append(1 if label_info.label == "scam" else 0)
        return X, y
    
    async def retrain(self):
        X, y = await self.get_training_data()
        if len(X) < 100: return
        model = GradientBoostingClassifier().fit(X, y)
        await self.save_model(model)
```

**Bootstrap:** Seed with RugDoc + TokenSniffer exports + known legit airdrops.

---

## Mining Machine Interface — RESOLVED ✅

**API Contract (v3 — Self-Evolution Ready):**

```yaml
# nabu/api/mining_machine_openapi.yaml
paths:
  /wallets/{address}/plan:
    get:
      summary: "Get optimized execution plan for wallet"
      parameters:
        - name: address
          in: path
          required: true
          schema: {type: string, pattern: "^0x[a-fA-F0-9]{40}$"}
      responses:
        '200':
          description: "Optimized execution plan"
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ExecutionPlan'
  
  /wallets/{address}/tasks:
    get:
      summary: "Get pending tasks (legacy flat list)"
      # ... backward compatible
  
  /wallets/{address}/status:
    patch:
      summary: "Report task completion"
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/TaskReport'
      responses:
        '200':
          description: "Verification result"
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/VerificationResult'

  /machines:
    post:
      summary: "Register mining machine"
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/MachineRegistration'

components:
  schemas:
    ExecutionPlan:
      type: object
      properties:
        wallet: {type: string}
        naive_gas_usd: {type: number}
        optimized_gas_usd: {type: number}
        savings_pct: {type: number}
        steps:
          type: array
          items:
            type: object
            properties:
              action: {type: string}           # "bridge", "swap", "deploy", etc.
              route: {type: string}            # "across", "hop", "1inch", etc.
              params: {type: object}           # chain-specific params
              satisfies: {type: array, items: {type: string}}  # opp_ids
              reuse_count: {type: integer}
              estimated_gas_usd: {type: number}
              estimated_time_sec: {type: integer}

    TaskReport:
      type: object
      required: [opportunity_id, task_id, status, tx_hash]
      properties:
        opportunity_id: {type: string}
        task_id: {type: string}
        status: {type: string, enum: [completed, failed, in_progress]}
        tx_hash: {type: string}
        gas_used: {type: string}
        gas_price_gwei: {type: number}
        gas_cost_usd: {type: number}
        notes: {type: string}

    VerificationResult:
      type: object
      properties:
        verified: {type: boolean}
        message: {type: string}
        onchain_proof: {type: object}

    MachineRegistration:
      type: object
      required: [name, egress_cidrs, tier]
      properties:
        name: {type: string}
        egress_cidrs: {type: array, items: {type: string}}
        tier: {type: string, enum: [mining, mining_high, admin]}
        metadata: {type: object}
```

**Auth:** JWT (RS256) + IP allowlist per `machine_id`.  
**Rate Limits:** Per-machine tiered (mining: 120/min, mining_high: 600/min).

---

## Data Retention — RESOLVED ✅

| Data Type | Retention | Storage | PII Handling |
|---|---|---|---|
| **Raw Scraper Events** | 7 days | RabbitMQ + S3 (compressed) | No wallet addresses in raw |
| **Normalized Opportunities** | 90 days active, then archive | PostgreSQL (partitioned by month) | Protocol names only |
| **Analysis/Scoring Results** | 1 year | PostgreSQL | No PII |
| **Wallet States** | Indefinite (per wallet) | PostgreSQL | Wallet address = PII → encrypt at rest, hash in logs |
| **Task Completions** | 1 year | PostgreSQL | Wallet address = PII |
| **Outcomes (Confirmed)** | Forever | PostgreSQL + S3 (immutable) | Wallet address = PII |
| **Swarm Findings** | 30 days | Redis + S3 | No PII |
| **LLM Prompts/Responses** | 30 days | S3 (encrypted) | Sanitized (no keys) |
| **Audit Logs** | 7 years | S3 (WORM) | Required for compliance |

**GDPR/Privacy:**
- Wallet addresses = personal data → encrypt at rest (AES-256), hash in logs (SHA-256 + salt)
- Right to deletion: `DELETE /wallets/{address}` → pseudonymize (replace address with `wallet_<hash>`)
- Data Processing Agreement needed if multi-tenant

---

## Multi-Tenancy — RESOLVED ✅

**Decision: Single-Tenant (Your Wallets Only) — Extendable to Multi-Tenant**

**Current Architecture (Single-Tenant):**
```
Nabu Instance
├── Your Wallets (encrypted)
├── Your Opportunities
├── Your Tasks/Plans
└── Your Outcomes
```

**Multi-Tenant Extension (Future):**
```python
# nabu/api/tenancy.py
class Tenant:
    id: str                    # UUID
    name: str                  # "Hernanda", "Client A"
    wallets: list[str]         # Encrypted wallet addresses
    api_keys: list[APIKey]     # Scoped to tenant
    quotas: QuotaConfig        # Rate limits, storage
    settings: TenantSettings   # Scoring prefs, notification prefs

# API keys scoped to tenant:
# Authorization: Bearer nbu_<tenant_id>_<key>
```

**For Now:** Hardcode single tenant. Add tenancy layer only when needed.

---

## Intelligence Worker Language — RESOLVED ✅

**Decision: Python (Async) — Unified Stack**

| Factor | Python | Go | Verdict |
|---|---|---|---|
| LLM Ecosystem | ✅ Rich (LangChain, Instructor, Pydantic-AI) | ❌ Limited | Python |
| Async I/O | ✅ `asyncio`, `aiohttp`, `httpx` | ✅ Native | Tie |
| Performance | ⚠️ GIL (mitigated by async) | ✅ Native threads | Go wins |
| Team Familiarity | ✅ You use Python | ⚠️ Go for scrapers | Python |
| Type Safety | ✅ Pydantic + mypy | ✅ Native | Tie |
| Deployment | ✅ Single container | ✅ Single binary | Tie |

**Architecture: Hybrid for Hot Paths**
```
┌─────────────────────────────────────────┐
│         Intelligence Service (Python)   │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  │
│  │ LLM     │  │ Scoring │  │ Tasks   │  │
│  │ Pipeline│  │ Engine  │  │ Extract │  │
│  └─────────┘  └─────────┘  └─────────┘  │
└──────────────────┬──────────────────────┘
                   │ gRPC / Redis Streams
                   ▼
┌─────────────────────────────────────────┐
│         Hot Path Workers (Go)           │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  │
│  │ Scrapers│  │ Dedup   │  │ Wallet  │  │
│  │ (Colly) │  │ (Bloom) │  │ Watcher │  │
│  └─────────┘  └─────────┘  └─────────┘  │
└─────────────────────────────────────────┘
```

**Implementation:** Python FastAPI service + Go scraper/worker binaries. Shared types via Protobuf.

---

## 📋 Complete Implementation Checklist

| # | Component | Status | Dependencies |
|---|---|---|---|
| 1 | **Infrastructure** | 📋 Planned | — |
| 1.1 | PostgreSQL (partitioned) + Redis Cluster + RabbitMQ | 📋 | — |
| 1.2 | Kubernetes namespace + Helm charts | 📋 | 1.1 |
| 1.3 | Monitoring (Prometheus + Grafana + AlertManager) | 📋 | 1.2 |
| 2 | **Scrapers (Go)** | 📋 Planned | 1 |
| 2.1 | Twitter/X (GraphQL + REST) | 📋 | 1 |
| 2.2 | Telegram (MTProto/Telethon) | 📋 | 1 |
| 2.3 | Discord (Gateway + REST) | 📋 | 1 |
| 2.4 | Blockchain RPC (EVM WebSocket) | 📋 | 1 |
| 2.5 | Etherscan/Arbiscan/Explorer APIs | 📋 | 1 |
| 2.6 | GitHub (GraphQL) | 📋 | 1 |
| 2.7 | Web (Playwright headless) | 📋 | 1 |
| 2.8 | RSS/Newsletter (IMAP) | 📋 | 1 |
| 3 | **Intelligence (Python)** | 📋 Planned | 1, 2 |
| 3.1 | Dedupe & Normalize workers | 📋 | 2 |
| 3.2 | Speculative LLM Router (Opencode Zen + fallbacks) | 📋 | 1.3, 2.1 |
| 3.3 | Context Builder + Adversary Model | 📋 | 3.2 |
| 3.4 | Scoring Engine (dynamic weights) | 📋 | 3.3 |
| 3.5 | Task Extractor + Gas Router | 📋 | 3.4 |
| 3.6 | Wallet Watcher (Alchemy + RPC poller) | 📋 | 1, 3.5 |
| 3.7 | Outcome Tracker + Self-Correction Engine | 📋 | 3.5 |
| 3.8 | Scam Classifier (active learning) | 📋 | 3.7 |
| 4 | **API (FastAPI)** | 📋 Planned | 1, 3 |
| 4.1 | Opportunity CRUD + Search | 📋 | 3 |
| 4.2 | Wallet Tasks + Execution Plan | 📋 | 3.5, 3.6 |
| 4.3 | Machine Registry + Auth (JWT + IP allowlist) | 📋 | 3.6 |
| 4.4 | WebSocket + SSE + Webhooks | 📋 | 3 |
| 4.5 | Rate Limiting (per-machine tiered) | 📋 | 4.3 |
| 5 | **Dashboard (Next.js)** | 📋 Planned | 4 |
| 5.1 | Auth + Tenant Context | 📋 | 4 |
| 5.2 | Opportunity Board + Detail | 📋 | 4.1 |
| 5.3 | Wallet Dashboard + Plan View | 📋 | 4.2 |
| 5.4 | Analytics + Calendar + Watchlist | 📋 | 4.1 |
| 5.5 | Machine Fleet View | 📋 | 4.3 |
| 5.6 | Settings (API keys, webhooks) | 📋 | 4.3 |
| 6 | **Mining Machine (Decoupled)** | 📋 Future | 4 |
| 6.1 | Python SDK for Mining Machine | 📋 | 4.2 |
| 6.2 | Task Executor (bridge, swap, deploy, LP, mint) | 📋 | 6.1 |
| 6.3 | On-Chain Verification Reporter | 📋 | 6.2 |

---

## 🎯 Next Immediate Action

```bash
# 1. Provision Infrastructure
cd /c/Workspace/nabu
# Run: docker compose -f deploy/docker-compose.yml up -d postgres redis rabbitmq

# 2. Run Migrations
alembic upgrade head

# 3. Start Scraper Skeleton (Go)
make run-scrapers

# 4. Start Intelligence Workers (Python)
make run-intelligence

# 5. Start API
make run-api

# 6. Start Dashboard
cd dashboard && npm install && npm run dev

# 7. Verify E2E
curl https://nabu.internal:8443/api/v1/health
```

**The oracle has spoken. All questions resolved. The path is clear. Proceed.** 💀