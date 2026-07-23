# 🚀 Nabu v2 — System Improvements & Hardening

> *"The oracle evolves. The tablet rewrites itself."*

**Status:** Proposed enhancements to the v1 design.
**Based on:** End-to-end architecture review (2026-07-23).

---

## 1. Summary of Gaps

| # | Gap | Severity |
|---|---|---|
| 1 | Wallet state is passive only — no on-chain auto-detection of task completion | High |
| 2 | Scoring weights are static — no market-condition awareness | High |
| 3 | No cross-opportunity gas/task optimization | Medium |
| 4 | Reactive only — no predictive/anomaly-based discovery | Medium |
| 5 | API lacks per-machine limits + abuse detection | Medium |
| 6 | Dashboard has no mining-machine fleet view | Low |
| 7 | No A/B testing or outcome feedback loop for scoring | Low |

---

## 2. On-Chain Wallet Monitoring (Gap #1)

**Problem:** Today the mining machine *reports* task completion. Nabu trusts it. If a machine lies, or crashes mid-task, Nabu has no ground truth.

**Solution:** Add a dedicated **Wallet Watcher** that independently observes on-chain activity and reconciles against reported state.

### Architecture

```
Mining Machine ──PATCH /wallets/:addr/status──► Nabu (records "reported")
        │
        ▼
┌──────────────────┐     ┌──────────────────┐
│  Chain Indexers  │────▶│  Wallet Watcher   │────▶ Reconcile vs reported
│ (Alchemy Notify,  │     │  (Python workers) │      │
│  Blocknative,     │     │                  │      ▼
│  custom RPC logs) │     │  - detect bridge │  wallet_states
└──────────────────┘     │  - detect swap    │  (verified=true)
                             │  - detect LP     │
                             │  - detect deploy │
                             └──────────────────┘
```

### Provider Options

| Provider | Method | Notes |
|---|---|---|
| **Alchemy Notify** | Webhook on address activity | Best DX, needs Alchemy RPC |
| **Blocknative** | Mempool → confirmed events | Early signal (pre-confirmation) |
| **Custom RPC `logs` subscription** | `eth_getLogs` filtered by address + topic | No vendor lock-in, needs full node or archive |
| **The Graph subgraphs** | Indexed protocol events per chain | Good for DEX/LP/bridge events |

### Reconciliation Logic

```python
class WalletReconciliation:
    async def on_chain_event(self, wallet, chain, event_type, tx_hash, block):
        # Find matching opportunity + task
        task = await db.match_task(wallet, chain, event_type, tx_hash)
        if not task:
            # Unknown task — still record raw activity for later attribution
            await db.record_unattributed_activity(wallet, chain, event_type, tx_hash)
            return
        reported = await db.get_reported_status(wallet, task.id)
        if reported and reported.tx_hash != tx_hash:
            # Conflict! Machine reported a different tx. Flag for review.
            await self.flag_conflict(wallet, task.id, reported.tx_hash, tx_hash)
            return
        # Auto-verify
        await db.mark_task_verified(wallet, task.id, tx_hash, block)

    async def flag_conflict(self, wallet, task_id, reported_tx, observed_tx):
        await db.insert_event(Event(
            type="wallet.task_conflict",
            wallet_address=wallet,
            data={"task_id": task_id, "reported_tx": reported_tx, "observed_tx": observed_tx},
        ))
        # Optionally alert ops
        await alerting.send("⚠️ Task conflict", f"Wallet {wallet} task {task_id}: reported {reported_tx} but chain shows {observed_tx}")
```

### Events Added

```
wallet.activity_detected   — on-chain event seen, not yet matched
wallet.task_verified     — on-chain confirmation matches a task
wallet.task_conflict     — reported tx differs from observed
wallet.unattributed      — on-chain activity with no matching task
```

---

## 3. Dynamic Scoring Weights (Gap #2)

**Problem:** Fixed weights ignore market regime. In a bull market, more airdrops drop and competition is fierce — value matters most. In a bear market, scams spike — reputation/risk should dominate.

**Solution:** A **Market Regime Detector** adjusts weights periodically from on-chain macro signals.

