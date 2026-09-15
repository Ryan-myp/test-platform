"""Test executions API."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text as sa_text
from typing import Any, Dict, List, Optional
import json
import logging
import uuid

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/executions", tags=["执行记录"])


async def get_db():
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/dashboard")
async def dashboard(period: str = "7d", session=Depends(get_db)) -> Dict[str, Any]:
    """Get execution dashboard data."""
    try:
        r = await session.execute(sa_text("""
            SELECT 
                COUNT(*) as total_runs,
                COUNT(DISTINCT case_id) as total_cases,
                SUM(CASE WHEN status='passed' THEN 1 ELSE 0 END) as total_pass,
                SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as total_fail,
                SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) as total_error,
                AVG(duration_ms) as avg_duration_ms
            FROM test_results
            WHERE started_at >= datetime('now', '-7 days')
        """))
        row = r.fetchone()
        
        total = row[0] or 0
        passed = row[2] or 0
        fail = row[3] or 0
        error = row[4] or 0
        pass_rate = f"{(passed / (passed + fail + error) * 100):.1f}%" if (passed + fail + error) > 0 else "0%"
        
        return {
            "period": f"近{period}",
            "summary": {
                "total_runs": total,
                "total_cases": row[1] or 0,
                "total_pass": passed,
                "total_fail": fail,
                "total_error": error,
                "pass_rate": pass_rate,
                "avg_duration_ms": row[5] or 0
            },
            "trends": [],
            "environments": []
        }
    except Exception as e:
        logger.error(f"Failed to get dashboard: {e}")
        return {
            "period": f"近{period}",
            "summary": {"total_runs": 0, "total_cases": 0, "total_pass": 0, "total_fail": 0, "total_error": 0, "pass_rate": "0%", "avg_duration_ms": 0},
            "trends": [],
            "environments": []
        }


@router.get("")
async def list_executions(
    suite_id: Optional[int] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    session=Depends(get_db)
) -> Dict[str, Any]:
    """List test executions."""
    conditions = []
    params = {}
    
    if suite_id:
        conditions.append("suite_id = :suite_id")
        params["suite_id"] = suite_id
    if status:
        conditions.append("status = :status")
        params["status"] = status
    
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    count_sql = f"SELECT COUNT(*) FROM test_results {where}"
    r = await session.execute(sa_text(count_sql), params)
    total = r.scalar() or 0
    
    sql = f"""SELECT id, suite_id, case_id, execution_id, status, duration_ms,
              actual_result, expected_result, error_message, screenshots, logs,
              started_at, completed_at
              FROM test_results {where} 
              ORDER BY id DESC LIMIT :limit OFFSET :offset"""
    params["limit"] = page_size
    params["offset"] = (page - 1) * page_size
    
    r = await session.execute(sa_text(sql), params)
    rows = r.fetchall()
    
    executions = []
    for row in rows:
        executions.append({
            "id": row[0],
            "suite_id": row[1],
            "case_id": row[2],
            "execution_id": row[3] or "",
            "status": row[4] or "pending",
            "duration_ms": row[5] or 0,
            "actual_result": row[6] or "",
            "expected_result": row[7] or "",
            "error_message": row[8] or "",
            "screenshots": json.loads(row[9] or "[]"),
            "logs": row[10] or "",
            "started_at": row[11],
            "completed_at": row[12]
        })
    
    return {
        "items": executions,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.post("/run")
async def run_execution(data: Dict[str, Any], session=Depends(get_db)):
    """Run a test execution."""
    suite_id = data.get("suite_id")
    case_ids = data.get("case_ids", [])
    
    if not suite_id and not case_ids:
        raise HTTPException(status_code=400, detail="Either suite_id or case_ids must be provided")
    
    # Get cases
    if suite_id:
        r = await session.execute(sa_text("SELECT id FROM test_cases WHERE suite_id = :id"), {"id": suite_id})
        case_ids = [row[0] for row in r.fetchall()]
    
    if not case_ids:
        raise HTTPException(status_code=400, detail="No cases found")
    
    # Create execution record
    execution_id = f"exec_{uuid.uuid4().hex[:8]}"
    
    # Run tests
    from app.engine import TestRunner
    runner = TestRunner()
    results = await runner.run_cases(case_ids, execution_id)
    
    # Save results
    for result in results:
        await session.execute(sa_text("""
            INSERT INTO test_results 
            (suite_id, case_id, execution_id, status, duration_ms, actual_result, expected_result, 
             error_message, started_at, completed_at)
            VALUES (:suite_id, :case_id, :execution_id, :status, :duration_ms, :actual_result, :expected_result,
                    :error_message, :started_at, :completed_at)
        """), {
            "suite_id": suite_id,
            "case_id": result["case_id"],
            "execution_id": execution_id,
            "status": result["status"],
            "duration_ms": result.get("duration_ms", 0),
            "actual_result": json.dumps(result.get("actual_result", {}), ensure_ascii=False),
            "expected_result": result.get("expected", ""),
            "error_message": result.get("error", ""),
            "started_at": result.get("started_at", ""),
            "completed_at": result.get("completed_at", "")
        })
    
    await session.commit()
    
    return {
        "execution_id": execution_id,
        "suite_id": suite_id,
        "total": len(results),
        "passed": sum(1 for r in results if r["status"] == "passed"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "results": results
    }


@router.post("/run-case")
async def run_single_case(data: Dict[str, Any], session=Depends(get_db)):
    """Execute a single test case."""
    try:
        case_id = data.get("case_id")
        
        # Get case
        r = await session.execute(sa_text("SELECT * FROM test_cases WHERE id = :id"), {"id": case_id})
        case = r.fetchone()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Execute using test runner
        from app.test_runner import runner
        result = await runner.run_case({
            "id": case[0],
            "name": case[1],
            "case_type": case[4],
            "api_config": json.loads(case[11] or "{}") if case[11] else {},
            "steps": case[9],
            "expected": case[10]
        })
        
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
            "execution_id": result.get("execution_id", ""),
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
        logger.error(f"Failed to run case: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-suite")
async def run_suite(data: Dict[str, Any], session=Depends(get_db)):
    """Execute a test suite."""
    try:
        suite_id = data.get("suite_id")
        
        # Get suite
        r = await session.execute(sa_text("SELECT * FROM test_suites WHERE id = :id"), {"id": suite_id})
        suite = r.fetchone()
        if not suite:
            raise HTTPException(status_code=404, detail="Suite not found")
        
        # Get cases
        r = await session.execute(sa_text(
            "SELECT id, name, case_type, api_config, steps, expected FROM test_cases WHERE suite_id = :suite_id AND status = 'active'"
        ), {"suite_id": suite_id})
        cases = r.fetchall()
        
        # Execute each case
        from app.test_runner import runner
        results = []
        for case in cases:
            result = await runner.run_case({
                "id": case[0],
                "name": case[1],
                "case_type": case[2],
                "api_config": json.loads(case[3] or "{}") if case[3] else {},
                "steps": case[4],
                "expected": case[5]
            })
            results.append(result)
        
        # Save results
        passed = sum(1 for r in results if r.get("status") == "passed")
        failed = sum(1 for r in results if r.get("status") == "failed")
        error = sum(1 for r in results if r.get("status") == "error")
        
        now = datetime.now().isoformat()
        
        return {
            "suite_id": suite_id,
            "suite_name": suite[1] or "",
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "error": error,
            "pass_rate": round(passed / max(len(results), 1) * 100, 1),
            "results": results,
            "started_at": now
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to run suite: {e}")
        raise HTTPException(status_code=500, detail=str(e))
