"""Schedule management API."""
from fastapi import APIRouter, HTTPException
from sqlalchemy import text as sa_text
from typing import Any, Dict, List, Optional
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/schedules", tags=["定时任务"])


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
        schedule_id = r.lastrowid
        
        return {"id": schedule_id, "message": "Schedule created"}
    except Exception as e:
        logger.error(f"Failed to create schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{schedule_id}")
async def update_schedule(schedule_id: int, data: Dict[str, Any], session=Depends(get_db)):
    """Update a schedule."""
    try:
        r = await session.execute(sa_text("SELECT id FROM schedules WHERE id = :id"), {"id": schedule_id})
        if not r.fetchone():
            raise HTTPException(status_code=404, detail="Schedule not found")
        
        await session.execute(sa_text("""
            UPDATE schedules 
            SET name=:name, entry_type=:entry_type, cron=:cron, params=:params, enabled=:enabled
            WHERE id = :id
        """), {
            "id": schedule_id,
            "name": data.get("name", ""),
            "entry_type": data.get("entry_type", "generate_cases"),
            "cron": data.get("cron", "0 */6 * * *"),
            "params": json.dumps(data.get("params", {}), ensure_ascii=False),
            "enabled": data.get("enabled", True)
        })
        await session.commit()
        
        return {"message": "Schedule updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: int, session=Depends(get_db)):
    """Delete a schedule."""
    try:
        r = await session.execute(sa_text("SELECT id FROM schedules WHERE id = :id"), {"id": schedule_id})
        if not r.fetchone():
            raise HTTPException(status_code=404, detail="Schedule not found")
        
        await session.execute(sa_text("DELETE FROM schedules WHERE id = :id"), {"id": schedule_id})
        await session.commit()
        
        return {"message": "Schedule deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{schedule_id}/toggle")
async def toggle_schedule(schedule_id: int, session=Depends(get_db)):
    """Toggle schedule enabled status."""
    try:
        r = await session.execute(sa_text("SELECT enabled FROM schedules WHERE id = :id"), {"id": schedule_id})
        row = r.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Schedule not found")
        
        new_status = not bool(row[0])
        await session.execute(sa_text("UPDATE schedules SET enabled = :status WHERE id = :id"), 
                            {"status": new_status, "id": schedule_id})
        await session.commit()
        
        return {"enabled": new_status}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to toggle schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))