### Signals

| Signal | Source | Effect when rising |
|---|---|---|
| Total crypto market cap (30d Δ) | CoinGecko | Bull → ↑ value weight |
| Average airdrop scam rate (trailing 30d) | Nabu's own scam detector | ↑ → ↑ reputation/risk weight |
| Median gas price (7d) | EVM RPC | ↑ → ↓ difficulty-inverse weight (gas too expensive to bother) |
| New protocol funding total (30d) | Crunchbase/Messari | ↑ → ↑ community weight |
| Number of active opportunities | Nabu DB | ↑ → ↑ confidence weight (signal dilution) |

### Weight Matrix

| Regime | Value | Conf | Urgency | Diff-inv | Reput | Comm |
|---|---|---|---|---|---|---|
| **Bull** | 0.38 | 0.18 | 0.15 | 0.07 | 0.12 | 0.10 |
| **Neutral** (default) | 0.30 | 0.20 | 0.15 | 0.10 | 0.15 | 0.10 |
| **Bear** | 0.22 | 0.18 | 0.12 | 0.08 | 0.28 | 0.12 |
| **High-scam** | 0.20 | 0.15 | 0.10 | 0.07 | 0.38 | 0.10 |

### Implementation

```python
class MarketRegimeDetector:
    def __init__(self):
        self.cache_ttl = 3600  # re-evaluate hourly

    async def current_regime(self) -> dict:
        cache = await redis.get("market:regime")
        if cache: return json.loads(cache)
        signals = await self.gather_signals()
        regime = self.classify(signals)
        weights = self.WEIGHT_MATRIX[regime]
        await redis.set("market:regime", json.dumps(weights), ex=self.cache_ttl)
        return weights

    def classify(self, s: Signals) -> str:
        if s.scam_rate > 0.25:
            return "high_scam"
        if s.market_cap_delta_30d > 0.20:
            return "bull"
        if s.market_cap_delta_30d < -0.15:
            return "bear"
        return "neutral"
```

The scoring engine reads weights from `MarketRegimeDetector` instead of constants.

---

## 4. Cross-Opportunity Optimization (Gap #3)

**Problem:** A wallet pursuing 8 airdrops may bridge to the same L2 five times, deploy contracts on three chains, and swap on four DEXes — with no awareness that tasks overlap.

**Solution:** A **Task Orchestrator** that, given a wallet's active opportunities, produces one optimal execution plan minimizing gas and maximizing shared-task reuse.

### Overlap Types

| Type | Example | Saving |
|---|---|---|
| Same-chain bridge | Bridge to Arbitrum for both A and B | 1 of 2 bridges eliminated |
| Shared deploy | One contract deploy qualifies for 3 airdrops | 2 of 3 deploys eliminated |
| Shared DEX interaction | Same DEX used by A and B | Gas amortized |
| Shared testnet | One testnet tx counts for multiple | N−1 eliminated |

### Planner (simplified)

```python
class TaskOrchestrator:
    def plan(self, wallet, opportunities) -> ExecutionPlan:
        flat_tasks = [(opp, t) for opp in opportunities for t in opp.tasks if not done(wallet, t)]
        # Group by (chain, type, params-hash)
        groups = defaultdict(list)
        for opp, t in flat_tasks:
            key = (t.chain, t.type, self.param_hash(t))
            groups[key].append((opp, t))
        plan_steps = []
        for key, members in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            plan_steps.append(PlanStep(
                action=key,
                satisfies=[m[0].id for m in members],  # which opps this satisfies
                reuse_count=len(members),
                estimated_gas_usd=members[0][1].estimated_gas_usd,  # paid once
            ))
        total_gas = sum(s.estimated_gas_usd for s in plan_steps)
        naive_gas = sum(t.estimated_gas_usd for _, t in flat_tasks)
        return ExecutionPlan(
            steps=plan_steps,
            total_gas_usd=total_gas,
            naive_gas_usd=naive_gas,
            savings_pct=round(100 * (naive_gas - total_gas) / naive_gas, 1),
        )
```

### Output Example

