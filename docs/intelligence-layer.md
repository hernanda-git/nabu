# 🧠 Intelligence Layer — The Oracle

> *"Raw data becomes prophecy."*

---

## 1. Overview

The Intelligence Layer is Nabu's **analytical core**. It consumes raw/normalized events from RabbitMQ, processes them through a multi-stage pipeline powered by LLMs, heuristics, and rule engines, and produces structured, scored, actionable airdrop opportunities.

```
Raw Event → Normalize → Context Builder → LLM Analysis → Scoring → Persist → Notify
                                              ↓
                                       [Fallback Chain]
                                       Claude → GPT-4 → DeepSeek → Local LLM
```

---

## 2. Pipeline Stages

### Stage 1: Opportunity Classification

**Goal**: Determine if a raw event represents a genuine airdrop opportunity.

**Method**: Multi-factor heuristic + LLM classifier

```python
class OpportunityClassifier:
    """
    Fast pre-filter before LLM analysis to avoid wasting tokens.
    """

    # High-precision keyword patterns (no NLP needed)
    STRONG_SIGNALS = [
        r"\bairdrop\b", r"\bclaim\s+(your\s+)?(tokens|rewards)\b",
        r"\bretroactive\b", r"\btoken\s+(launch|distribution|generation)\b",
        r"\bTGE\b", r"\bfarming\s+(opportunity|season)\b",
        r"\bgenesis\s+(drop|reward)\b", r"\bgovernance\s+token\b",
    ]

    # Weak signals (need more context)
    WEAK_SIGNALS = [
        r"\blaunch", r"\bincentive", r"\brewards", r"\bstaking",
        r"\bliquidity\s+(mining|provision)", r"\bbridge", r"\btestnet",
    ]

    def classify(self, event: RawEvent) -> ClassificationResult:
        confidence = self.calculate_confidence(event)
        if confidence > 0.7:
            return ClassificationResult(is_airdrop=True, confidence=confidence, method="heuristic")
        elif confidence > 0.3:
            return ClassificationResult(is_airdrop=True, confidence=confidence, method="llm_needed")
        else:
            return ClassificationResult(is_airdrop=False, confidence=confidence, method="discard")
```

### Stage 2: Context Building

**Goal**: Assemble all available information about a protocol/project into a rich context for LLM analysis.

```python
class ContextBuilder:
    """
    Scrapes and aggregates information from multiple sources.
    """

    async def build_context(self, event: NormalizedEvent) -> AnalysisContext:
        protocol_name = self.extract_protocol_name(event)
        return AnalysisContext(
            protocol_name=protocol_name,
            event=event,
            social_context=await self.gather_social(protocol_name),
            onchain_context=await self.gather_onchain(protocol_name),
            project_context=await self.gather_project_info(protocol_name),
            existing_opportunities=self.find_existing(protocol_name),
            similar_opportunities=self.find_similar(event)
        )

    async def gather_onchain(self, name: str) -> OnchainContext:
        """Check if the protocol already has a token, TVL, contracts."""
        return OnchainContext(
            has_token=await self.check_token_deployment(name),
            tvl=await self.defillama.get_tvl(name),
            contracts=await self.find_contracts(name),
            age_days=await self.get_contract_age(name),
        )

    async def gather_project_info(self, name: str) -> ProjectContext:
        """Scrape website, Crunchbase, docs, GitHub."""
        return ProjectContext(
            website=await self.scrape_website(name),
            github=await self.check_github(name),
            fundraising=await self.check_fundraising(name),
            team=await self.check_team_info(name),
            audits=await self.check_audits(name),
            doc_quality=await self.assess_docs(name),
        )
```

### Stage 3: LLM Analysis (The Core)

**Goal**: Extract structured data from unstructured announcements.

**System Prompt Architecture**:

