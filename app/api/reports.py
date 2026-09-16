"""Report generation API."""
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy import text as sa_text
from typing import Any, Dict, List, Optional
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["报告生成"])

async def get_db():
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/dashboard")
async def generate_dashboard_report(session=Depends(get_db)) -> Dict[str, Any]:
    """Generate comprehensive dashboard report."""
    try:
        # Case stats
        r = await session.execute(sa_text("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status='active' THEN 1 ELSE 0 END) as active,
                SUM(CASE WHEN is_automated=1 THEN 1 ELSE 0 END) as automated,
                SUM(CASE WHEN priority='P0' THEN 1 ELSE 0 END) as p0,
                SUM(CASE WHEN priority='P1' THEN 1 ELSE 0 END) as p1,
                SUM(CASE WHEN case_type='api' THEN 1 ELSE 0 END) as api,
                SUM(CASE WHEN case_type='sql' THEN 1 ELSE 0 END) as sql,
                SUM(CASE WHEN case_type='browser' THEN 1 ELSE 0 END) as browser
            FROM test_cases
        """))
        case_stats = r.fetchone()
        
        # Suite stats
        r = await session.execute(sa_text("""
            SELECT id, name, description, priority, status,
                   (SELECT COUNT(*) FROM test_cases WHERE suite_id = ts.id) as case_count
            FROM test_suites ts
            ORDER BY id
        """))
        suites = []
        for row in r.fetchall():
            suites.append({
                "id": row[0],
                "name": row[1] or "",
                "description": row[2] or "",
                "priority": row[3] or "P2",
                "status": row[4] or "draft",
                "case_count": row[5] or 0
            })
        
        # Bug stats
        r = await session.execute(sa_text("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status='open' THEN 1 ELSE 0 END) as open,
                SUM(CASE WHEN severity='critical' THEN 1 ELSE 0 END) as critical,
                SUM(CASE WHEN severity='major' THEN 1 ELSE 0 END) as major
            FROM bugs
        """))
        bug_stats = r.fetchone()
        
        # Execution stats
        r = await session.execute(sa_text("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status='passed' THEN 1 ELSE 0 END) as passed,
                SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) as error,
                AVG(duration_ms) as avg_duration,
                MAX(started_at) as last_run
            FROM test_results
        """))
        exec_stats = r.fetchone()
        
        # Top failing cases
        r = await session.execute(sa_text("""
            SELECT tc.name, COUNT(*) as failures
            FROM test_results tr
            JOIN test_cases tc ON tr.case_id = tc.id
            WHERE tr.status = 'failed'
            GROUP BY tc.id
            ORDER BY failures DESC
            LIMIT 5
        """))
        top_failures = [{"case": row[0], "failures": row[1]} for row in r.fetchall()]
        
        # Trend data (last 7 days)
        trends = []
        for i in range(7):
            date = (datetime.now() - timedelta(days=6-i)).strftime("%Y-%m-%d")
            r = await session.execute(sa_text("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status='passed' THEN 1 ELSE 0 END) as passed,
                    SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed
                FROM test_results
                WHERE date(started_at) = :date
            """), {"date": date})
            row = r.fetchone()
            trends.append({
                "date": date,
                "total": row[0] or 0,
                "passed": row[1] or 0,
                "failed": row[2] or 0,
                "pass_rate": round((row[1] or 0) / max(row[0], 1) * 100, 1) if row[0] else 0
            })
        
        return {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_cases": case_stats[0] or 0,
                "active_cases": case_stats[1] or 0,
                "automated_cases": case_stats[2] or 0,
                "total_suites": len(suites),
                "open_bugs": bug_stats[1] or 0,
                "total_executions": exec_stats[0] or 0,
                "pass_rate": round((exec_stats[1] or 0) / max(exec_stats[0], 1) * 100, 1) if exec_stats[0] else 0
            },
            "cases": {
                "total": case_stats[0] or 0,
                "active": case_stats[1] or 0,
                "automated": case_stats[2] or 0,
                "p0": case_stats[3] or 0,
                "p1": case_stats[4] or 0,
                "by_type": {
                    "api": case_stats[5] or 0,
                    "sql": case_stats[6] or 0,
                    "browser": case_stats[7] or 0
                }
            },
            "suites": suites,
            "bugs": {
                "total": bug_stats[0] or 0,
                "open": bug_stats[1] or 0,
                "critical": bug_stats[2] or 0,
                "major": bug_stats[3] or 0
            },
            "executions": {
                "total": exec_stats[0] or 0,
                "passed": exec_stats[1] or 0,
                "failed": exec_stats[2] or 0,
                "error": exec_stats[3] or 0,
                "avg_duration_ms": round(exec_stats[4] or 0, 2),
                "last_run": exec_stats[5]
            },
            "top_failures": top_failures,
            "trends": trends
        }
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/{format}")
async def export_report(format: str, session=Depends(get_db)):
    """Export report in specified format (json, csv)."""
    try:
        if format == "json":
            report = await generate_dashboard_report(session)
            return report
        
        elif format == "csv":
            r = await session.execute(sa_text("""
                SELECT id, name, module, priority, case_type, status,
                       preconditions, steps, expected, tags
                FROM test_cases
                ORDER BY id
            """))
            rows = r.fetchall()
            
            lines = ["ID,Name,Module,Priority,Type,Status,Preconditions,Steps,Expected,Tags"]
            for row in rows:
                def escape(val):
                    if val is None:
                        return ""
                    val = str(val).replace('"', '""')
                    if ',' in val or '\n' in val:
                        return f'"{val}"'
                    return val
                lines.append(f"{row[0]},{escape(row[1])},{escape(row[2])},{escape(row[3])},{escape(row[4])},{escape(row[5])},{escape(row[6])},{escape(row[7])},{escape(row[8])},{escape(row[9])}")
            
            return {"format": "csv", "content": "\n".join(lines), "rows": len(rows)}
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export report: {e}")
        raise HTTPException(status_code=500, detail=str(e))
