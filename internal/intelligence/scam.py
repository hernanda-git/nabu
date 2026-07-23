"""
𒀭 Scam Detection + Adversary Model
"""

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

from pydantic import BaseModel


class ScamVerdict(str, Enum):
    LEGIT = "legit"
    SUSPECTED = "suspected"
    SCAM = "scam"
    HONEYPOT = "honeypot"
    RUG_PULL = "rug_pull"
    UNKNOWN = "unknown"


@dataclass
class ScamCheckResult:
    verdict: ScamVerdict
    confidence: float
    reasons: list[str]
    factors: dict[str, float]  # factor_name -> score 0-1


class ScamDetector:
    """
    Multi-layer scam detection:
    1. Pattern matching on announcement text
    2. Contract analysis (honeypot, rug pull patterns)
    3. Social verification (impersonation, fake accounts)
    4. Adversary model (what would a scammer do?)
    """

    # Known scam patterns
    SCAM_PATTERNS = [
        (re.compile(r"send\s+(ETH|BTC|SOL|BNB)\s+to\s+receive"), "advance_fee", 0.95),
        (re.compile(r"free\s+(money|tokens?|airdrop)\s+(no\s+effort|instant|guaranteed)"), "too_good", 0.9),
        (re.compile(r"gas\s+fee\s+required\s+to\s+claim"), "gas_trap", 0.85),
        (re.compile(r"official\s+airdrop\s+contract"), "fake_contract", 0.8),
        (re.compile(r"claim\s+your\s+\w+\s+now\s+limited"), "urgency_pressure", 0.75),
        (re.compile(r"connect\s+wallet\s+to\s+verify"), "wallet_drain", 0.9),
        (re.compile(r"private\s+key|seed\s+phrase|mnemonic"), "credential_theft", 1.0),
    ]

    HONEYPOT_PATTERNS = [
        r"667.*7374616e64",  # suspicious opcodes
        r"73656c6c.*6279",    # "sell" function trap
    ]

    RUG_PULL_INDICATORS = {
        "anonymous_team": 0.3,
        "no_audit": 0.25,
        "unlocked_liquidity": 0.25,
        "high_token_supply": 0.1,
        "recent_creation": 0.1,
    }

    def __init__(self, redis_client=None, honeypot_api_key=None):
        self.redis = redis_client
        self.honeypot_api_key = honeypot_api_key

    async def analyze(self, event, analysis) -> ScamCheckResult:
        """Full scam analysis pipeline."""
        checks = await asyncio.gather(
            self.check_patterns(event),
            self.check_contract(analysis),
            self.check_social(event),
            self.check_adversary(event, analysis),
            return_exceptions=True,
        )

        all_reasons = []
        all_factors = {}
        
        for check in checks:
            if isinstance(check, ScamCheckResult):
                all_reasons.extend(check.reasons)
                all_factors.update(check.factors)
            elif isinstance(check, Exception):
                # Log but continue
                pass

        # Aggregate verdict
        if all_factors.get("honeypot", 0) > 0.8:
            verdict = ScamVerdict.HONEYPOT
            confidence = all_factors["honeypot"]
        elif all_factors.get("rug_pull", 0) > 0.7:
            verdict = ScamVerdict.RUG_PULL
            confidence = all_factors["rug_pull"]
        elif all_factors.get("scam", 0) > 0.6:
            verdict = ScamVerdict.SCAM
            confidence = all_factors["scam"]
        elif any(f > 0.5 for f in all_factors.values()):
            verdict = ScamVerdict.SUSPECTED
            confidence = max(all_factors.values())
        else:
            verdict = ScamVerdict.LEGIT
            confidence = 1.0 - max(all_factors.values(), default=0)

        return ScamCheckResult(
            verdict=verdict,
            confidence=confidence,
            reasons=all_reasons,
            factors=all_factors,
        )

    async def check_patterns(self, event) -> ScamCheckResult:
        """Text pattern matching on announcement."""
        text = event.raw_text.lower()
        reasons = []
        factors = {}

        for pattern, name, weight in self.SCAM_PATTERNS:
            if pattern.search(text):
                reasons.append(f"Pattern '{name}' matched in announcement")
                factors[f"pattern_{name}"] = weight

        if not reasons:
            return ScamCheckResult(ScamVerdict.LEGIT, 0.5, ["No scam patterns detected"], {"clean_text": 0.1})

        return ScamCheckResult(
            ScamVerdict.SUSPECTED,
            max(factors.values()),
            reasons,
            factors,
        )

    async def check_contract(self, analysis) -> ScamCheckResult:
        """Analyze contract for honeypot/rug patterns."""
        contract_addr = None
        if analysis.requirements:
            for req in analysis.requirements:
                if "contract" in req.parameters:
                    contract_addr = req.parameters["contract"]
                    break
        
        if not contract_addr:
            return ScamCheckResult(ScamVerdict.UNKNOWN, 0.3, ["No contract address found"], {})

        reasons = []
        factors = {}

        # Check bytecode for honeypot patterns
        bytecode = await self.fetch_bytecode(contract_addr)
        if bytecode:
            for pattern in self.HONEYPOT_PATTERNS:
                if re.search(pattern, bytecode):
                    reasons.append(f"Honeypot bytecode pattern detected")
                    factors["honeypot"] = 0.95

        # Check rug pull indicators
        rug_score = 0
        for indicator, weight in self.RUG_PULL_INDICATORS.items():
            if await self.check_rug_indicator(contract_addr, indicator):
                rug_score += weight
                reasons.append(f"Rug pull indicator: {indicator}")
        
        if rug_score > 0.5:
            factors["rug_pull"] = rug_score

        if not factors:
            return ScamCheckResult(ScamVerdict.LEGIT, 0.5, ["Contract checks passed"], {"clean_contract": 0.1})

        return ScamCheckResult(
            ScamVerdict.SUSPECTED,
            max(factors.values()) if factors else 0.3,
            reasons,
            factors,
        )

    async def check_social(self, event) -> ScamCheckResult:
        """Check for impersonation, fake accounts."""
        reasons = []
        factors = {}

        # Check if source is verified/known
        for source in event.sources:
            if source.source_type == "twitter":
                authority = await self.check_twitter_authority(source)
                if authority < 0.3:
                    reasons.append(f"Low authority source: {source.url}")
                    factors["low_authority_source"] = 1.0 - authority

        return ScamCheckResult(
            ScamVerdict.LEGIT if not factors else ScamVerdict.SUSPECTED,
            1.0 - max(factors.values()) if factors else 0.5,
            reasons,
            factors,
        )

    async def check_adversary(self, event, analysis) -> ScamCheckResult:
        """Adversary model: what would a scammer do to fool me?"""
        model = AdversaryModel()
        return await model.score_scam_likelihood(event, analysis)

    async def fetch_bytecode(self, address: str) -> Optional[str]:
        # Query RPC for contract bytecode
        return None

    async def check_rug_indicator(self, address: str, indicator: str) -> bool:
        # Query blockchain state
        return False

    async def check_twitter_authority(self, source) -> float:
        # Query source authority DB
        return 0.5


