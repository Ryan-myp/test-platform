"""调度器 API — 定时任务管理"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
import json
from datetime import datetime, timezone, timedelta
import re

from app.database import get_db, _exec
from app.api.tasks import _run_auto_execution, call_ai

router = APIRouter(prefix="/api/schedule", tags=["定时调度"])


class ScheduleCreate(BaseModel):
    name: str
    entry_type: str
    schedule: str  # cron expression
    input_data: dict = {}
    enabled: bool = True


def parse_cron(cron: str) -> timedelta | None:
    """简单解析 cron 表达式，返回下次执行时间（简化版）"""
    parts = cron.strip().split()
    if len(parts) != 5:
        return None
    try:
        minute, hour, day, month, weekday = parts
        # 支持 */N 格式
        if minute.startswith("*/"):
            interval_min = int(minute[2:])
            return timedelta(minutes=interval_min)
        if hour.startswith("*/"):
            interval_hr = int(hour[2:])
            return timedelta(hours=interval_hr)
        # 默认每分钟
        return timedelta(minutes=1)
    except (ValueError, IndexError):
        return None


@router.get("")
async def list_schedules(session=Depends(get_db)):
    result = await _exec(session, "SELECT * FROM scheduled_jobs ORDER BY created_at DESC")
    rows = result.fetchall()
    return {
        "data": [{
            "id": r[0], "name": r[1], "entry_type": r[2],
            "schedule": r[3], "enabled": bool(r[4]),
            "last_run": r[5], "next_run": r[6], "created_at": r[7]
        } for r in rows],
        "total": len(rows)
    }


@router.post("")
async def create_schedule(job: ScheduleCreate, session=Depends(get_db)):
    now = datetime.now(timezone.utc)
    interval = parse_cron(job.schedule)
    next_run = (now + interval).isoformat() if interval else now.isoformat()

    await _exec(session, """
        INSERT INTO scheduled_jobs (name, entry_type, schedule, input_data, enabled, next_run)
        VALUES (:name, :etype, :schedule, :input, :enabled, :next)
    """, {
        "name": job.name, "etype": job.entry_type,
        "schedule": job.schedule, "input": json.dumps(job.input_data, ensure_ascii=False),
        "enabled": job.enabled, "next": next_run
    })
    return {"message": "Schedule created"}


@router.put("/{job_id}")
async def update_schedule(job_id: int, job: ScheduleCreate, session=Depends(get_db)):
    await _exec(session, """
        UPDATE scheduled_jobs SET name=:name, entry_type=:etype, schedule=:schedule,
            input_data=:input, enabled=:enabled WHERE id=:id
    """, {
        "id": job_id, "name": job.name, "etype": job.entry_type,
        "schedule": job.schedule, "input": json.dumps(job.input_data, ensure_ascii=False),
        "enabled": job.enabled
    })
    return {"message": "Updated"}


@router.delete("/{job_id}")
async def delete_schedule(job_id: int, session=Depends(get_db)):
    await _exec(session, "DELETE FROM scheduled_jobs WHERE id = :id", {"id": job_id})
    return {"message": "Deleted"}


@router.post("/{job_id}/run")
async def run_now(job_id: int, session=Depends(get_db)):
    """手动触发一次执行"""
    result = await _exec(session, "SELECT * FROM scheduled_jobs WHERE id = :id", {"id": job_id})
    row = result.fetchone()
    if not row:
        raise HTTPException(404, "Schedule not found")

    now = datetime.now(timezone.utc).isoformat()
    await _exec(session, "UPDATE scheduled_jobs SET last_run = :now WHERE id = :id",
                   {"now": now, "id": job_id})
    return {"message": "Triggered", "job_id": job_id}


@router.get("/stats")
async def schedule_stats(session=Depends(get_db)):
    result = await _exec(session, """
        SELECT enabled, COUNT(*) FROM scheduled_jobs GROUP BY enabled
    """)
    rows = result.fetchall()
    return {str(r[0]): r[1] for r in rows}
