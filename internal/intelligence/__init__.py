"""
𒀭 NABU — Intelligence Layer
The Oracle's analytical brain: LLM analysis, scoring, task extraction, self-evolution.
"""

# nabu/intelligence/__init__.py
from .analysis import OpportunityAnalyzer, SpeculativeRouter
from .scoring import ScoringEngine, MarketRegimeDetector
from .tasks import TaskExtractor, TaskOrchestrator, GasRouter
from .scam import ScamDetector, AdversaryModel
from .patterns import HistoricalPatternEngine
from .authority import SourceAuthorityScorer
from .outcomes import OutcomeTracker, VerificationEngine
from .router import SpeculativeLLMRouter

__all__ = [
    "OpportunityAnalyzer",
    "SpeculativeRouter", 
    "ScoringEngine",
    "MarketRegimeDetector",
    "TaskExtractor",
    "TaskOrchestrator",
    "GasRouter",
    "ScamDetector",
    "AdversaryModel",
    "HistoricalPatternEngine",
    "SourceAuthorityScorer",
    "OutcomeTracker",
    "VerificationEngine",
    "SpeculativeLLMRouter",
]