```
You are Nabu, the airdrop intelligence oracle. Analyze the following
crypto project announcement and extract structured opportunity data.

You must output valid JSON following this schema:

{
  "is_airdrop": bool,
  "explanation": string,
  "protocol_name": string | null,
  "category": "l1"|"l2"|"l3"|"defi"|"dex"|"bridge"|"nft"|"gaming"|"social"|"infra"|"other",
  "estimated_value": {
    "min_tokens": int|null,
    "max_tokens": int|null,
    "estimated_usd_min": int|null,
    "estimated_usd_max": int|null,
    "confidence": "low"|"medium"|"high",
    "token_name": string|null,
    "token_type": "governance"|"utility"|"meme"|"security"|"unknown"
  },
  "timeline": {
    "snapshot_date": string|null,
    "claim_start": string|null,
    "claim_end": string|null,
    "tge_date": string|null,
    "estimated_tge_quarter": string|null
  },
  "requirements": [
    {
      "type": "bridge"|"swap"|"lp"|"stake"|"mint_nft"|"deploy"|"vote"|"social"|"referral"|"testnet"|"other",
      "description": string,
      "optional": bool,
      "chain": string|null,
      "estimated_gas_usd": number|null
    }
  ],
  "risk_assessment": {
    "overall_risk": "low"|"medium"|"high"|"critical",
    "factors": [
      {
        "name": string,
        "risk": "low"|"medium"|"high",
        "detail": string
      }
    ]
  },
  "difficulty_score": number, // 1-10
  "overall_score": number,    // 0-100
  "verdict": "worthwhile"|"speculative"|"risky"|"skip"|"scam"
}

---

ANNOUNCEMENT:

{event_text}

ADDITIONAL CONTEXT:

{context_summary}
```

**Fallback Chain**:
```python
ANALYSIS_MODELS = [
    ("claude-sonnet-4", "anthropic"),
    ("gpt-4o", "openai"),
    ("deepseek-v4", "deepseek"),
    ("llama-4-70b", "local"),  # fallback when all APIs fail
]

async def analyze_opportunity(context: AnalysisContext) -> AnalysisResult:
    for model, provider in ANALYSIS_MODELS:
        try:
            result = await llm_call(model, provider, build_prompt(context))
            validated = AnalysisResult.model_validate_json(result)
            if validated.is_airdrop:
                return validated
        except Exception as e:
            logger.warning(f"Model {model} failed: {e}")
            continue
    raise AnalysisError("All models failed for this opportunity")
```

### Stage 4: Scoring Engine

**Multi-factor scoring algorithm**:

```python
class ScoringEngine:
    WEIGHTS = {
        "value_score": 0.30,        # Estimated USD value
        "confidence_score": 0.20,   # LLM confidence in analysis
        "timeline_urgency": 0.15,   # How soon we need to act
        "difficulty_inverse": 0.10, # Easy = higher score
        "reputation_score": 0.15,   # Team, investors, audits
        "community_score": 0.10,    # Social signals, TVL
    }

    def calculate(self, analysis: AnalysisResult, context: AnalysisContext) -> float:
        scores = {
            "value_score": self.score_value(analysis.estimated_value),
            "confidence_score": self.score_confidence(analysis.estimated_value.confidence),
            "timeline_urgency": self.score_timeline(analysis.timeline),
            "difficulty_inverse": self.score_difficulty(analysis.difficulty_score),
            "reputation_score": self.score_reputation(analysis.risk_assessment, context),
            "community_score": self.score_community(context),
        }

        return sum(scores[k] * self.WEIGHTS[k] for k in self.WEIGHTS)

    def score_value(self, value) -> float:
        if not value or value.estimated_usd_max is None:
            return 10  # Unknown value = low-medium
        avg = (value.estimated_usd_min + value.estimated_usd_max) / 2
        # Exponential curve: $100 → 10, $10K → 50, $100K → 80, $1M+ → 100
        return min(100, math.log10(max(1, avg)) * 25 - 40)

    def score_timeline(self, timeline) -> float:
        """Urgency score: about to start = high, far away = medium, done = 0"""
        if not timeline or not timeline.claim_start:
            return 50  # Unknown timeline = mid
        days_until = (timeline.claim_start - now).days
        if days_until < 0: return 0      # Already started/past
        if days_until < 7: return 100     # Starting within a week
        if days_until < 30: return 80     # Starting within a month
        if days_until < 90: return 50     # Starting within a quarter
        return 20                          # Far future
```

### Stage 5: Task Extraction

**Goal**: Convert natural language requirements into structured, machine-actionable tasks.

```python
TASK_TEMPLATES = {
    "bridge": BridgeTask,
    "swap": SwapTask,
    "lp": LPTask,
    "stake": StakeTask,
    "mint_nft": MintNFTTask,
    "deploy": DeployContractTask,
    "vote": VoteTask,
    "social": SocialTask,
    "testnet": TestnetTask,
}

class TaskExtractor:
    """Converts LLM-extracted requirements into chain-specific executable tasks."""

    CHAIN_CONFIGS = {
        "ethereum": {"rpc": "...", "explorer": "etherscan", "native_currency": "ETH"},
        "arbitrum": {"rpc": "...", "explorer": "arbiscan", "native_currency": "ETH"},
        "solana": {"rpc": "...", "explorer": "solscan", "native_currency": "SOL"},
        "base": {"rpc": "...", "explorer": "basescan", "native_currency": "ETH"},
        # ... 15+ chains
    }

    def extract(self, analysis: AnalysisResult, context: AnalysisContext) -> list[StructuredTask]:
        tasks = []
        for req in analysis.requirements:
            template = TASK_TEMPLATES.get(req.type)
            if not template:
                continue
            chain_config = self.CHAIN_CONFIGS.get(req.chain)
            tasks.append(template(
                description=req.description,
                chain=req.chain,
                chain_config=chain_config,
                optional=req.optional,
                gas_estimate=req.estimated_gas_usd,
            ))
        return tasks
```

