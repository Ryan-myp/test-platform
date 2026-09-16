"""Test case management API."""
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy import text as sa_text
from typing import Any, Dict, List, Optional
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/test-cases", tags=["测试用例"])

async def get_db():
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
                SUM(CASE WHEN is_automated=1 THEN 1 ELSE 0 END) as automated,
                SUM(CASE WHEN priority='P0' THEN 1 ELSE 0 END) as p0,
                SUM(CASE WHEN priority='P1' THEN 1 ELSE 0 END) as p1,
                SUM(CASE WHEN case_type='api' THEN 1 ELSE 0 END) as api_count,
                SUM(CASE WHEN case_type='sql' THEN 1 ELSE 0 END) as sql_count,
                SUM(CASE WHEN case_type='browser' THEN 1 ELSE 0 END) as browser_count
            FROM test_cases
        """))
        row = r.fetchone()
        return {
            "total": row[0] or 0,
            "active": row[1] or 0,
            "automated": row[2] or 0,
            "p0": row[3] or 0,
            "p1": row[4] or 0,
            "by_type": {
                "api": row[5] or 0,
                "sql": row[6] or 0,
                "browser": row[7] or 0
            }
        }
    except Exception as e:
        logger.error(f"Failed to get case stats: {e}")
        return {"total": 0, "active": 0, "automated": 0}


@router.get("")
async def list_cases(
    module: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    case_type: Optional[str] = Query(None),
    status: Optional[str] = Query("all"),
    suite_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session=Depends(get_db)
) -> Dict[str, Any]:
    """List test cases with filters."""
    try:
        conditions = []
        params = {"limit": limit, "offset": offset}
        
        if module:
            conditions.append("module = :module")
            params["module"] = module
        if priority:
            conditions.append("priority = :priority")
            params["priority"] = priority
        if case_type:
            conditions.append("case_type = :case_type")
            params["case_type"] = case_type
        if status != "all":
            conditions.append("status = :status")
            params["status"] = status
        if suite_id:
            conditions.append("suite_id = :suite_id")
            params["suite_id"] = suite_id
        if search:
            conditions.append("(name LIKE :search OR preconditions LIKE :search)")
            params["search"] = f"%{search}%"
        
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        # Count
        count_sql = f"SELECT COUNT(*) FROM test_cases {where}"
        r = await session.execute(sa_text(count_sql), params)
        total = r.scalar() or 0
        
        # Get cases
        sql = f"""SELECT id, name, module, priority, case_type, automation_type, 
                  status, is_automated, preconditions, steps, expected,
                  tags, owner, version, suite_id, created_at, updated_at
                  FROM test_cases {where}
                  ORDER BY 
                    CASE priority WHEN 'P0' THEN 1 WHEN 'P1' THEN 2 WHEN 'P2' THEN 3 ELSE 4 END,
                    id DESC
                  LIMIT :limit OFFSET :offset"""
        
        r = await session.execute(sa_text(sql), params)
        rows = r.fetchall()
        
        cases = []
        for row in rows:
            tags_str = row[12] or "[]"
            try:
                tags = json.loads(tags_str) if tags_str else []
            except:
                tags = []
            
            cases.append({
                "id": row[0],
                "name": row[1] or "",
                "module": row[2] or "",
                "priority": row[3] or "P2",
                "case_type": row[4] or "api",
                "automation_type": row[5] or "",
                "status": row[6] or "draft",
                "is_automated": bool(row[7]),
                "preconditions": row[8] or "",
                "steps": row[9] or "",
                "expected": row[10] or "",
                "tags": tags,
                "owner": row[11] or "",
                "version": row[13] or "1.0",
                "suite_id": row[14],
                "created_at": row[15],
                "updated_at": row[16]
            })
        
        return {"cases": cases, "total": total, "limit": limit, "offset": offset}
    except Exception as e:
        logger.error(f"Failed to list cases: {e}")
        return {"cases": [], "total": 0}


@router.get("/{case_id}")
async def get_case(case_id: int, session=Depends(get_db)) -> Dict[str, Any]:
    """Get a single test case."""
    try:
        r = await session.execute(sa_text("SELECT * FROM test_cases WHERE id = :id"), {"id": case_id})
        row = r.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Case not found")
        
        tags_str = row[12] or "[]"
        try:
            tags = json.loads(tags_str) if tags_str else []
        except:
            tags = []
        
        return {
            "id": row[0],
            "name": row[1] or "",
            "module": row[2] or "",
            "priority": row[3] or "P2",
            "case_type": row[4] or "api",
            "automation_type": row[5] or "",
            "status": row[6] or "draft",
            "is_automated": bool(row[7]),
            "preconditions": row[8] or "",
            "steps": row[9] or "",
            "expected": row[10] or "",
            "api_config": json.loads(row[11] or "{}") if row[11] else {},
            "tags": tags,
            "owner": row[13] or "",
            "version": row[14] or "1.0",
            "suite_id": row[15],
            "source_task_id": row[16],
            "created_at": row[17],
            "updated_at": row[18]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get case: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_case(data: Dict[str, Any], session=Depends(get_db)):
    """Create a new test case."""
    try:
        tags = data.get("tags", [])
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except:
                tags = []
        
        now = datetime.now().isoformat()
        
        r = await session.execute(sa_text("""
            INSERT INTO test_cases (
                name, module, priority, case_type, automation_type, status,
                is_automated, preconditions, steps, expected, api_config,
                tags, owner, version, suite_id, source_task_id, created_at, updated_at
            ) VALUES (
                :name, :module, :priority, :case_type, :automation_type, :status,
                :is_automated, :preconditions, :steps, :expected, :api_config,
                :tags, :owner, :version, :suite_id, :source_task_id, :created_at, :updated_at
            )
        """), {
            "name": data.get("name", "未命名用例"),
            "module": data.get("module", ""),
            "priority": data.get("priority", "P2"),
            "case_type": data.get("case_type", "api"),
            "automation_type": data.get("automation_type", ""),
            "status": data.get("status", "draft"),
            "is_automated": data.get("is_automated", False),
            "preconditions": data.get("preconditions", ""),
            "steps": data.get("steps", ""),
            "expected": data.get("expected", ""),
            "api_config": json.dumps(data.get("api_config", {}), ensure_ascii=False),
            "tags": json.dumps(tags, ensure_ascii=False),
            "owner": data.get("owner", ""),
            "version": data.get("version", "1.0"),
            "suite_id": data.get("suite_id"),
            "source_task_id": data.get("source_task_id"),
            "created_at": now,
            "updated_at": now
        })
        await session.commit()
        
        return {"id": r.lastrowid, "message": "Case created"}
    except Exception as e:
        logger.error(f"Failed to create case: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{case_id}")
async def update_case(case_id: int, data: Dict[str, Any], session=Depends(get_db)):
    """Update a test case."""
    try:
        # Check exists
        r = await session.execute(sa_text("SELECT id FROM test_cases WHERE id = :id"), {"id": case_id})
        if not r.fetchone():
            raise HTTPException(status_code=404, detail="Case not found")
        
        tags = data.get("tags", [])
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except:
                tags = []
        
        await session.execute(sa_text("""
            UPDATE test_cases SET
                name=:name, module=:module, priority=:priority,
                case_type=:case_type, automation_type=:automation_type,
                status=:status, is_automated=:is_automated,
                preconditions=:preconditions, steps=:steps, expected=:expected,
                api_config=:api_config, tags=:tags, owner=:owner,
                version=:version, suite_id=:suite_id, updated_at=:updated_at
            WHERE id=:id
        """), {
            "id": case_id,
            "name": data.get("name", ""),
            "module": data.get("module", ""),
            "priority": data.get("priority", "P2"),
            "case_type": data.get("case_type", "api"),
            "automation_type": data.get("automation_type", ""),
            "status": data.get("status", "draft"),
            "is_automated": data.get("is_automated", False),
            "preconditions": data.get("preconditions", ""),
            "steps": data.get("steps", ""),
            "expected": data.get("expected", ""),
            "api_config": json.dumps(data.get("api_config", {}), ensure_ascii=False),
            "tags": json.dumps(tags, ensure_ascii=False),
            "owner": data.get("owner", ""),
            "version": data.get("version", "1.0"),
            "suite_id": data.get("suite_id"),
            "updated_at": datetime.now().isoformat()
        })
        await session.commit()
        
        return {"message": "Case updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update case: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{case_id}")
async def delete_case(case_id: int, session=Depends(get_db)):
    """Delete a test case."""
    try:
        r = await session.execute(sa_text("SELECT id FROM test_cases WHERE id = :id"), {"id": case_id})
        if not r.fetchone():
            raise HTTPException(status_code=404, detail="Case not found")
        
        await session.execute(sa_text("DELETE FROM test_cases WHERE id = :id"), {"id": case_id})
        await session.commit()
        
        return {"message": "Case deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete case: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{case_id}/execute")
async def execute_case(case_id: int, session=Depends(get_db)):
    """Execute a single test case."""
    try:
        # Get case
        r = await session.execute(sa_text("SELECT * FROM test_cases WHERE id = :id"), {"id": case_id})
        case = r.fetchone()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Execute based on case type
        case_type = case[4] or "api"
        api_config = json.loads(case[11] or "{}") if case[11] else {}
        
        result = {"status": "pending", "duration_ms": 0}
        
        if case_type == "api":
            import httpx
            start = datetime.now()
            try:
                url = api_config.get("url", "")
                method = api_config.get("method", "GET").upper()
                headers = api_config.get("headers", {})
                body = api_config.get("body")
                
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.request(method=method, url=url, headers=headers, json=body)
                
                duration = (datetime.now() - start).total_seconds() * 1000
                
                # Check assertions
                assertions = api_config.get("assertions", {})
                passed = True
                errors = []
                
                if "status_code" in assertions:
                    if resp.status_code != assertions["status_code"]:
                        passed = False
                        errors.append(f"Status code mismatch: expected {assertions['status_code']}, got {resp.status_code}")
                
                result = {
                    "status": "passed" if passed else "failed",
                    "status_code": resp.status_code,
                    "duration_ms": round(duration, 2),
                    "response_time_ms": round(duration, 2),
                    "passed": passed,
                    "errors": errors
                }
            except Exception as e:
                result = {"status": "error", "error": str(e)}
        
        elif case_type == "sql":
            db_url = api_config.get("db_url", "")
            sql = api_config.get("sql", "")
            if db_url and sql:
                import sqlite3
                try:
                    start = datetime.now()
                    conn = sqlite3.connect(db_url.replace("sqlite:///", ""))
                    cursor = conn.cursor()
                    cursor.execute(sql)
                    rows = cursor.fetchall()
                    duration = (datetime.now() - start).total_seconds() * 1000
                    result = {
                        "status": "passed",
                        "rows": len(rows),
                        "duration_ms": round(duration, 2),
                        "data": rows[:100]  # Limit to 100 rows
                    }
                    conn.close()
                except Exception as e:
                    result = {"status": "error", "error": str(e)}
            else:
                result = {"status": "skipped", "reason": "No DB URL or SQL"}
        
        else:
            result = {"status": "skipped", "reason": f"Unsupported case type: {case_type}"}
        
        # Save result
        now = datetime.now().isoformat()
        await session.execute(sa_text("""
            INSERT INTO test_results (suite_id, case_id, execution_id, status, duration_ms, 
                                      actual_result, expected_result, error_message, started_at, completed_at)
            VALUES (:suite_id, :case_id, :execution_id, :status, :duration_ms,
                    :actual_result, :expected_result, :error_message, :started_at, :completed_at)
        """), {
            "suite_id": case[15],
            "case_id": case_id,
            "execution_id": f"exec_{case_id}_{int(datetime.now().timestamp())}",
            "status": result.get("status", "pending"),
            "duration_ms": result.get("duration_ms", 0),
            "actual_result": json.dumps(result, ensure_ascii=False),
            "expected_result": case[10] or "",
            "error_message": result.get("error", ""),
            "started_at": now,
            "completed_at": now
        })
        await session.commit()
        
        return {
            "case_id": case_id,
            "case_name": case[1] or "",
            "result": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute case: {e}")
        raise HTTPException(status_code=500, detail=str(e))