```json
{
  "wallet": "0x1234...abcd",
  "naive_gas_usd": 180.00,
  "optimized_gas_usd": 132.50,
  "savings_pct": 26.4,
  "steps": [
    {"action": "bridge:arbitrum:0.5ETH", "satisfies": ["opp_a", "opp_b"], "reuse_count": 2, "gas_usd": 15},
    {"action": "deploy:arbitrum:contract", "satisfies": ["opp_a", "opp_c", "opp_d"], "reuse_count": 3, "gas_usd": 10},
    {"action": "swap:arbitrum:HSC", "satisfies": ["opp_a"], "reuse_count": 1, "gas_usd": 5}
  ]
}
```

The mining machine consumes `/api/v1/wallets/:addr/plan` instead of a flat task list.

---

## 5. Predictive Discovery (Gap #4)

**Problem:** Nabu finds airdrops *after* announcement. First movers capture the most.

**Solution:** Add a **Signals Engine** that monitors *pre-announcement* indicators.

### Leading Indicators

| Indicator | Source | Lead time |
|---|---|---|
| Funding round closed ($10M+) | Crunchbase, Messari, press | 3-9 months |
| Testnet activity spike (>200% WoW) | Custom RPC / Dune | 1-4 months |
| New contract deployments from known deployer clusters | Etherscan / RPC | 2-6 months |
| Governance proposal spike | Snapshot, Tally | 1-3 months |
| Job postings for "tokenomics" / "airdrop lead" | LinkedIn, Web3 job boards | 2-5 months |
| Bridge TVL inflow anomaly | LayerZero, CCIP, DefiLlama | 1-2 months |

### Anomaly Detector

```python
class AnomalyDetector:
    async def scan(self):
        for signal in self.LEADING_INDICATORS:
            series = await self.get_time_series(signal)
            z = self.zscore_last(series)
            if z > 3.0:
                await self.raise_lead(
                    signal=signal.name,
                    protocol=signal.protocol,
                    z_score=z,
                    confidence=min(1.0, z / 5),
                    recommended_watch=True,
                )
```

Leads enter a `leads` table (separate from `opportunities`) and surface in the dashboard as **"Watchlist"** with a confidence bar.

---

## 6. API: Per-Machine Limits + Abuse Detection (Gap #5)

### Per-Machine Rate Limits

Replace global tier limits with **per-`machine_id`** quotas:

```yaml
mining_machine_limits:
  default_per_minute: 120
  burst: 30
  per_machine_overrides:
    "mm_001": { per_minute: 600, burst: 100 }   # trusted, high-throughput
    "mm_002": { per_minute: 300, burst: 50 }
```

### Abuse Detection

