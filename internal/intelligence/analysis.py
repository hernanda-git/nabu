"""
𒀭 Opportunity Analyzer — Core LLM Analysis Pipeline
"""

import asyncio
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from enum import Enum

from pydantic import BaseModel, Field, validator
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from nabu.intelligence.router import SpeculativeLLMRouter, LLMProvider
from nabu.intelligence.schemas import (
    NormalizedEvent, 
    AnalysisContext, 
    AnalysisResult,
    RiskFactor,
    Requirement,
    Timeline,
    EstimatedValue,
)


class Verdict(str, Enum):
    WORTHWHILE = "worthwhile"
    SPECULATIVE = "speculative"
    RISKY = "risky"
    SKIP = "skip"
    SCAM = "scam"


class OpportunityAnalyzer:
    """
    Main analysis pipeline: context → LLM → structured output.
    """

    def __init__(self, router: SpeculativeLLMRouter):
        self.router = router
        self.model = os.getenv("NABU_LLM_MODEL", "opencode-zen:default")

    async def analyze(self, event: NormalizedEvent, context: AnalysisContext) -> AnalysisResult:
        """Run full analysis on a normalized event."""
        
        # Build prompt with all context
        prompt = self.build_prompt(event, context)
        
        # Run speculative LLM analysis
        llm_response = await self.router.analyze(
            prompt=prompt,
            schema=AnalysisResult,
            min_confidence=0.75,
        )

        if not llm_response.success:
            # Fallback to heuristic analysis
            return await self.heuristic_analysis(event, context)

        result = llm_response.data
        result.analysis_version = 3
        result.analyzed_at = datetime.now(timezone.utc)
        result.opportunity_id = event.id
        
        return result

    def build_prompt(self, event: NormalizedEvent, context: AnalysisContext) -> str:
        """Construct the master analysis prompt."""
        
        sources_str = "\n".join([
            f"- {s.source_type}: {s.url} (collected: {s.collected_at})"
            for s in event.sources
        ])

        context_str = ""
        if context.social_context:
            context_str += f"\nSocial Context:\n{json.dumps(context.social_context, indent=2)}"
        if context.onchain_context:
            context_str += f"\nOn-Chain Context:\n{json.dumps(context.onchain_context, indent=2)}"
        if context.project_context:
            context_str += f"\nProject Context:\n{json.dumps(context.project_context, indent=2)}"

        return f"""You are Nabu, the airdrop intelligence oracle. Analyze this opportunity.

EVENT:
Title: {event.title}
Protocol: {event.protocol_name or "Unknown"}
Category: {event.category or "Unknown"}
Detected: {event.detected_at.isoformat()}
Sources:
{sources_str}
Raw Text: {event.raw_text[:5000]}

ADDITIONAL CONTEXT:
{context_str}

OUTPUT SCHEMA (JSON only):
{AnalysisResult.schema_json(indent=2)}

RULES:
1. Be precise — extract exact numbers, dates, addresses
2. If unknown, use null — never guess
3. Requirements must be machine-actionable (chain, contract, amounts)
4. Risk factors must be specific, not generic
5. Score 0-100 for overall, 1-10 for difficulty
6. Verdict must be one of: worthwhile, speculative, risky, skip, scam
"""

    async def heuristic_analysis(self, event: NormalizedEvent, context: AnalysisContext) -> AnalysisResult:
        """Fallback when all LLMs fail."""
        # Quick heuristic scoring based on keywords, source quality
        score = self.heuristic_score(event, context)
        
        return AnalysisResult(
            opportunity_id=event.id,
            analysis_version=0,
            analyzed_at=datetime.now(timezone.utc),
            is_airdrop=score > 40,
            explanation="Heuristic fallback analysis",
            protocol_name=event.protocol_name,
            category=event.category,
            estimated_value=EstimatedValue(
                min_tokens=None, max_tokens=None,
                estimated_usd_min=None, estimated_usd_max=None,
                confidence="low", token_name=None, token_type="unknown"
            ),
            timeline=Timeline(),
            requirements=[],
            risk_assessment=RiskAssessment(overall_risk="unknown", factors=[]),
            difficulty_score=5.0,
            overall_score=score,
            verdict=Verdict.SKIP if score < 40 else Verdict.SPECULATIVE,
        )

    def heuristic_score(self, event: NormalizedEvent, context: AnalysisContext) -> float:
        score = 50.0
        
        # Source quality
        if len(event.sources) >= 2:
            score += 15
        elif len(event.sources) == 1:
            score += 5
        
        # Keywords in raw text
        text = event.raw_text.lower()
        strong_signals = ["airdrop", "claim", "token launch", "tge", "genesis", "retroactive", "farming"]
        for kw in strong_signals:
            if kw in text:
                score += 5
        
        # Project context
        if context.project_context:
            if context.project_context.get("fundraising_total", 0) > 5_000_000:
                score += 10
            if context.project_context.get("has_audit"):
                score += 5
            if context.project_context.get("team_doxxed"):
                score += 5
        
        return max(0, min(100, score))


