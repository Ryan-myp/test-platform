"""Test suites API."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text as sa_text
from typing import Any, Dict, List, Optional
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/suites", tags=["测试套件"])


async def get_db():
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/stats/summary")
async def suite_stats(session=Depends(get_db)) -> Dict[str, Any]:
    """Get suite statistics."""
    try:
        r = await session.execute(sa_text("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status='active' THEN 1 ELSE 0 END) as active,
                (SELECT COUNT(*) FROM test_cases tc WHERE tc.suite_id = ts.id) as total_cases
            FROM test_suites ts
        """))
        row = r.fetchone()
        return {
            "total": row[0] or 0,
            "active": row[1] or 0,
            "total_cases": row[2] or 0,
            "have_run_pct": "0%"
        }
    except Exception as e:
        logger.error(f"Failed to get suite stats: {e}")
        return {"total": 0, "active": 0, "total_cases": 0, "have_run_pct": "0%"}


@router.get("")
async def list_suites(
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    session=Depends(get_db)
) -> Dict[str, Any]:
    """List test suites."""
    conditions = []
    params = {}
    
    if status:
        conditions.append("status = :status")
        params["status"] = status
    if search:
        conditions.append("(name LIKE :search OR description LIKE :search)")
        params["search"] = f"%{search}%"
    
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    count_sql = f"SELECT COUNT(*) FROM test_suites {where}"
    r = await session.execute(sa_text(count_sql), params)
    total = r.scalar() or 0
    
    sql = f"""SELECT id, name, description, module, priority, status, 
              owner, concurrent, config, tags, case_count, created_at, updated_at
              FROM test_suites {where} 
              ORDER BY id DESC LIMIT :limit OFFSET :offset"""
    params["limit"] = page_size
    params["offset"] = (page - 1) * page_size
    
    r = await session.execute(sa_text(sql), params)
    rows = r.fetchall()
    
    suites = []
    for row in rows:
        suites.append({
            "id": row[0],
            "name": row[1],
            "description": row[2] or "",
            "module": row[3] or "",
            "priority": row[4] or "P2",
            "status": row[5] or "active",
            "owner": row[6] or "",
            "concurrent": row[7] or 3,
            "config": json.loads(row[8] or "{}"),
            "tags": json.loads(row[9] or "[]"),
            "case_count": row[10] or 0,
            "created_at": row[11],
            "updated_at": row[12]
        })
    
    return {
        "items": suites,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/{suite_id}")
async def get_suite(suite_id: int, session=Depends(get_db)):
    """Get a specific suite."""
    r = await session.execute(sa_text("SELECT * FROM test_suites WHERE id = :id"), {"id": suite_id})
    row = r.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Suite not found")
    
    return {
        "id": row[0],
        "name": row[1],
        "description": row[2] or "",
        "module": row[3] or "",
        "priority": row[4] or "P2",
        "status": row[5] or "active",
        "owner": row[6] or "",
        "concurrent": row[7] or 3,
        "config": json.loads(row[8] or "{}"),
        "tags": json.loads(row[9] or "[]"),
        "case_count": row[10] or 0,
        "created_at": row[11],
        "updated_at": row[12]
    }


@router.post("")
async def create_suite(data: Dict[str, Any], session=Depends(get_db)):
    """Create a new suite."""
    sql = """INSERT INTO test_suites 
             (name, description, module, priority, status, owner, concurrent, config, tags, case_count)
             VALUES (:name, :description, :module, :priority, :status, :owner, :concurrent, :config, :tags, 0)"""
    
    params = {
        "name": data.get("name", ""),
        "description": data.get("description", ""),
        "module": data.get("module", ""),
        "priority": data.get("priority", "P2"),
        "status": data.get("status", "active"),
        "owner": data.get("owner", ""),
        "concurrent": data.get("concurrent", 3),
        "config": json.dumps(data.get("config", {}), ensure_ascii=False),
        "tags": json.dumps(data.get("tags", []), ensure_ascii=False)
    }
    
    await session.execute(sa_text(sql), params)
    await session.commit()
    
    r = await session.execute(sa_text("SELECT last_insert_rowid()"))
    suite_id = r.scalar()
    
    return {"id": suite_id, "message": "Suite created"}


@router.put("/{suite_id}")
async def update_suite(suite_id: int, data: Dict[str, Any], session=Depends(get_db)):
    """Update a suite."""
    r = await session.execute(sa_text("SELECT id FROM test_suites WHERE id = :id"), {"id": suite_id})
    if not r.fetchone():
        raise HTTPException(status_code=404, detail="Suite not found")
    
    sql = """UPDATE test_suites SET
             name = :name, description = :description, module = :module,
             priority = :priority, status = :status, owner = :owner,
             concurrent = :concurrent, config = :config, tags = :tags,
             updated_at = CURRENT_TIMESTAMP
             WHERE id = :id"""
    
    params = {
        "id": suite_id,
        "name": data.get("name"),
        "description": data.get("description"),
        "module": data.get("module"),
        "priority": data.get("priority"),
        "status": data.get("status"),
        "owner": data.get("owner"),
        "concurrent": data.get("concurrent"),
        "config": json.dumps(data.get("config", {}), ensure_ascii=False),
        "tags": json.dumps(data.get("tags", []), ensure_ascii=False)
    }
    
    await session.execute(sa_text(sql), params)
    await session.commit()
    
    return {"message": "Suite updated"}


@router.delete("/{suite_id}")
async def delete_suite(suite_id: int, session=Depends(get_db)):
    """Delete a suite."""
    r = await session.execute(sa_text("SELECT id FROM test_suites WHERE id = :id"), {"id": suite_id})
    if not r.fetchone():
        raise HTTPException(status_code=404, detail="Suite not found")
    
    await session.execute(sa_text("DELETE FROM test_cases WHERE suite_id = :id"), {"id": suite_id})
    await session.execute(sa_text("DELETE FROM test_suites WHERE id = :id"), {"id": suite_id})
    await session.commit()
    
    return {"message": "Suite deleted"}


@router.post("/{suite_id}/run")
async def run_suite(suite_id: int, session=Depends(get_db)):
    """Run a test suite."""
    from app.engine import TestRunner
    runner = TestRunner()
    result = await runner.run_suite(suite_id)
    return result
