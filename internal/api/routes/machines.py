"""
𒀭 API Routes — Mining Machines
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from nabu.api.auth import get_current_machine

router = APIRouter(prefix="/machines", tags=["machines"])


class MachineRegistration(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    egress_cidr: List[str] = Field(min_items=1)
    tier: str = Field(pattern="^(mining|mining_high|admin)$")
    metadata: Optional[dict] = None


class MachineResponse(BaseModel):
    id: str
    name: str
    status: str
    egress_cidr: List[str]
    tier: str
    current_task: Optional[str]
    total_gas_usd: float
    success_rate: float
    last_heartbeat: Optional[datetime]
    registered_at: datetime
    metadata: dict


class MachineListResponse(BaseModel):
    data: List[MachineResponse]


@router.get("", response_model=MachineListResponse)
async def list_machines(
    status: Optional[str] = Query(None),
    db = Depends(lambda: None),
    machine = Depends(get_current_machine),
):
    """List all registered mining machines."""
    
    where = ""
    params = []
    if status:
        where = "WHERE status = $1"
        params = [status]
    
    rows = await db.fetch(f"""
        SELECT * FROM mining_machines
        {where}
        ORDER BY last_heartbeat DESC NULLS LAST
    """, *params)
    
    return MachineListResponse(data=[MachineResponse(**dict(r)) for r in rows])


@router.post("", response_model=MachineResponse, status_code=201)
async def register_machine(
    registration: MachineRegistration,
    db = Depends(lambda: None),
    machine = Depends(get_current_machine),
):
    """Register a new mining machine with IP allowlist."""
    
    # Generate machine ID
    import uuid
    machine_id = f"mm_{uuid.uuid4().hex[:12]}"
    
    # Validate CIDR format
    import ipaddress
    for cidr in registration.egress_cidr:
        try:
            ipaddress.ip_network(cidr)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid CIDR: {cidr}")
    
    # Check tier permissions
    if registration.tier == "admin" and machine.get("tier") != "admin":
        raise HTTPException(status_code=403, detail="Cannot register admin tier machine")
    
    row = await db.fetchrow("""
        INSERT INTO mining_machines (id, name, egress_cidr, tier, metadata)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING *
    """, machine_id, registration.name, registration.egress_cidr, registration.tier, 
        registration.metadata or {})
    
    return MachineResponse(**dict(row))


@router.get("/{machine_id}", response_model=MachineResponse)
async def get_machine(
    machine_id: str,
    db = Depends(lambda: None),
    machine = Depends(get_current_machine),
):
    """Get machine details."""
    
    row = await db.fetchrow("SELECT * FROM mining_machines WHERE id = $1", machine_id)
    if not row:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    return MachineResponse(**dict(row))


@router.patch("/{machine_id}/heartbeat")
async def machine_heartbeat(
    machine_id: str,
    current_task: Optional[str] = None,
    db = Depends(lambda: None),
    machine = Depends(get_current_machine),
):
    """Machine heartbeat - update status and current task."""
    
    # Verify machine owns this ID
    if machine["id"] != machine_id:
        raise HTTPException(status_code=403, detail="Cannot heartbeat for another machine")
    
    updates = ["last_heartbeat = NOW()"]
    params = [machine_id]
    param_idx = 2
    
    if current_task:
        updates.append(f"current_task = ${param_idx}")
        params.append(current_task)
        param_idx += 1
    
    await db.execute(f"""
        UPDATE mining_machines 
        SET {", ".join(updates)}
        WHERE id = $1
    """, *params)
    
    return {"success": True, "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/{machine_id}/assignments")
async def get_machine_assignments(
    machine_id: str,
    db = Depends(lambda: None),
    machine = Depends(get_current_machine),
):
    """Get current opportunity assignments for a machine."""
    
    if machine["id"] != machine_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    rows = await db.fetch("""
        SELECT o.id as opportunity_id, o.title, o.overall_score,
               ws.status, ws.tasks_completed, ws.tasks_in_progress,
               ws.gas_spent_usd, ws.last_activity
        FROM wallet_states ws
        JOIN opportunities o ON o.id = ws.opportunity_id
        WHERE ws.assigned_machine = $1
        ORDER BY o.overall_score DESC
    """, machine_id)
    
    return {"data": [dict(r) for r in rows]}