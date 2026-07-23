"""
𒀭 Speculative LLM Router — Parallel calls, first confident win
"""

import asyncio
import os
import time
from dataclasses import dataclass
from typing import Any, Optional, Type, TypeVar
from pydantic import BaseModel

from nabu.intelligence.analysis import LLMProviders, LLMProviderConfig

T = TypeVar("T", bound=BaseModel)


@dataclass
class LLMResult:
    success: bool
    data: Optional[Any] = None
    confidence: float = 0.0
    provider: str = ""
    model: str = ""
    latency_ms: int = 0
    error: Optional[str] = None
    raw_response: Optional[str] = None


@dataclass 
class LLMProvider:
    name: str
    model: str
    api_key: str
    base_url: Optional[str] = None
    weight: float = 1.0


class SpeculativeLLMRouter:
    """
    Parallel LLM calls with first-confident-win strategy.
    Falls back through provider chain.
    """

    def __init__(
        self,
        providers: Optional[list[LLMProvider]] = None,
        timeout_seconds: int = 30,
        min_confidence: float = 0.75,
    ):
        self.providers = providers or LLMProviders.get_chain()
        self.timeout = timeout_seconds
        self.min_confidence = min_confidence
        self.client = httpx.AsyncClient(timeout=timeout_seconds)

    async def analyze(
        self,
        prompt: str,
        schema: Type[T],
        min_confidence: Optional[float] = None,
    ) -> "LLMAnalysisResult[T]":
        """Run speculative analysis across all providers in parallel."""
        
        min_conf = min_confidence or self.min_confidence
        tasks = [
            self._call_provider(p, prompt, schema)
            for p in self.providers
        ]
        
        done, pending = await asyncio.wait(
            tasks,
            timeout=self.timeout,
            return_when=asyncio.FIRST_COMPLETED,
        )
        
        # Check completed for confident result
        for task in done:
            result = task.result()
            if result.success and result.confidence >= min_conf:
                # Cancel pending
                for p in pending:
                    p.cancel()
                return LLMAnalysisResult(
                    success=True,
                    data=result.data,
                    confidence=result.confidence,
                    provider=result.provider,
                    model=result.model,
                    latency_ms=result.latency_ms,
                )
        
        # Wait for remaining (with shorter timeout)
        remaining_timeout = max(0, self.timeout - 2)
        if pending:
            done2, _ = await asyncio.wait(pending, timeout=remaining_timeout)
            for task in done2:
                result = task.result()
                if result.success and result.confidence >= min_conf:
                    return LLMAnalysisResult(
                        success=True,
                        data=result.data,
                        confidence=result.confidence,
                        provider=result.provider,
                        model=result.model,
                        latency_ms=result.latency_ms,
                    )
        
        # No confident result — ensemble or best effort
        all_results = [t.result() for t in done if not t.cancelled()]
        all_results.extend([t.result() for t in pending if not t.cancelled()])
        
        successful = [r for r in all_results if r.success]
        if not successful:
            return LLMAnalysisResult(
                success=False,
                error="All providers failed",
                provider="none",
            )
        
        # Ensemble average
        return self._ensemble(successful, schema)

    async def _call_provider(
        self,
        provider: LLMProvider,
        prompt: str,
        schema: Type[T],
    ) -> LLMResult:
        start = time.time()
        
        try:
            if provider.name == "opencode-zen":
                result = await self._call_opencode_zen(provider, prompt, schema)
            elif provider.name == "deepseek":
                result = await self._call_deepseek(provider, prompt, schema)
            elif provider.name == "openrouter":
                result = await self._call_openrouter(provider, prompt, schema)
            else:
                return LLMResult(success=False, error=f"Unknown provider: {provider.name}")
            
            result.provider = provider.name
            result.model = provider.model
            result.latency_ms = int((time.time() - start) * 1000)
            return result
            
        except Exception as e:
            return LLMResult(
                success=False,
                error=str(e),
                provider=provider.name,
                model=provider.model,
                latency_ms=int((time.time() - start) * 1000),
            )

    async def _call_opencode_zen(
        self, 
        provider: LLMProvider, 
        prompt: str, 
        schema: Type[T]
    ) -> LLMResult:
        """Call Opencode Zen API."""
        # Opencode Zen uses OpenAI-compatible API
        payload = {
            "model": provider.model,
            "messages": [
                {"role": "system", "content": "You are Nabu, airdrop intelligence oracle. Output valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "max_tokens": 4000,
        }
        
        response = await self.client.post(
            f"{provider.base_url or 'https://api.opencode.ai'}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {provider.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.timeout,
        )
        
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        
        return self._parse_structured(content, schema, provider)

    async def _call_deepseek(
        self,
        provider: LLMProvider,
        prompt: str,
        schema: Type[T]
    ) -> LLMResult:
        payload = {
            "model": provider.model,
            "messages": [
                {"role": "system", "content": "Output valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 4000,
        }
        
        response = await self.client.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {provider.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.timeout,
        )
        
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        
        return self._parse_structured(content, schema, provider)

    async def _call_openrouter(
        self,
        provider: LLMProvider,
        prompt: str,
        schema: Type[T]
    ) -> LLMResult:
        payload = {
            "model": provider.model,
            "messages": [
                {"role": "system", "content": "Output valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 4000,
        }
        
        response = await self.client.post(
            f"{provider.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {provider.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://nabu.intelligence",
                "X-Title": "Nabu Intelligence",
            },
            json=payload,
            timeout=self.timeout,
        )
        
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        
        return self._parse_structured(content, schema, provider)

    def _parse_structured(
        self, 
        content: str, 
        schema: Type[T], 
        provider: LLMProvider
    ) -> LLMResult:
        """Parse LLM response into structured schema with confidence estimation."""
        try:
            # Clean content (remove markdown fences if present)
            cleaned = content.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            # Parse JSON
            raw_data = json.loads(cleaned)
            
            # Validate against schema
            validated = schema.model_validate(raw_data)
            
            # Estimate confidence from response characteristics
            confidence = self._estimate_confidence(content, validated)
            
            return LLMResult(
                success=True,
                data=validated,
                confidence=confidence,
                raw_response=content,
            )
            
        except Exception as e:
            return LLMResult(
                success=False,
                error=f"Parse/validate failed: {e}",
                raw_response=content,
            )

    def _estimate_confidence(self, raw_response: str, data: Any) -> float:
        """Heuristic confidence estimation."""
        confidence = 0.5
        
        # Length check — too short = suspicious
        if len(raw_response) > 500:
            confidence += 0.15
        elif len(raw_response) < 100:
            confidence -= 0.2
        
        # Has all required fields
        if hasattr(data, '__fields__'):
            required = [f for f, info in data.__fields__.items() if info.required]
            present = [f for f in required if getattr(data, f, None) is not None]
            confidence += 0.1 * (len(present) / max(len(required), 1))
        
        # Specific fields populated (not null)
        if hasattr(data, 'overall_score') and data.overall_score is not None:
            confidence += 0.1
        if hasattr(data, 'requirements') and data.requirements:
            confidence += 0.1
        if hasattr(data, 'explanation') and data.explanation:
            confidence += 0.1
        
        return max(0.0, min(1.0, confidence))

    def _ensemble(self, results: list[LLMResult], schema: Type[T]) -> "LLMAnalysisResult[T]":
        """Average successful results."""
        if not results:
            return LLMAnalysisResult(success=False, error="No results to ensemble")
        
        # For now, return highest confidence
        best = max(results, key=lambda r: r.confidence)
        return LLMAnalysisResult(
            success=True,
            data=best.data,
            confidence=best.confidence * 0.9,  # slight penalty for ensemble
            provider=f"ensemble({len(results)})",
            model=best.model,
        )

    async def close(self):
        await self.client.aclose()


@dataclass
class LLMAnalysisResult:
    success: bool
    data: Optional[T] = None
    confidence: float = 0.0
    provider: str = ""
    model: str = ""
    latency_ms: int = 0
    error: Optional[str] = None