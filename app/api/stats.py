"""统计 API"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.database import get_db, _exec

router = APIRouter(prefix="/api/stats", tags=["统计"])


@router.get("")
async def get_stats(session=Depends(get_db)):
    # 任务统计
    result = await _exec(session, """
        SELECT entry_type, COUNT(*),
               SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END),
               SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END)
        FROM task_executions GROUP BY entry_type
    """)
    by_entry = {}
    for row in result.fetchall():
        by_entry[row[0]] = {"total": row[1], "completed": row[2], "failed": row[3]}

    total = await _exec(session, "SELECT COUNT(*) FROM task_executions")
    total_tasks = total.fetchone()[0]

    # 知识库统计
    k_result = await _exec(session, "SELECT category, COUNT(*) FROM knowledge GROUP BY category")
    by_category = {row[0]: row[1] for row in k_result.fetchall()}

    # Bug 统计
    b_result = await _exec(session, """
        SELECT severity, COUNT(*) FROM bugs GROUP BY severity
    """)
    by_severity = {row[0]: row[1] for row in b_result.fetchall()}

    # 最近执行
    recent = await _exec(session, """
        SELECT id, entry_type, title, status, created_at
        FROM task_executions ORDER BY created_at DESC LIMIT 10
    """)
    recent_tasks = [{"id": r[0], "entry_type": r[1], "title": r[2],
                     "status": r[3], "created_at": r[4][:16]} for r in recent.fetchall()]

    return {
        "total_tasks": total_tasks,
        "by_entry": by_entry,
        "knowledge_by_category": by_category,
        "bugs_by_severity": by_severity,
        "recent_tasks": recent_tasks
    }
