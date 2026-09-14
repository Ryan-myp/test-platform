"""Statistics and dashboard API."""
from fastapi import APIRouter, Depends
from sqlalchemy import text as sa_text
from typing import Any, Dict, List
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stats", tags=["统计"])


@router.get("/dashboard")
async def dashboard_stats(session=Depends(lambda: None)) -> Dict[str, Any]:
    """Get dashboard statistics."""
    from app.database import AsyncSessionLocal
    
    try:
        async with AsyncSessionLocal() as db:
            # Test cases stats
            r = await db.execute(sa_text("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status='active' THEN 1 ELSE 0 END) as active,
                    SUM(CASE WHEN is_automated=1 THEN 1 ELSE 0 END) as automated,
                    SUM(CASE WHEN case_type='api' THEN 1 ELSE 0 END) as api_count,
                    SUM(CASE WHEN case_type='sql' THEN 1 ELSE 0 END) as sql_count,
                    SUM(CASE WHEN case_type='browser' THEN 1 ELSE 0 END) as browser_count
                FROM test_cases
            """))
            cases = r.fetchone()
            
            # Suites stats
            r = await db.execute(sa_text("SELECT COUNT(*), SUM(CASE WHEN status='active' THEN 1 ELSE 0 END) FROM test_suites"))
            suites = r.fetchone()
            
            # Bugs stats
            r = await db.execute(sa_text("""
                SELECT 
                    COUNT(*),
                    SUM(CASE WHEN status != 'closed' THEN 1 ELSE 0 END) as open,
                    SUM(CASE WHEN severity='critical' THEN 1 ELSE 0 END) as critical,
                    SUM(CASE WHEN severity='major' THEN 1 ELSE 0 END) as major
                FROM bugs
            """))
            bugs = r.fetchone()
            
            # Execution stats
            r = await db.execute(sa_text("""
                SELECT 
                    COUNT(*),
                    SUM(CASE WHEN status='passed' THEN 1 ELSE 0 END) as passed,
                    SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) as error_count,
                    AVG(duration_ms) as avg_duration
                FROM test_executions
                WHERE started_at >= datetime('now', '-7 days')
            """))
            executions = r.fetchone()
            
            return {
                "cases": {
                    "total": cases[0] or 0,
                    "active": cases[1] or 0,
                    "automated": cases[2] or 0,
                    "by_type": {
                        "api": cases[3] or 0,
                        "sql": cases[4] or 0,
                        "browser": cases[5] or 0
                    }
                },
                "suites": {
                    "total": suites[0] or 0,
                    "active": suites[1] or 0
                },
                "bugs": {
                    "total": bugs[0] or 0,
                    "open": bugs[1] or 0,
                    "critical": bugs[2] or 0,
                    "major": bugs[3] or 0
                },
                "executions": {
                    "total": executions[0] or 0,
                    "passed": executions[1] or 0,
                    "failed": executions[2] or 0,
                    "error": executions[3] or 0,
                    "avg_duration_ms": round(executions[4] or 0, 2)
                }
            }
    except Exception as e:
        logger.error(f"Failed to get dashboard stats: {e}")
        return {
            "cases": {"total": 0, "active": 0, "automated": 0, "by_type": {"api": 0, "sql": 0, "browser": 0}},
            "suites": {"total": 0, "active": 0},
            "bugs": {"total": 0, "open": 0, "critical": 0, "major": 0},
            "executions": {"total": 0, "passed": 0, "failed": 0, "error": 0, "avg_duration_ms": 0}
        }


@router.get("/trends")
async def trend_stats() -> List[Dict[str, Any]]:
    """Get trend statistics."""
    return [
        {"date": "今天", "cases": 0, "success": 0, "failed": 0},
        {"date": "昨天", "cases": 0, "success": 0, "failed": 0},
        {"date": "前天", "cases": 0, "success": 0, "failed": 0}
    ]