# ─── LLM Router Integration ───

@dataclass
class LLMProviderConfig:
    name: str
    model: str
    api_key: str
    base_url: Optional[str] = None
    weight: float = 1.0


class LLMProviders:
    """Configured provider chain for Opencode Zen + fallbacks."""
    
    PROVIDERS = [
        LLMProviderConfig(
            name="opencode-zen",
            model="default",
            api_key=os.getenv("OPENCODE_ZEN_KEY", ""),
            base_url=os.getenv("OPENCODE_ZEN_URL"),
            weight=1.0,
        ),
        LLMProviderConfig(
            name="deepseek",
            model="deepseek-v4-flash",
            api_key=os.getenv("DEEPSEEK_KEY", ""),
            weight=0.8,
        ),
        LLMProviderConfig(
            name="openrouter",
            model="laguna-s-2.1-free",
            api_key=os.getenv("OPENROUTER_KEY", ""),
            base_url="https://openrouter.ai/api/v1",
            weight=0.6,
        ),
        LLMProviderConfig(
            name="openrouter",
            model="nvidia/nemotron-3-ultra:free",
            api_key=os.getenv("OPENROUTER_KEY", ""),
            base_url="https://openrouter.ai/api/v1",
            weight=0.5,
        ),
        LLMProviderConfig(
            name="openrouter", 
            model="north-mini-code:free",
            api_key=os.getenv("OPENROUTER_KEY", ""),
            base_url="https://openrouter.ai/api/v1",
            weight=0.4,
        ),
    ]

    @classmethod
    def get_chain(cls) -> list[LLMProvider]:
        return [LLMProvider(**p.__dict__) for p in cls.PROVIDERS if p.api_key]


# ─── Schemas (Pydantic Models) ───

class NormalizedEvent(BaseModel):
    id: str
    title: str
    protocol_name: Optional[str]
    category: Optional[str]
    sources: list[SourceRef]
    raw_text: str
    detected_at: datetime
    networks: list[str] = Field(default_factory=list)
    confidence_score: float = 0.5

class SourceRef(BaseModel):
    source_type: str
    url: str
    collected_at: datetime
    metadata: dict = Field(default_factory=dict)

class AnalysisContext(BaseModel):
    social_context: Optional[dict] = None
    onchain_context: Optional[dict] = None
    project_context: Optional[dict] = None
    existing_opportunities: list[str] = Field(default_factory=list)
    similar_opportunities: list[str] = Field(default_factory=list)


class EstimatedValue(BaseModel):
    min_tokens: Optional[int] = None
    max_tokens: Optional[int] = None
    estimated_usd_min: Optional[float] = None
    estimated_usd_max: Optional[float] = None
    confidence: str = "medium"  # low, medium, high
    token_name: Optional[str] = None
    token_type: str = "unknown"  # governance, utility, meme, security, unknown


class Timeline(BaseModel):
    snapshot_date: Optional[datetime] = None
    claim_start: Optional[datetime] = None
    claim_end: Optional[datetime] = None
    tge_date: Optional[datetime] = None
    estimated_tge_quarter: Optional[str] = None


class Requirement(BaseModel):
    id: str
    type: str  # bridge, swap, lp, stake, mint_nft, deploy, vote, social, referral, testnet, other
    description: str
    optional: bool = False
    chain: Optional[str] = None
    estimated_gas_usd: Optional[float] = None
    parameters: dict = Field(default_factory=dict)


class RiskFactor(BaseModel):
    name: str
    risk: str  # low, medium, high
    detail: str


class RiskAssessment(BaseModel):
    overall_risk: str  # low, medium, high, critical
    factors: list[RiskFactor] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    opportunity_id: str
    analysis_version: int
    analyzed_at: datetime
    is_airdrop: bool = True
    explanation: str
    protocol_name: Optional[str] = None
    category: Optional[str] = None
    estimated_value: EstimatedValue = Field(default_factory=EstimatedValue)
    timeline: Timeline = Field(default_factory=Timeline)
    requirements: list[Requirement] = Field(default_factory=list)
    risk_assessment: RiskAssessment = Field(default_factory=RiskAssessment)
    difficulty_score: float = 5.0
    overall_score: float = 0.0
    verdict: Verdict = Verdict.SKIP