| Pattern | Action |
|---|---|
| > 500 task reports / minute from one machine | Throttle + flag |
| Same tx_hash reported for 2+ wallets | Fraud alert (tx can't satisfy 2 wallets) |
| Task reported "completed" but on-chain verification fails 3× | Suspend machine |
| Reports arrive before on-chain confirmation (impossible latency) | Flag |
| Wallet state jumps 0→100% in < 1 block | Impossible — freeze |

```python
class AbuseDetector:
    async def check_report(self, machine_id, report):
        key = f"abuse:reports:{machine_id}"
        count = await redis.incr(key)
        await redis.expire(key, 60)
        if count > 500:
            await self.throttle(machine_id)
            await alerting.send("🚨 Abuse: report flood", f"Machine {machine_id}: {count} reports/min")
        if await db.tx_already_used(report.tx_hash, exclude_wallet=report.wallet):
            await self.fraud_alert(machine_id, report)
```

### IP Allowlisting

Mining machines register an expected egress IP/CIDR. Requests from unknown IPs for a known `machine_id` are rejected.

---

## 7. Dashboard: Mining Machine Fleet View (Gap #6)

New route: `/machines`

```
┌──────────────────────────────────────────────────────────────┐
│ 🤖 Mining Machines              [+ Register Machine]         │
├──────────────────────────────────────────────────────────────┤
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│ │ mm_001  │ │ mm_002  │ │ mm_003  │ │ mm_004  │       │
│ │ 🟢 Online│ │ 🟢 Online│ │ 🟡 Idle  │ │ 🔴 Error │       │
│ │ 12 opps │ │ 8 opps  │ │ 0 opps  │ │ 3 opps  │       │
│ │ $142 gas │ │ $98 gas  │ │ $0 gas  │ │ $12 gas  │       │
│ │ 94% succ │ │ 88% succ │ │ —       │ │ 40% succ │       │
│ └─────────┘ └─────────┘ └─────────┘ └─────────┘       │
├──────────────────────────────────────────────────────────────┤
│ 📋 Machine Detail: mm_001                                     │
│ Current task: Bridge 0.5 ETH → HyperScale (opp_a)          │
│ Progress: ████████░░ 80%                                   │
│ Uptime: 14d 6h │ Last heartbeat: 3s ago                  │
│ Assignments:                                                    │
│   opp_a  ████████░░ 80%  HyperScale                       │
│   opp_b  ██████░░░░ 60%  Nova Chain                      │
│   opp_c  ███░░░░░░░ 30%  Quantum DEX                     │
└──────────────────────────────────────────────────────────────┘
```

New DB table:

```sql
CREATE TABLE mining_machines (
    id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(100),
    status VARCHAR(20) DEFAULT 'idle',  -- online, idle, error, suspended
    egress_cidr TEXT[],
    current_task VARCHAR(100),
    total_gas_usd DECIMAL(12,2),
    success_rate DECIMAL(5,2),
    last_heartbeat TIMESTAMPTZ,
    registered_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 8. Scoring A/B Testing & Feedback Loop (Gap #7)

**Problem:** No way to know if the scoring formula actually predicts value.

**Solution:** Run **champion/challenger** scoring in parallel and record outcomes.

### Design

```python
class ScoringExperiment:
    CHAMPION = "weights_v1"      # current production weights
    CHALLENGERS = ["weights_v2_dynamic", "weights_v3_ml"]

    async def score(self, opp) -> dict:
        results = {self.CHAMPION: self.score_with(self.CHAMPION, opp)}
        for c in self.CHALLENGERS:
            results[c] = self.score_with(c, opp)
        # Persist all variants for later comparison
        await db.store_scoring_variants(opp.id, results)
        return results[self.CHAMPION]  # serve champion

    async def on_outcome(self, opp_id, actual_value_usd, actual_claimed: bool):
        variants = await db.get_scoring_variants(opp_id)
        for name, predicted in variants.items():
            await db.record_outcome(
                model=name,
                predicted_score=predicted["overall_score"],
                predicted_value=predicted["estimated_value_usd_max"],
                actual_value=actual_value_usd,
                claimed=actual_claimed,
            )
```

After 100+ outcomes, compute MAPE per variant. Promote challenger if it beats champion by > 5%.

---

## 9. Implementation Priority

| Priority | Item | Doc section | Effort |
|---|---|---|---|
| 🔴 High | On-chain wallet monitoring | §2 | Medium |
| 🔴 High | Dynamic scoring weights | §3 | Medium |
| 🟡 Medium | Cross-opportunity optimization | §4 | High |
| 🟡 Medium | Predictive discovery | §5 | High |
| 🟢 Low | API per-machine limits + abuse | §6 | Medium |
| 🟢 Low | Machine fleet dashboard | §7 | Medium |
| 🟢 Low | Scoring A/B + feedback | §8 | Medium |

---

## 10. Updated Roadmap (appended)

### Phase 5 — Hardening & Autonomy (Week 8+)
- [ ] On-chain wallet watcher (Alchemy Notify / Blocknative / RPC logs)
- [ ] Dynamic scoring weights from market regime detector
- [ ] Cross-opportunity task orchestrator (`/wallets/:addr/plan`)
- [ ] Predictive leads engine (anomaly detection on leading indicators)
- [ ] Per-machine API rate limits + abuse detection
- [ ] Mining machine fleet dashboard (`/machines`)
- [ ] Scoring champion/challenger A/B with outcome feedback loop
- [ ] Public read-only dashboard for community