---

## 3. LLM Cost Management

| Strategy | Savings |
|---|---|
| **Heuristic pre-filter** | Only 15% of events reach LLM |
| **Prompt caching** | Repeated protocols reuse analysis |
| **Batch analysis** | Up to 10 announcements per LLM call (when from same source) |
| **Model tiering** | High-value → Claude/GPT-4. Low-confidence → cheaper models |
| **Incremental analysis** | Don't re-analyze known protocols unless new info |
| **Tiered depth** | Quick scan (2k tokens) vs deep analysis (8k tokens) |

**Estimated monthly LLM cost**:
```
Events per day: ~5,000
After pre-filter: ~750 reach LLM
Tokens per analysis: ~3,000 input / ~800 output
Total monthly tokens: ~67.5M input / ~18M output
Estimated cost: ~$150-300/month (with fallback chain optimizations)
```

---

## 4. Scam Detection

```python
class ScamDetector:
    """
    Multi-layer scam/fraud detection before an opportunity is presented.
    """

    SIGNATURES = [
        # Known scam patterns
        r"send\s+(ETH|BTC|SOL)\s+to\s+receive",
        r"free\s+money\s+no\s+effort",
        r"gas\s+fee\s+required",
        r"official\s+airdrop\s+contract",
        r"claim\s+your\s+\w+\s+now\s+limited",
    ]

    async def analyze(self, event: RawEvent, analysis: AnalysisResult) -> ScamResult:
        checks = [
            self.check_patterns(event),
            self.check_contract_analysis(event),
            self.check_social_verification(event),
            self.check_impersonation(event),
            self.check_audit_exists(analysis),
            self.check_abnormal_requirements(analysis),
        ]
        results = await asyncio.gather(*checks)
        scam_score = sum(r.score * r.weight for r in results)

        return ScamResult(
            is_scam=scam_score > 60,
            scam_score=scam_score,
            reasons=[r.reason for r in results if r.flagged],
        )

    async def check_contract_analysis(self, event) -> CheckResult:
        """If a contract is mentioned, analyze it for known honeypot patterns."""
        contract_address = extract_contract(event)
        if not contract_address:
            return CheckResult(score=0, weight=0)

        # Check with Honeypot.is API, or run static analysis
        is_honeypot = await self.honeypot_check(contract_address)
        return CheckResult(
            score=100 if is_honeypot else 0,
            weight=0.3,
            flagged=is_honeypot,
            reason=f"Contract {contract_address} flagged as potential honeypot"
        )
```

---

## 5. Wallet State Tracking

**Goal**: Know what each wallet has accomplished so the mining machine doesn't repeat work.

```python
class WalletStateTracker:
    """
    Maintains a real-time view of what each wallet has done per opportunity.
    """

    async def get_pending_tasks(self, wallet: str, opportunity_id: str) -> list[Task]:
        all_tasks = await db.get_tasks(opportunity_id)
        completed = await db.get_completed_tasks(wallet, opportunity_id)
        return [t for t in all_tasks if t.id not in completed]

    async def verify_task_completion(self, wallet: str, task_id: str, tx_hash: str) -> bool:
        """
        Verify on-chain that a task was actually completed.
        Prevents the mining machine from lying about completions.
        """
        task = await db.get_task(task_id)
        if task.type == "bridge":
            return await self.verify_bridge_tx(tx_hash, task.chain)
        elif task.type == "swap":
            return await self.verify_swap_tx(tx_hash, task.chain)
        # ... etc
        return False

    async def update_wallet_state(self, wallet: str, opportunity_id: str, task_id: str, status: str):
        await db.upsert_wallet_state(
            address=wallet,
            opportunity_id=opportunity_id,
            task_statuses=json.dumps({task_id: status}),
            last_activity=datetime.utcnow()
        )
```

---

## 5b. On-Chain Wallet Monitoring (Gap #1 — see docs/improvements-v2.md §2)

**Problem with v1:** wallet state is *passive* — the mining machine reports completion and Nabu trusts it. No ground truth if a machine lies or crashes mid-task.

**Fix:** add a **Wallet Watcher** that independently observes on-chain activity and reconciles against reported state.

