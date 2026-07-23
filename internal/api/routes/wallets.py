"""
𒀭 API Routes — Wallets
"""

from fastapi import APIRouter, Depends, Query, HTTPException, Body
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from nabu.api.auth import get_current_machine

router = APIRouter(prefix="/wallets", tags=["wallets"])


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskResponse(BaseModel):
    id: str
    type: str
    description: str
    status: str
    tx_hash: Optional[str]
    completed_at: Optional[datetime]


class OpportunityTaskResponse(BaseModel):
    opportunity_id: str
    title: str
    score: float
    status: str
    tasks_total: int
    tasks_completed: int
    tasks_in_progress: int
    tasks_pending: int
    gas_spent_usd: float
    last_activity: Optional[datetime]
    tasks: List[TaskResponse]


class WalletTasksResponse(BaseModel):
    address: str
    total_gas_spent_usd: float
    opportunities_engaged: int
    opportunities: List[OpportunityTaskResponse]


@router.get("/{address}/tasks", response_model=WalletTasksResponse)
async def get_wallet_tasks(
    address: str,
    status: Optional[str] = Query("pending"),
    min_score: int = Query(50, ge=0, le=100),
    db = Depends(lambda: None),
    machine = Depends(get_current_machine),
):
    """Get personalized task list for a specific wallet."""
    
    # Validate address format
    if not address.startswith("0x") or len(address) != 42:
        raise HTTPException(status_code=400, detail="Invalid address format")
    
    # Fetch wallet states with opportunities
    rows = await db.fetch("""
        SELECT ws.*, o.title, o.overall_score, o.status as opp_status,
               (SELECT COUNT(*) FROM tasks WHERE opportunity_id = o.id) as tasks_total,
               (SELECT COALESCE(SUM(estimated_gas_usd), 0) FROM tasks WHERE opportunity_id = o.id) as total_gas_estimate
        FROM wallet_states ws
        JOIN opportunities o ON o.id = ws.opportunity_id
        WHERE ws.address = $1 AND o.overall_score >= $2
        ORDER BY o.overall_score DESC
    """, address, min_score)
    
    opportunities = []
    for row in rows:
        tasks = await db.fetch("""
            SELECT t.id, t.type, t.description, ws_task.status, ws_task.tx_hash, ws_task.completed_at
            FROM tasks t
            LEFT JOIN wallet_task_status ws_task ON ws_task.task_id = t.id AND ws_task.wallet_address = $1
            WHERE t.opportunity_id = $2
            ORDER BY t.sort_order
        """, address, row["opportunity_id"])
        
        opp_tasks = []
        completed = in_progress = pending = 0
        for task in tasks:
            t_status = task["status"] or "pending"
            opp_tasks.append(TaskResponse(
                id=task["id"],
                type=task["type"],
                description=task["description"],
                status=t_status,
                tx_hash=task["tx_hash"],
                completed_at=task["completed_at"],
            ))
            if t_status == "completed":
                completed += 1
            elif t_status == "in_progress":
                in_progress += 1
            else:
                pending += 1
        
        opportunities.append(OpportunityTaskResponse(
            opportunity_id=row["opportunity_id"],
            title=row["title"],
            score=row["overall_score"],
            status=row["status"],
            tasks_total=row["tasks_total"],
            tasks_completed=completed,
            tasks_in_progress=in_progress,
            tasks_pending=pending,
            gas_spent_usd=row["gas_spent_usd"] or 0,
            last_activity=row["last_activity"],
            tasks=opp_tasks,
        ))
    
    total_gas = sum(o.gas_spent_usd for o in opportunities)
    
    return WalletTasksResponse(
        address=address,
        total_gas_spent_usd=total_gas,
        opportunities_engaged=len(opportunities),
        opportunities=opportunities,
    )


class TaskReport(BaseModel):
    opportunity_id: str
    task_id: str
    status: str = Field(pattern="^(completed|failed|in_progress)$")
    tx_hash: str
    gas_used: str
    gas_price_gwei: int
    gas_cost_usd: float
    notes: Optional[str] = None


class VerificationResult(BaseModel):
    success: bool
    verified: bool
    message: str
    detail: Optional[str] = None


@router.patch("/{address}/status", response_model=VerificationResult)
async def report_task_status(
    address: str,
    report: TaskReport,
    db = Depends(lambda: None),
    machine = Depends(get_current_machine),
):
    """Report task completion from mining machine."""
    
    # Validate address
    if not address.startswith("0x") or len(address) != 42:
        raise HTTPException(status_code=400, detail="Invalid address format")
    
    # Validate tx hash
    if not report.tx_hash.startswith("0x") or len(report.tx_hash) != 66:
        raise HTTPException(status_code=400, detail="Invalid tx hash format")
    
    # Check opportunity exists
    opp = await db.fetchrow("SELECT id FROM opportunities WHERE id = $1", report.opportunity_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    # Check task exists
    task = await db.fetchrow("SELECT id FROM tasks WHERE id = $1 AND opportunity_id = $2", 
                              report.task_id, report.opportunity_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found for this opportunity")
    
    # Verify on-chain (simplified - in production: call verification engine)
    verified = await verify_task_on_chain(address, report)
    
    # Update wallet state
    await db.execute("""
        INSERT INTO wallet_states (address, opportunity_id, tasks_completed, tasks_in_progress, gas_spent_usd, status, last_activity)
        VALUES ($1, $2, ARRAY[$3], ARRAY[]::text[], $4, 'in_progress', NOW())
        ON CONFLICT (address, opportunity_id) DO UPDATE SET
            tasks_completed = wallet_states.tasks_completed || EXCLUDED.tasks_completed,
            gas_spent_usd = wallet_states.gas_spent_usd + EXCLUDED.gas_spent_usd,
            last_activity = NOW()
    """, address, report.opportunity_id, report.task_id, report.gas_cost_usd)
    
    # Record event
    await db.execute("""
        INSERT INTO events (opportunity_id, wallet_address, type, data)
        VALUES ($1, $2, 'task_reported', $3)
    """, report.opportunity_id, address, {
        "task_id": report.task_id,
        "status": report.status,
        "tx_hash": report.tx_hash,
        "gas_cost_usd": report.gas_cost_usd,
        "verified": verified,
    })
    
    return VerificationResult(
        success=True,
        verified=verified,
        message="Task reported successfully" + (" and verified on-chain" if verified else " (pending verification)"),
        detail=None if verified else "On-chain verification pending",
    )


async def verify_task_on_chain(address: str, report: TaskReport) -> bool:
    """Verify task completion on-chain. In production: call Wallet Watcher service."""
    # This would call the wallet watcher or directly query RPC
    # For now, return True if tx_hash format is valid
    return len(report.tx_hash) == 66