class AdversaryModel:
    """
    Models the attacker's incentives to fool the oracle.
    """

    def __init__(self):
        self.scam_patterns = ScamDetector().SCAM_PATTERNS

    async def score_scam_likelihood(self, event, analysis) -> ScamCheckResult:
        """Score from attacker's perspective."""
        factors = {}

        # P(fake_announcement)
        factors["fake_announcement"] = self.p_fake_announcement(event, analysis)

        # P(honeypot_contract)
        factors["honeypot_contract"] = await self.p_honeypot_contract(analysis)

        # P(rug_pull_pattern)
        factors["rug_pull_pattern"] = self.p_rug_pull_pattern(event, analysis)

        # P(impersonation)
        factors["impersonation"] = self.p_impersonation(event)

        # Combined score
        total = (
            0.4 * factors["fake_announcement"] +
            0.3 * factors["honeypot_contract"] +
            0.2 * factors["rug_pull_pattern"] +
            0.1 * factors["impersonation"]
        )

        if total > 0.7:
            verdict = ScamVerdict.SCAM
        elif total > 0.4:
            verdict = ScamVerdict.SUSPECTED
        else:
            verdict = ScamVerdict.LEGIT

        return ScamCheckResult(
            verdict=verdict,
            confidence=total,
            reasons=[f"Adversary score: {k}={v:.2f}" for k, v in factors.items()],
            factors=factors,
        )

    def p_fake_announcement(self, event, analysis) -> float:
        """Probability announcement is fabricated."""
        novelty = 1.0 if not analysis.existing_protocol else 0.0
        social_proof = len(event.sources) / 10.0
        urgency = 1.0 if analysis.timeline.claim_start and \
            (analysis.timeline.claim_start - datetime.now(timezone.utc)).days < 3 else 0.0
        
        # High novelty + low social proof + high urgency = suspicious
        return min(1.0, 0.5 * novelty - 0.3 * social_proof + 0.2 * urgency)

    async def p_honeypot_contract(self, analysis) -> float:
        # Would need contract analysis
        return 0.0

    def p_rug_pull_pattern(self, event, analysis) -> float:
        funding_anomaly = 1.0 if analysis.protocol_funding and analysis.protocol_funding > 10_000_000 else 0.0
        team_anon = 1.0 if analysis.team_anonymous else 0.0
        no_audit = 1.0 if not analysis.has_audit else 0.0
        return (funding_anomaly + team_anon + no_audit) / 3.0

    def p_impersonation(self, event) -> float:
        # Check for similar known accounts
        return 0.0