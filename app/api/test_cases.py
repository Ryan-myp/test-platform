"""Test cases API."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text as sa_text
from typing import Any, Dict, List, Optional
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/cases", tags=["测试用例"])


async def get_db():
    """Get database session."""
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/stats/summary")
async def case_stats(session=Depends(get_db)) -> Dict[str, Any]:
    """Get test case statistics."""
    try:
        r = await session.execute(sa_text("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status='active' THEN 1 ELSE 0 END) as active,
                SUM(CASE WHEN status='draft' THEN 1 ELSE 0 END) as draft,
                SUM(CASE WHEN is_automated=1 THEN 1 ELSE 0 END) as automated,
                SUM(CASE WHEN case_type='api' THEN 1 ELSE 0 END) as api_count,
                SUM(CASE WHEN case_type='browser' THEN 1 ELSE 0 END) as browser_count,
                SUM(CASE WHEN case_type='sql' THEN 1 ELSE 0 END) as sql_count
            FROM test_cases
        """))
        row = r.fetchone()
        return {
            "total": row[0] or 0,
            "active": row[1] or 0,
            "draft": row[2] or 0,
            "automated": row[3] or 0,
            "api_count": row[4] or 0,
            "browser_count": row[5] or 0,
            "sql_count": row[6] or 0
        }
    except Exception as e:
        logger.error(f"Failed to get case stats: {e}")
        return {"total": 0, "active": 0, "draft": 0, "automated": 0, "api_count": 0, "browser_count": 0, "sql_count": 0}