```python
class WalletReconciliation:
    async def on_chain_event(self, wallet, chain, event_type, tx_hash, block):
        task = await db.match_task(wallet, chain, event_type, tx_hash)
        if not task:
            await db.record_unattributed_activity(wallet, chain, event_type, tx_hash)
            return
        reported = await db.get_reported_status(wallet, task.id)
        if reported and reported.tx_hash != tx_hash:
            await self.flag_conflict(wallet, task.id, reported.tx_hash, tx_hash)
            return
        await db.mark_task_verified(wallet, task.id, tx_hash, block)

    async def flag_conflict(self, wallet, task_id, reported_tx, observed_tx):
        await db.insert_event(Event(
            type="wallet.task_conflict", wallet_address=wallet,
            data={"task_id": task_id, "reported_tx": reported_tx, "observed_tx": observed_tx}))
        await alerting.send("⚠️ Task conflict",
            f"Wallet {wallet} task {task_id}: reported {reported_tx} but chain shows {observed_tx}")
```

**Providers:** Alchemy Notify (webhook on address activity), Blocknative (mempool→confirmed), custom RPC `eth_getLogs` filtered by address+topic, The Graph subgraphs per protocol.

**New events:** `wallet.activity_detected`, `wallet.task_verified`, `wallet.task_conflict`, `wallet.unattributed`.

---

## 5c. Dynamic Scoring Weights (Gap #2 — see docs/improvements-v2.md §3)

Fixed weights ignore market regime. A **Market Regime Detector** adjusts them hourly from on-chain macro signals.

| Regime | Value | Conf | Urgency | Diff-inv | Reput | Comm |
|---|---|---|---|---|---|---|
| Bull | 0.38 | 0.18 | 0.15 | 0.07 | 0.12 | 0.10 |
| Neutral (default) | 0.30 | 0.20 | 0.15 | 0.10 | 0.15 | 0.10 |
| Bear | 0.22 | 0.18 | 0.12 | 0.08 | 0.28 | 0.12 |
| High-scam | 0.20 | 0.15 | 0.10 | 0.07 | 0.38 | 0.10 |

```python
class MarketRegimeDetector:
    async def current_regime(self) -> dict:
        cache = await redis.get("market:regime")
        if cache: return json.loads(cache)
        signals = await self.gather_signals()
        weights = self.WEIGHT_MATRIX[self.classify(signals)]
        await redis.set("market:regime", json.dumps(weights), ex=3600)
        return weights

    def classify(self, s) -> str:
        if s.scam_rate > 0.25: return "high_scam"
        if s.market_cap_delta_30d > 0.20: return "bull"
        if s.market_cap_delta_30d < -0.15: return "bear"
        return "neutral"
```

The scoring engine reads weights from `MarketRegimeDetector` instead of constants.

---

## 6. Predictive Analytics (Phase 4)

**Goal**: Predict airdrop value before official announcements.

```python
class PredictiveScorer:
    """
    ML model trained on historical airdrop outcomes to predict future value.
    Features include:
    - Protocol TVL trajectory
    - Funding amount & investor quality
    - GitHub activity (commits, contributors, stars)
    - Social media growth rate
    - Code audit existence & quality
    - Team background
    - Fee revenue / protocol earnings
    - Competitor analysis
    - Tokenomics similarity to past successful airdrops
    """

    MODEL_PATH = "models/airdrop_predictor_v1.pkl"

    FEATURES = [
        "tvl_usd", "tvl_growth_30d", "funding_total_usd",
        "investor_quality_score", "github_stars", "github_commits_30d",
        "twitter_followers", "twitter_growth_30d", "discord_members",
        "has_audit", "auditor_quality_score", "team_doxxed",
        "revenue_annual_usd", "total_value_locked",
        "competition_intensity", "category_niche_score",
    ]

    def predict(self, protocol: ProtocolContext) -> Prediction:
        features = self.extract_features(protocol)
        if self.model is None:
            return Prediction(estimate=50, confidence=0.3)  # No model yet
        return self.model.predict(features)
```

---

## 7. Data Enrichment

Beyond LLM analysis, each opportunity is enriched with:

| Enrichment | Source | Method |
|---|---|---|
| TVL data | DefiLlama API | Direct API call |
| Token price | CoinGecko/DefiLlama | Historical + current price |
| Social metrics | Twitter API, Discord bot | Follower count, growth rate |
| Audit info | Audit firm websites | Scrape or known DB |
| VC portfolio | Messari/Crunchbase | Fundraising round data |
| Code quality | GitHub API | Stars, forks, recent commits |
| Competitor set | Internal DB | Similar protocols and their outcomes |
