"""
𒀭 API Routes — Events & Real-time
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone

router = APIRouter(prefix="/events", tags=["events"])


class EventResponse(BaseModel):
    id: str
    type: str
    opportunity_id: Optional[str]
    wallet_address: Optional[str]
    data: dict
    occurred_at: datetime


class EventsListResponse(BaseModel):
    data: List[EventResponse]


@router.get("", response_model=EventsListResponse)
async def list_events(
    since: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    type: Optional[str] = Query(None),
    db = Depends(lambda: None),
):
    """List recent events."""
    
    where = []
    params = []
    param_idx = 1
    
    if since:
        where.append(f"occurred_at >= ${param_idx}")
        params.append(since)
        param_idx += 1
    
    if type:
        where.append(f"type = ${param_idx}")
        params.append(type)
        param_idx += 1
    
    where_clause = "WHERE " + " AND ".join(where) if where else ""
    
    params.append(limit)
    query = f"""
        SELECT * FROM events
        {where_clause}
        ORDER BY occurred_at DESC
        LIMIT ${param_idx}
    """
    
    rows = await db.fetch(query, *params)
    return EventsListResponse(data=[EventResponse(**dict(r)) for r in rows])


@router.get("/stream")
async def stream_events(
    since: Optional[datetime] = Query(None),
    types: Optional[str] = Query(None),
    db = Depends(lambda: None),
):
    """Server-Sent Events stream for real-time updates."""
    
    async def event_generator():
        last_id = 0
        type_filter = types.split(",") if types else None
        
        if since:
            row = await db.fetchrow("SELECT id FROM events WHERE occurred_at >= $1 ORDER BY id LIMIT 1", since)
            if row:
                last_id = row["id"]
        
        while True:
            query = """
                SELECT * FROM events 
                WHERE id > $1
                AND ($2 IS NULL OR type = ANY($3))
                ORDER BY id ASC
                LIMIT 50
            """
            rows = await db.fetch(query, last_id, types, type_filter)
            
            for row in rows:
                last_id = row["id"]
                event_type = row["type"]
                
                yield f"event: {event_type}\n"
                yield f"data: {row.to_json()}\n\n"
            
            # Wait for new events (long poll)
            await asyncio.sleep(2)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )