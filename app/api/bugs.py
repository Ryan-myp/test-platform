"""Bugs API."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text as sa_text
from typing import Any, Dict, List, Optional
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bugs", tags=["缺陷管理"])


async def get_db():
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/stats")
async def bug_stats(session=Depends(get_db)) -> Dict[str, Any]:
    """Get bug statistics."""
    try:
        r = await session.execute(sa_text("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status='open' THEN 1 ELSE 0 END) as open,
                SUM(CASE WHEN status='fixed' THEN 1 ELSE 0 END) as fixed,
                SUM(CASE WHEN status='closed' THEN 1 ELSE 0 END) as closed,
                SUM(CASE WHEN severity='critical' THEN 1 ELSE 0 END) as critical,
                SUM(CASE WHEN severity='major' THEN 1 ELSE 0 END) as major
            FROM bugs
        """))
        row = r.fetchone()
        total = row[0] or 0
        resolved = (row[1] or 0) + (row[2] or 0) + (row[3] or 0)
        rate = f"{(resolved / total * 100):.1f}%" if total > 0 else "0%"
        
        return {
            "total": total,
            "open": row[1] or 0,
            "fixed": row[2] or 0,
            "closed": row[3] or 0,
            "critical": row[4] or 0,
            "major": row[5] or 0,
            "resolution_rate": rate
        }
    except Exception as e:
        logger.error(f"Failed to get bug stats: {e}")
        return {"total": 0, "open": 0, "fixed": 0, "closed": 0, "critical": 0, "major": 0, "resolution_rate": "0%"}


@router.get("")
async def list_bugs(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    session=Depends(get_db)
) -> Dict[str, Any]:
    """List bugs."""
    conditions = []
    params = {}
    
    if status:
        conditions.append("status = :status")
        params["status"] = status
    if severity:
        conditions.append("severity = :severity")
        params["severity"] = severity
    if search:
        conditions.append("(title LIKE :search OR description LIKE :search)")
        params["search"] = f"%{search}%"
    
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    count_sql = f"SELECT COUNT(*) FROM bugs {where}"
    r = await session.execute(sa_text(count_sql), params)
    total = r.scalar() or 0
    
    sql = f"""SELECT id, title, description, severity, status, module, priority,
              reporter, assignee, steps, expected, actual, screenshots,
              related_cases, resolution, created_at, updated_at
              FROM bugs {where} 
              ORDER BY id DESC LIMIT :limit OFFSET :offset"""
    params["limit"] = page_size
    params["offset"] = (page - 1) * page_size
    
    r = await session.execute(sa_text(sql), params)
    rows = r.fetchall()
    
    bugs = []
    for row in rows:
        bugs.append({
            "id": row[0],
            "title": row[1],
            "description": row[2] or "",
            "severity": row[3] or "medium",
            "status": row[4] or "open",
            "module": row[5] or "",
            "priority": row[6] or "P2",
            "reporter": row[7] or "",
            "assignee": row[8] or "",
            "steps": row[9] or "",
            "expected": row[10] or "",
            "actual": row[11] or "",
            "screenshots": json.loads(row[12] or "[]"),
            "related_cases": json.loads(row[13] or "[]"),
            "resolution": row[14] or "",
            "created_at": row[15],
            "updated_at": row[16]
        })
    
    return {
        "items": bugs,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.post("")
async def create_bug(data: Dict[str, Any], session=Depends(get_db)):
    """Create a new bug."""
    sql = """INSERT INTO bugs 
             (title, description, severity, status, module, priority,
              reporter, assignee, steps, expected, actual, screenshots, related_cases, resolution)
             VALUES (:title, :description, :severity, :status, :module, :priority,
                     :reporter, :assignee, :steps, :expected, :actual, :screenshots, :related_cases, :resolution)"""
    
    params = {
        "title": data.get("title", ""),
        "description": data.get("description", ""),
        "severity": data.get("severity", "medium"),
        "status": data.get("status", "open"),
        "module": data.get("module", ""),
        "priority": data.get("priority", "P2"),
        "reporter": data.get("reporter", ""),
        "assignee": data.get("assignee", ""),
        "steps": data.get("steps", ""),
        "expected": data.get("expected", ""),
        "actual": data.get("actual", ""),
        "screenshots": json.dumps(data.get("screenshots", []), ensure_ascii=False),
        "related_cases": json.dumps(data.get("related_cases", []), ensure_ascii=False),
        "resolution": data.get("resolution", "")
    }
    
    await session.execute(sa_text(sql), params)
    await session.commit()
    
    r = await session.execute(sa_text("SELECT last_insert_rowid()"))
    bug_id = r.scalar()
    
    return {"id": bug_id, "message": "Bug created"}


@router.put("/{bug_id}")
async def update_bug(bug_id: int, data: Dict[str, Any], session=Depends(get_db)):
    """Update a bug."""
    r = await session.execute(sa_text("SELECT id FROM bugs WHERE id = :id"), {"id": bug_id})
    if not r.fetchone():
        raise HTTPException(status_code=404, detail="Bug not found")
    
    sql = """UPDATE bugs SET
             title = :title, description = :description, severity = :severity,
             status = :status, module = :module, priority = :priority,
             reporter = :reporter, assignee = :assignee,
             steps = :steps, expected = :expected, actual = :actual,
             screenshots = :screenshots, related_cases = :related_cases,
             resolution = :resolution, updated_at = CURRENT_TIMESTAMP
             WHERE id = :id"""
    
    params = {
        "id": bug_id,
        "title": data.get("title"),
        "description": data.get("description"),
        "severity": data.get("severity"),
        "status": data.get("status"),
        "module": data.get("module"),
        "priority": data.get("priority"),
        "reporter": data.get("reporter"),
        "assignee": data.get("assignee"),
        "steps": data.get("steps"),
        "expected": data.get("expected"),
        "actual": data.get("actual"),
        "screenshots": json.dumps(data.get("screenshots", []), ensure_ascii=False),
        "related_cases": json.dumps(data.get("related_cases", []), ensure_ascii=False),
        "resolution": data.get("resolution")
    }
    
    await session.execute(sa_text(sql), params)
    await session.commit()
    
    return {"message": "Bug updated"}


@router.delete("/{bug_id}")
async def delete_bug(bug_id: int, session=Depends(get_db)):
    """Delete a bug."""
    r = await session.execute(sa_text("SELECT id FROM bugs WHERE id = :id"), {"id": bug_id})
    if not r.fetchone():
        raise HTTPException(status_code=404, detail="Bug not found")
    
    await session.execute(sa_text("DELETE FROM bugs WHERE id = :id"), {"id": bug_id})
    await session.commit()
    
    return {"message": "Bug deleted"}