@router.get("")
async def list_cases(
    suite_id: Optional[int] = None,
    case_type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    session=Depends(get_db)
) -> Dict[str, Any]:
    """List test cases with filtering."""
    conditions = []
    params = {}
    
    if suite_id:
        conditions.append("suite_id = :suite_id")
        params["suite_id"] = suite_id
    if case_type:
        conditions.append("case_type = :case_type")
        params["case_type"] = case_type
    if status:
        conditions.append("status = :status")
        params["status"] = status
    if search:
        conditions.append("(name LIKE :search OR tags LIKE :search)")
        params["search"] = f"%{search}%"
    
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    # Get total count
    count_sql = f"SELECT COUNT(*) FROM test_cases {where}"
    r = await session.execute(sa_text(count_sql), params)
    total = r.scalar() or 0
    
    # Get page data
    sql = f"""SELECT id, name, module, priority, case_type, automation_type, 
              status, is_automated, preconditions, steps, expected, 
              tags, owner, version, suite_id, created_at, updated_at
              FROM test_cases {where} 
              ORDER BY id DESC LIMIT :limit OFFSET :offset"""
    params["limit"] = page_size
    params["offset"] = (page - 1) * page_size
    
    r = await session.execute(sa_text(sql), params)
    rows = r.fetchall()
    
    cases = []
    for row in rows:
        cases.append({
            "id": row[0],
            "name": row[1],
            "module": row[2] or "",
            "priority": row[3] or "P2",
            "case_type": row[4] or "api",
            "automation_type": row[5] or "",
            "status": row[6] or "draft",
            "is_automated": bool(row[7]),
            "preconditions": row[8] or "",
            "steps": row[9] or "[]",
            "expected": row[10] or "",
            "tags": row[11] or "[]",
            "owner": row[12] or "",
            "version": row[13] or 1,
            "suite_id": row[14],
            "created_at": row[15],
            "updated_at": row[16]
        })
    
    return {
        "items": cases,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.get("/{case_id}")
async def get_case(case_id: int, session=Depends(get_db)):
    """Get a specific test case."""
    r = await session.execute(sa_text("SELECT * FROM test_cases WHERE id = :id"), {"id": case_id})
    row = r.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")
    
    return {
        "id": row[0],
        "name": row[1],
        "module": row[2] or "",
        "priority": row[3] or "P2",
        "case_type": row[4] or "api",
        "automation_type": row[5] or "",
        "status": row[6] or "draft",
        "is_automated": bool(row[7]),
        "preconditions": row[8] or "",
        "steps": row[9] or "[]",
        "expected": row[10] or "",
        "api_config": row[11] or "{}",
        "sql_config": row[12] or "{}",
        "browser_config": row[13] or "{}",
        "script_config": row[14] or "{}",
        "tags": row[15] or "[]",
        "owner": row[16] or "",
        "version": row[17] or 1,
        "suite_id": row[18],
        "created_at": row[19],
        "updated_at": row[20]
    }


@router.post("")
async def create_case(data: Dict[str, Any], session=Depends(get_db)):
    """Create a new test case."""
    sql = """INSERT INTO test_cases 
             (name, module, priority, case_type, automation_type, status, is_automated,
              preconditions, steps, expected, api_config, sql_config, browser_config, 
              script_config, tags, owner, suite_id, version)
             VALUES (:name, :module, :priority, :case_type, :automation_type, :status, 
                     :is_automated, :preconditions, :steps, :expected, :api_config, :sql_config,
                     :browser_config, :script_config, :tags, :owner, :suite_id, 1)"""
    
    params = {
        "name": data.get("name", ""),
        "module": data.get("module", ""),
        "priority": data.get("priority", "P2"),
        "case_type": data.get("case_type", "api"),
        "automation_type": data.get("automation_type", ""),
        "status": data.get("status", "draft"),
        "is_automated": data.get("is_automated", 0),
        "preconditions": data.get("preconditions", ""),
        "steps": json.dumps(data.get("steps", []), ensure_ascii=False),
        "expected": data.get("expected", ""),
        "api_config": json.dumps(data.get("api_config", {}), ensure_ascii=False),
        "sql_config": json.dumps(data.get("sql_config", {}), ensure_ascii=False),
        "browser_config": json.dumps(data.get("browser_config", {}), ensure_ascii=False),
        "script_config": json.dumps(data.get("script_config", {}), ensure_ascii=False),
        "tags": json.dumps(data.get("tags", []), ensure_ascii=False),
        "owner": data.get("owner", ""),
        "suite_id": data.get("suite_id")
    }
    
    await session.execute(sa_text(sql), params)
    await session.commit()
    
    r = await session.execute(sa_text("SELECT last_insert_rowid()"))
    case_id = r.scalar()
    
    return {"id": case_id, "message": "Case created"}


@router.put("/{case_id}")
async def update_case(case_id: int, data: Dict[str, Any], session=Depends(get_db)):
    """Update a test case."""
    # Check if exists
    r = await session.execute(sa_text("SELECT id FROM test_cases WHERE id = :id"), {"id": case_id})
    if not r.fetchone():
        raise HTTPException(status_code=404, detail="Case not found")
    
    sql = """UPDATE test_cases SET
             name = :name, module = :module, priority = :priority,
             case_type = :case_type, automation_type = :automation_type,
             status = :status, is_automated = :is_automated,
             preconditions = :preconditions, steps = :steps, expected = :expected,
             api_config = :api_config, sql_config = :sql_config,
             browser_config = :browser_config, script_config = :script_config,
             tags = :tags, owner = :owner, suite_id = :suite_id,
             version = version + 1, updated_at = CURRENT_TIMESTAMP
             WHERE id = :id"""
    
    params = {
        "id": case_id,
        "name": data.get("name"),
        "module": data.get("module"),
        "priority": data.get("priority"),
        "case_type": data.get("case_type"),
        "automation_type": data.get("automation_type"),
        "status": data.get("status"),
        "is_automated": data.get("is_automated"),
        "preconditions": data.get("preconditions"),
        "steps": json.dumps(data.get("steps", []), ensure_ascii=False),
        "expected": data.get("expected"),
        "api_config": json.dumps(data.get("api_config", {}), ensure_ascii=False),
        "sql_config": json.dumps(data.get("sql_config", {}), ensure_ascii=False),
        "browser_config": json.dumps(data.get("browser_config", {}), ensure_ascii=False),
        "script_config": json.dumps(data.get("script_config", {}), ensure_ascii=False),
        "tags": json.dumps(data.get("tags", []), ensure_ascii=False),
        "owner": data.get("owner"),
        "suite_id": data.get("suite_id")
    }
    
    await session.execute(sa_text(sql), params)
    await session.commit()
    
    return {"message": "Case updated"}


@router.delete("/{case_id}")
async def delete_case(case_id: int, session=Depends(get_db)):
    """Delete a test case."""
    r = await session.execute(sa_text("SELECT id FROM test_cases WHERE id = :id"), {"id": case_id})
    if not r.fetchone():
        raise HTTPException(status_code=404, detail="Case not found")
    
    await session.execute(sa_text("DELETE FROM test_cases WHERE id = :id"), {"id": case_id})
    await session.commit()
    
    return {"message": "Case deleted"}


@router.post("/{case_id}/execute")
async def execute_case(case_id: int, session=Depends(get_db)):
    """Execute a test case."""
    try:
        r = await session.execute(sa_text("SELECT * FROM test_cases WHERE id = :id"), {"id": case_id})
        case_row = r.fetchone()
        if not case_row:
            raise HTTPException(status_code=404, detail="Case not found")
        
        case_data = {
            "id": case_row[0],
            "name": case_row[1],
            "case_type": case_row[4] or "api",
            "automation_type": case_row[5] or "",
            "api_config": json.loads(case_row[11] or "{}"),
            "sql_config": json.loads(case_row[12] or "{}"),
            "browser_config": json.loads(case_row[13] or "{}"),
            "expected": case_row[10] or ""
        }
        
        # Execute based on type
        from app.engine import TestRunner
        runner = TestRunner()
        result = await runner.execute_case(case_data)
        
        # Save result
        await session.execute(sa_text("""
            INSERT INTO test_results 
            (suite_id, case_id, execution_id, status, duration_ms, actual_result, expected_result, 
             error_message, started_at, completed_at)
            VALUES (:suite_id, :case_id, :execution_id, :status, :duration_ms, :actual_result, :expected_result,
                    :error_message, :started_at, :completed_at)
        """), {
            "suite_id": case_row[18],
            "case_id": case_id,
            "execution_id": result.get("execution_id", ""),
            "status": result.get("status", "failed"),
            "duration_ms": result.get("duration_ms", 0),
            "actual_result": json.dumps(result.get("actual_result", {}), ensure_ascii=False),
            "expected_result": case_row[10] or "",
            "error_message": result.get("error", ""),
            "started_at": result.get("started_at", ""),
            "completed_at": result.get("completed_at", "")
        })
        await session.commit()
        
        return result
    except Exception as e:
        logger.error(f"Execute case failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
