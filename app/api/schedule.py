"""Schedule management API."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text as sa_text
from typing import Any, Dict, List, Optional
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/schedules", tags=["定时任务"])


async def get_db():
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session



async def get_db():
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session


@router.get("")
async def list_schedules(session=Depends(get_db)) -> Dict[str, Any]:
    """List all scheduled tasks."""
    try:
        r = await session.execute(sa_text("SELECT * FROM schedules ORDER BY id DESC"))
        rows = r.fetchall()
        
        schedules = []
        for row in rows:
            schedules.append({
                "id": row[0],
                "name": row[1] or "",
                "entry_type": row[2] or "",
                "cron": row[3] or "",
                "params": json.loads(row[4] or "{}"),
                "enabled": bool(row[5]) if row[5] is not None else True,
                "last_run": row[6],
                "next_run": row[7],
                "created_at": row[8]
            })
        
        return {"items": schedules, "total": len(schedules)}
    except Exception as e:
        logger.error(f"Failed to list schedules: {e}")
        return {"items": [], "total": 0}


@router.post("")
async def create_schedule(data: Dict[str, Any], session=Depends(get_db)):
    """Create a new schedule."""
    try:
        r = await session.execute(sa_text("""
            INSERT INTO schedules (name, entry_type, cron, params, enabled)
            VALUES (:name, :entry_type, :cron, :params, :enabled)
        """), {
            "name": data.get("name", ""),
            "entry_type": data.get("entry_type", "generate_cases"),
            "cron": data.get("cron", "0 */6 * * *"),
            "params": json.dumps(data.get("params", {}), ensure_ascii=False),
            "enabled": data.get("enabled", True)
        })
        await session.commit()
        return {"id": r.lastrowid, "message": "Schedule created"}
    except Exception as e:
        logger.error(f"Failed to create schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))
