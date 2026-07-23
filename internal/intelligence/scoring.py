"""
𒀭 Scoring Engine — Dynamic, Market-Aware, Self-Correcting
"""

import json
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

from pydantic import BaseModel

from nabu.intelligence.schemas import AnalysisResult, RiskAssessment


class MarketRegime(str, Enum):
    BULL = "bull"
    NEUTRAL = "neutral"
    BEAR = "bear"
    HIGH_SCAM = "high_scam"


@dataclass
class MarketSignals:
    market_cap_delta_30d: float = 0.0
    scam_rate_30d: float = 0.0
    median_gas_price_gwei: float = 20.0
    funding_total_30d: float = 0.0
    active_opportunities: int = 0
    avg_difficulty: float = 5.0


# ─── Weight Matrices per Regime ───

WEIGHT_MATRIX = {
    MarketRegime.BULL: {
        "value_score": 0.38,
        "confidence_score": 0.18,
        "timeline_urgency": 0.15,
        "difficulty_inverse": 0.07,
        "reputation_score": 0.12,
        "community_score": 0.10,
    },
    MarketRegime.NEUTRAL: {
        "value_score": 0.30,
        "confidence_score": 0.20,
        "timeline_urgency": 0.15,
        "difficulty_inverse": 0.10,
        "reputation_score": 0.15,
        "community_score": 0.10,
    },
    MarketRegime.BEAR: {
        "value_score": 0.22,
        "confidence_score": 0.18,
        "timeline_urgency": 0.12,
        "difficulty_inverse": 0.08,
        "reputation_score": 0.28,
        "community_score": 0.12,
    },
    MarketRegime.HIGH_SCAM: {
        "value_score": 0.20,
        "confidence_score": 0.15,
        "timeline_urgency": 0.10,
        "difficulty_inverse": 0.07,
        "reputation_score": 0.38,
        "community_score": 0.10,
    },
}

DEFAULT_WEIGHTS = WEIGHT_MATRIX[MarketRegime.NEUTRAL]


class MarketRegimeDetector:
    """
    Detects market regime from on-chain macro signals.
    Updates hourly, cached in Redis.
    """

    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.cache_key = "nabu:market:regime"
        self.cache_ttl = 3600  # 1 hour

    async def current_regime(self) -> dict:
        """Returns current regime with weights."""
        if self.redis:
            cached = await self.redis.get(self.cache_key)
            if cached:
                return json.loads(cached)

        signals = await self.gather_signals()
        regime = self.classify(signals)
        weights = WEIGHT_MATRIX[regime]

        result = {
            "regime": regime.value,
            "weights": weights,
            "signals": {
                "market_cap_delta_30d": signals.market_cap_delta_30d,
                "scam_rate_30d": signals.scam_rate_30d,
                "median_gas_price_gwei": signals.median_gas_price_gwei,
                "funding_total_30d": signals.funding_total_30d,
                "active_opportunities": signals.active_opportunities,
            },
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if self.redis:
            await self.redis.setex(self.cache_key, self.cache_ttl, json.dumps(result))

        return result

    async def gather_signals(self) -> MarketSignals:
        """Gather macro signals from various sources."""
        # In production: query CoinGecko, DefiLlama, internal DB, RPC
        return MarketSignals(
            market_cap_delta_30d=0.15,      # +15% = bullish
            scam_rate_30d=0.12,             # 12% scam rate
            median_gas_price_gwei=18.0,     # moderate
            funding_total_30d=50_000_000,   # $50M raised
            active_opportunities=42,        # current active
            avg_difficulty=5.3,
        )

    def classify(self, s: MarketSignals) -> MarketRegime:
        # High scam rate overrides everything
        if s.scam_rate_30d > 0.25:
            return MarketRegime.HIGH_SCAM
        if s.market_cap_delta_30d > 0.20:
            return MarketRegime.BULL
        if s.market_cap_delta_30d < -0.15:
            return MarketRegime.BEAR
        return MarketRegime.NEUTRAL


class ScoringEngine:
    """
    Dynamic scoring with regime-aware weights.
    Integrates with SelfCorrectionEngine for weight updates.
    """

    def __init__(self, regime_detector: MarketRegimeDetector):
        self.regime_detector = regime_detector
        self.weights = DEFAULT_WEIGHTS.copy()
        self.factor_names = list(DEFAULT_WEIGHTS.keys())

    async def calculate(self, analysis: AnalysisResult, context: dict = None) -> float:
        """Calculate overall score using current regime weights."""
        
        # Update weights from regime detector
        regime_info = await self.regime_detector.current_regime()
        self.weights = regime_info["weights"]

        # Extract sub-scores from analysis
        scores = {
            "value_score": self._score_value(analysis.estimated_value),
            "confidence_score": self._score_confidence(analysis.estimated_value.confidence),
            "timeline_urgency": self._score_timeline(analysis.timeline),
            "difficulty_inverse": self._score_difficulty(analysis.difficulty_score),
            "reputation_score": self._score_reputation(analysis.risk_assessment, context),
            "community_score": self._score_community(context),
        }

        # Weighted sum
        total = sum(scores[k] * self.weights[k] for k in self.weights)
        return round(total, 2)

    def _score_value(self, ev: EstimatedValue) -> float:
        if not ev or ev.estimated_usd_max is None:
            return 10.0
        avg = (ev.estimated_usd_min + ev.estimated_usd_max) / 2
        # Log curve: $100→10, $1K→30, $10K→60, $100K→85, $1M+→100
        return min(100, np.log10(max(1, avg)) * 25 - 40)

    def _score_confidence(self, conf: str) -> float:
        return {"high": 90, "medium": 50, "low": 20}.get(conf, 30)

    def _score_timeline(self, tl: Timeline) -> float:
        if not tl.claim_start:
            return 50
        days = (tl.claim_start - datetime.now(timezone.utc)).days
        if days < 0: return 0
        if days < 7: return 100
        if days < 30: return 80
        if days < 90: return 50
        return 20

    def _score_difficulty(self, diff: float) -> float:
        # Inverse: easy (1-3) = high score, hard (8-10) = low score
        return max(0, 100 - diff * 12)

    def _score_reputation(self, risk: RiskAssessment, context: dict) -> float:
        if not risk or not risk.factors:
            return 50
        score = 50
        for f in risk.factors:
            if f.risk == "high":
                score -= 15
            elif f.risk == "medium":
                score -= 5
            elif f.risk == "low":
                score += 5
        # Boost for audits, VC backing
        if context:
            if context.get("has_audit"): score += 10
            if context.get("vc_backing"): score += 10
            if context.get("team_doxxed"): score += 5
        return max(0, min(100, score))

    def _score_community(self, context: dict) -> float:
        if not context:
            return 30
        score = 30
        if context.get("twitter_followers", 0) > 50000: score += 15
        elif context.get("twitter_followers", 0) > 10000: score += 10
        if context.get("discord_members", 0) > 20000: score += 15
        elif context.get("discord_members", 0) > 5000: score += 10
        if context.get("github_stars", 0) > 1000: score += 10
        return min(100, score)


# ─── Self-Correction Engine ───

class SelfCorrectionEngine:
    """
    Gradient descent on scoring weights based on prediction accuracy.
    Runs hourly, retrains weights from historical outcomes.
    """

    def __init__(self, db_pool, redis_client=None):
        self.db = db_pool
        self.redis = redis_client
        self.learning_rate = 0.01
        self.min_samples = 100

    async def retrain(self):
        """Retrain weights from historical outcomes."""
        # Get outcomes with predictions
        outcomes = await self.fetch_outcomes()
        if len(outcomes) < self.min_samples:
            return

        # Extract features and errors
        X, y_pred, y_actual = self.prepare_training_data(outcomes)
        if len(X) < self.min_samples:
            return

        errors = y_actual - y_pred
        gradients = X.T @ errors / len(X)

        # Update weights
        new_weights = np.array([self.weights[k] for k in self.factor_names])
        new_weights += self.learning_rate * gradients
        new_weights = np.clip(new_weights, 0.01, 0.5)  # bounds
        new_weights /= new_weights.sum()  # normalize

        # Update in Redis
        if self.redis:
            updated = {k: float(v) for k, v in zip(self.factor_names, new_weights)}
            await self.redis.set("nabu:scoring:weights", json.dumps(updated))

        self.weights = {k: float(v) for k, v in zip(self.factor_names, new_weights)}

    async def fetch_outcomes(self) -> list:
        """Fetch historical outcomes from database."""
        query = """
            SELECT actual_value_usd, claimed, scoring_weights, regime_at_time
            FROM historical_outcomes
            WHERE completed_at > NOW() - INTERVAL '90 days'
              AND actual_value_usd IS NOT NULL
        """
        # Execute query
        return []  # placeholder

    def prepare_training_data(self, outcomes: list) -> tuple:
        X, y_pred, y_actual = [], [], []
        for o in outcomes:
            features = self.extract_features(o)
            X.append(features)
            y_pred.append(o["scoring_weights"].get("overall_score", 50))
            y_actual.append(min(100, o["actual_value_usd"] / 100))  # normalize
        return np.array(X), np.array(y_pred), np.array(y_actual)

    def extract_features(self, outcome: dict) -> np.ndarray:
        weights = outcome.get("scoring_weights", {})
        return np.array([weights.get(k, 0) for k in self.factor_names])