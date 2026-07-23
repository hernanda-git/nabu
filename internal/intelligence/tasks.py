"""
𒀭 Task Extraction + Orchestration + Gas Optimization
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

from pydantic import BaseModel, Field

from nabu.intelligence.schemas import AnalysisResult, Requirement


class TaskType(str, Enum):
    BRIDGE = "bridge"
    SWAP = "swap"
    LP = "lp"
    STAKE = "stake"
    MINT_NFT = "mint_nft"
    DEPLOY = "deploy"
    VOTE = "vote"
    SOCIAL = "social"
    REFERRAL = "referral"
    TESTNET = "testnet"
    OTHER = "other"


@dataclass
class ChainConfig:
    name: str
    chain_id: int
    rpc_url: str
    explorer_url: str
    native_currency: str
    bridge_contracts: dict[str, str]  # bridge_name -> address
    dex_routers: dict[str, str]       # dex_name -> router_address
    multicall_address: str
    gas_estimator: str = "rpc"  # rpc, api, local


# ─── Chain Registry ───

CHAIN_REGISTRY = {
    "ethereum": ChainConfig(
        name="ethereum", chain_id=1,
        rpc_url="https://eth-mainnet.g.alchemy.com/v2/{key}",
        explorer_url="https://etherscan.io",
        native_currency="ETH",
        bridge_contracts={
            "layerzero": "0x...",
            "ccip": "0x...",
            "across": "0x...",
            "hop": "0x...",
        },
        dex_routers={
            "uniswap_v3": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
            "1inch": "0x1111111254EEB25477B68fb85Ed929f73A960582",
        },
        multicall_address="0xcA11bde05977b3631167028862bE2a173976CA11",
    ),
    "arbitrum": ChainConfig(
        name="arbitrum", chain_id=42161,
        rpc_url="https://arb-mainnet.g.alchemy.com/v2/{key}",
        explorer_url="https://arbiscan.io",
        native_currency="ETH",
        bridge_contracts={
            "layerzero": "0x...",
            "across": "0x...",
            "hop": "0x...",
        },
        dex_routers={
            "uniswap_v3": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
            "1inch": "0x1111111254EEB25477B68fb85Ed929f73A960582",
        },
        multicall_address="0xcA11bde05977b3631167028862bE2a173976CA11",
    ),
    "optimism": ChainConfig(
        name="optimism", chain_id=10,
        rpc_url="https://opt-mainnet.g.alchemy.com/v2/{key}",
        explorer_url="https://optimistic.etherscan.io",
        native_currency="ETH",
        bridge_contracts={
            "layerzero": "0x...",
            "across": "0x...",
        },
        dex_routers={
            "uniswap_v3": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
        },
        multicall_address="0xcA11bde05977b3631167028862bE2a173976CA11",
    ),
    "base": ChainConfig(
        name="base", chain_id=8453,
        rpc_url="https://base-mainnet.g.alchemy.com/v2/{key}",
        explorer_url="https://basescan.org",
        native_currency="ETH",
        bridge_contracts={
            "base_bridge": "0x...",
            "across": "0x...",
        },
        dex_routers={
            "uniswap_v3": "0x...",
            "aerodrome": "0x...",
        },
        multicall_address="0xcA11bde05977b3631167028862bE2a173976CA11",
    ),
    "solana": ChainConfig(
        name="solana", chain_id=0,
        rpc_url="https://api.mainnet-beta.solana.com",
        explorer_url="https://solscan.io",
        native_currency="SOL",
        bridge_contracts={
            "wormhole": "0x...",
        },
        dex_routers={
            "jupiter": "0x...",
        },
        multicall_address="",
    ),
}


# ─── Task Extraction ───

class TaskExtractor:
    """Converts LLM requirements into structured, chain-specific tasks."""

    def __init__(self):
        self.task_templates = {
            TaskType.BRIDGE: BridgeTask,
            TaskType.SWAP: SwapTask,
            TaskType.LP: LPTask,
            TaskType.STAKE: StakeTask,
            TaskType.MINT_NFT: MintNFTTask,
            TaskType.DEPLOY: DeployContractTask,
            TaskType.VOTE: VoteTask,
            TaskType.SOCIAL: SocialTask,
            TaskType.TESTNET: TestnetTask,
        }

    def extract(self, analysis: AnalysisResult) -> list["StructuredTask"]:
        tasks = []
        for i, req in enumerate(analysis.requirements):
            template = self.task_templates.get(TaskType(req.type))
            if not template:
                continue
            
            chain_config = CHAIN_REGISTRY.get(req.chain)
            if not chain_config:
                continue
            
            task = template(
                id=f"{analysis.opportunity_id}_task_{i}",
                description=req.description,
                chain=req.chain,
                chain_config=chain_config,
                optional=req.optional,
                gas_estimate=req.estimated_gas_usd,
                parameters=req.parameters,
                sort_order=i,
            )
            tasks.append(task)
        return tasks


# ─── Structured Tasks ───

@dataclass
class StructuredTask:
    id: str
    description: str
    chain: str
    chain_config: ChainConfig
    optional: bool = False
    gas_estimate: Optional[float] = None
    parameters: dict = field(default_factory=dict)
    sort_order: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.__class__.__name__.replace("Task", "").lower(),
            "description": self.description,
            "chain": self.chain,
            "optional": self.optional,
            "estimated_gas_usd": self.gas_estimate,
            "parameters": self.parameters,
            "sort_order": self.sort_order,
        }


class BridgeTask(StructuredTask):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.source_chain = kwargs.get("parameters", {}).get("source_chain", self.chain)
        self.target_chain = kwargs.get("parameters", {}).get("target_chain", self.chain)
        self.min_amount = kwargs.get("parameters", {}).get("min_amount")
        self.bridge = kwargs.get("parameters", {}).get("bridge", "across")


class SwapTask(StructuredTask):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.token_in = kwargs.get("parameters", {}).get("token_in")
        self.token_out = kwargs.get("parameters", {}).get("token_out")
        self.min_amount = kwargs.get("parameters", {}).get("min_amount")
        self.dex = kwargs.get("parameters", {}).get("dex", "1inch")


class LPTask(StructuredTask):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.token_a = kwargs.get("parameters", {}).get("token_a")
        self.token_b = kwargs.get("parameters", {}).get("token_b")
        self.dex = kwargs.get("parameters", {}).get("dex", "uniswap_v3")


class StakeTask(StructuredTask):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.token = kwargs.get("parameters", {}).get("token")
        self.validator = kwargs.get("parameters", {}).get("validator")


class MintNFTTask(StructuredTask):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.contract = kwargs.get("parameters", {}).get("contract")
        self.quantity = kwargs.get("parameters", {}).get("quantity", 1)


class DeployContractTask(StructuredTask):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bytecode = kwargs.get("parameters", {}).get("bytecode")
        self.constructor_args = kwargs.get("parameters", {}).get("constructor_args", [])


class VoteTask(StructuredTask):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.proposal_id = kwargs.get("parameters", {}).get("proposal_id")
        self.choice = kwargs.get("parameters", {}).get("choice")


class SocialTask(StructuredTask):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.platform = kwargs.get("parameters", {}).get("platform")
        self.action = kwargs.get("parameters", {}).get("action")


class TestnetTask(StructuredTask):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.testnet = kwargs.get("parameters", {}).get("testnet")
        self.actions = kwargs.get("parameters", {}).get("actions", [])


# ─── Task Orchestrator — Cross-Opportunity Gas Optimization ───

@dataclass
class PlanStep:
    action: str                          # e.g., "bridge:ethereum->arbitrum:0.5ETH"
    route: str                           # e.g., "across"
    params: dict
    satisfies: list[str]                 # opportunity IDs this step satisfies
    reuse_count: int
    estimated_gas_usd: float
    estimated_time_sec: int


@dataclass
class ExecutionPlan:
    wallet: str
    naive_gas_usd: float
    optimized_gas_usd: float
    savings_pct: float
    steps: list[PlanStep]
    total_time_sec: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class TaskOrchestrator:
    """
    Given a wallet's active opportunities, produces an optimal execution plan
    that minimizes gas by de-duplicating shared tasks.
    """

    def __init__(self, gas_router: "GasRouter"):
        self.gas_router = gas_router

    def plan(self, wallet: str, opportunities: list[AnalysisResult]) -> ExecutionPlan:
        # Collect all pending tasks across opportunities
        flat_tasks = []
        for opp in opportunities:
            for task in opp.tasks:
                if not self.is_completed(wallet, task.id):
                    flat_tasks.append((opp.id, task))

        # Group by (chain, type, normalized_params)
        groups = {}
        for opp_id, task in flat_tasks:
            key = self.task_key(task)
            if key not in groups:
                groups[key] = []
            groups[key].append((opp_id, task))

        # For each group, pick cheapest route
        plan_steps = []
        for key, members in groups.items():
            chain, task_type, norm_params = key
            chain_config = CHAIN_REGISTRY.get(members[0][1].chain)
            if not chain_config:
                continue

            # Get cheapest route for this task type
            route, gas_usd = self.gas_router.get_cheapest_route(
                task_type, members[0][1].chain, norm_params
            )

            plan_steps.append(PlanStep(
                action=f"{task_type}:{chain}:{self.describe_params(norm_params)}",
                route=route,
                params=norm_params,
                satisfies=[m[0] for m in members],
                reuse_count=len(members),
                estimated_gas_usd=gas_usd,
                estimated_time_sec=self.estimate_time(task_type),
            ))

        # Sort by chain, then by type priority
        plan_steps.sort(key=lambda s: (s.params.get("chain", ""), s.action))

        naive_gas = sum(t.gas_estimate or 0 for _, t in flat_tasks)
        optimized_gas = sum(s.estimated_gas_usd for s in plan_steps)
        savings = round(100 * (naive_gas - optimized_gas) / max(naive_gas, 1), 1)

        return ExecutionPlan(
            wallet=wallet,
            naive_gas_usd=naive_gas,
            optimized_gas_usd=optimized_gas,
            savings_pct=savings,
            steps=plan_steps,
            total_time_sec=sum(s.estimated_time_sec for s in plan_steps),
        )

    def task_key(self, task: StructuredTask) -> tuple:
        """Normalize task params for grouping."""
        params = task.parameters.copy()
        # Remove wallet-specific amounts, keep minimums
        normalized = {
            "type": task.__class__.__name__,
            "chain": task.chain,
        }
        for k, v in params.items():
            if k in ("min_amount", "quantity"):
                normalized[k] = v
        return (task.chain, task.__class__.__name__.replace("Task", "").lower(), 
                json.dumps(normalized, sort_keys=True))

    def describe_params(self, params: dict) -> str:
        parts = []
        for k, v in params.items():
            if k not in ("type", "chain"):
                parts.append(f"{k}={v}")
        return ",".join(parts) if parts else "default"

    def estimate_time(self, task_type: str) -> int:
        times = {
            "bridge": 300,  # 5 min
            "swap": 60,     # 1 min
            "lp": 120,      # 2 min
            "stake": 60,
            "mint_nft": 30,
            "deploy": 180,
            "vote": 30,
        }
        return times.get(task_type.lower(), 60)

    def is_completed(self, wallet: str, task_id: str) -> bool:
        # Query DB
        return False

    def get_cheapest_route(self, task_type: str, chain: str, params: dict) -> tuple[str, float]:
        return self.gas_router.get_cheapest_route(task_type, chain, params)


# ─── Gas Router — Cheapest Path Selection ───

class GasRouter:
    """
    Maintains gas cost matrix per (task_type, chain, route).
    Queries aggregator APIs, caches in Redis.
    """

    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.cache_ttl = 300  # 5 min

    async def get_cheapest_route(self, task_type: str, chain: str, params: dict) -> tuple[str, float]:
        cache_key = f"gas:{task_type}:{chain}:{json.dumps(params, sort_keys=True)}"
        
        if self.redis:
            cached = await self.redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                return data["route"], data["cost_usd"]

        # Query providers
        routes = await self.query_providers(task_type, chain, params)
        if not routes:
            return "default", 0.0

        best = min(routes, key=lambda r: r["cost_usd"])
        
        if self.redis:
            await self.redis.setex(cache_key, self.cache_ttl, json.dumps(best))

        return best["route"], best["cost_usd"]

    async def query_providers(self, task_type: str, chain: str, params: dict) -> list[dict]:
        routes = []

        if task_type == "bridge":
            routes.extend(await self.query_bridge_apis(chain, params))
        elif task_type == "swap":
            routes.extend(await self.query_dex_apis(chain, params))
        elif task_type == "lp":
            routes.extend(await self.query_lp_apis(chain, params))

        return routes

    async def query_bridge_apis(self, chain: str, params: dict) -> list[dict]:
        # Query Across, Hop, Synapse, LayerZero, etc.
        return []

    async def query_dex_apis(self, chain: str, params: dict) -> list[dict]:
        # Query 1inch, Paraswap, 0x, Uniswap quoter
        return []

    async def query_lp_apis(self, chain: str, params: dict) -> list[dict]:
        # Query DEX router estimateGas
        return []