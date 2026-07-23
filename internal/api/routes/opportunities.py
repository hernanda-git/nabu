"""
𒀭 API Routes — Opportunities
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

from nabu.api.auth import get_current_machine

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


class OpportunityStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"
    SCAM = "scam"
    ALL = "all"


class Verdict(str, Enum):
    WORTHWHILE = "worthwhile"
    SPECULATIVE = "speculative"
    RISKY = "risky"
    SKIP = "skip"
    SCAM = "scam"


class SortBy(str, Enum):
    OVERALL_SCORE = "overall_score"
    DETECTED_AT = "detected_at"
    ESTIMATED_VALUE = "estimated_value"
    CLAIM_START = "claim_start"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class OpportunityResponse(BaseModel):
    id: str
    slug: str
    title: str
    protocol_name: str
    category: str
    status: str
    overall_score: float
    difficulty_score: float
    estimated_value_usd_min: Optional[float]
    estimated_value_usd_max: Optional[float]
    confidence: str
    verdict: str
    networks: List[str]
    risk_level: str
    detected_at: datetime
    claim_start: Optional[datetime]
    claim_end: Optional[datetime]
    tge_date: Optional[datetime]
    task_count: int
    total_gas_estimate_usd: float
    sources: List[dict]


class PaginatedResponse(BaseModel):
    data: List[OpportunityResponse]
    pagination: dict


@router.get("", response_model=PaginatedResponse)
async def list_opportunities(
    status: OpportunityStatus = Query(OpportunityStatus.ACTIVE),
    min_score: float = Query(0, ge=0, le=100),
    max_difficulty: float = Query(10, ge=1, le=10),
    network: Optional[str] = None,
    category: Optional[str] = None,
    verdict: Optional[Verdict] = None,
    search: Optional[str] = None,
    sort_by: SortBy = Query(SortBy.OVERALL_SCORE),
    sort_order: SortOrder = Query(SortOrder.DESC),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db = Depends(lambda: None),  # Inject from app.state
    machine = Depends(get_current_machine),
):
    """List all active airdrop opportunities with filtering."""
    
    # Build query
    where_clauses = []
    params = []
    param_idx = 1
    
    if status != OpportunityStatus.ALL:
        where_clauses.append(f"status = ${param_idx}")
        params.append(status.value)
        param_idx += 1
    
    if min_score > 0:
        where_clauses.append(f"overall_score >= ${param_idx}")
        params.append(min_score)
        param_idx += 1
    
    if max_difficulty < 10:
        where_clauses.append(f"difficulty_score <= ${param_idx}")
        params.append(max_difficulty)
        param_idx += 1
    
    if network:
        where_clauses.append(f"${param_idx} = ANY(networks)")
        params.append(network)
        param_idx += 1
    
    if category:
        where_clauses.append(f"category = ${param_idx}")
        params.append(category)
        param_idx += 1
    
    if verdict:
        where_clauses.append(f"verdict = ${param_idx}")
        params.append(verdict.value)
        param_idx += 1
    
    if search:
        where_clauses.append(f"(title ILIKE ${param_idx} OR description ILIKE ${param_idx})")
        params.append(f"%{search}%")
        param_idx += 1
    
    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    
    # Count total
    count_sql = f"SELECT COUNT(*) FROM opportunities {where_sql}"
    total = await db.fetchval(count_sql, *params)
    
    # Fetch data
    order_col = sort_by.value
    order_dir = sort_order.value.upper()
    data_sql = f"""
        SELECT id, slug, title, protocol_name, category, status,
               overall_score, difficulty_score, estimated_value_usd_min,
               estimated_value_usd_max, confidence, verdict, networks,
               risk_level, detected_at, claim_start, claim_end, tge_date,
               (SELECT COUNT(*) FROM tasks WHERE opportunity_id = o.id) as task_count,
               (SELECT COALESCE(SUM(estimated_gas_usd), 0) FROM tasks WHERE opportunity_id = o.id) as total_gas_estimate_usd,
               sources
        FROM opportunities o
        {where_sql}
        ORDER BY {order_col} {order_dir}
        LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """
    params.extend([limit, offset])
    
    rows = await db.fetch(data_sql, *params)
    
    return PaginatedResponse(
        data=[OpportunityResponse(**dict(row)) for row in rows],
        pagination={
            "total": total,
            "limit": limit,
            "offset": offset,
            "next_offset": offset + limit if offset + limit < total else None,
        }
    )


@router.get("/{opportunity_id}")
async def get_opportunity(
    opportunity_id: str,
    db = Depends(lambda: None),
    machine = Depends(get_current_machine),
):
    """Get full opportunity detail with tasks."""
    
    # Fetch opportunity
    opp = await db.fetchrow("""
        SELECT o.*, p.*, 
               (SELECT COUNT(*) FROM tasks WHERE opportunity_id = o.id) as task_count
        FROM opportunities o
        LEFT JOIN protocol_info p ON p.opportunity_id = o.id
        WHERE o.id = $1
    """, opportunity_id)
    
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    # Fetch tasks
    tasks = await db.fetch("""
        SELECT id, type, description, parameters, is_optional,
               estimated_gas_usd, estimated_time_minutes, difficulty, sort_order
        FROM tasks
        WHERE opportunity_id = $1
        ORDER BY sort_order
    """, opportunity_id)
    
    return {
        "data": {
            **dict(opp),
            "tasks": [dict(t) for t in tasks],
        }
    }


@router.get("/{opportunity_id}/tasks")
async def get_opportunity_tasks(
    opportunity_id: str,
    db = Depends(lambda: None),
    machine = Depends(get_current_machine),
):
    """Get machine-actionable tasks for an opportunity."""
    
    tasks = await db.fetch("""
        SELECT id, type, description, parameters, is_optional,
               estimated_gas_usd, estimated_time_minutes, difficulty, sort_order
        FROM tasks
        WHERE opportunity_id = $1
        ORDER BY sort_order
    """, opportunity_id)
    
    return {"data": [dict(t) for t in tasks]}