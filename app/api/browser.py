"""浏览器测试 API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List, Any
import json
from datetime import datetime, timezone

from app.database import get_db, _exec, AsyncSessionLocal
from app.browser_executor import get_browser_executor, close_browser_executor
from app.entries import ENTRY_DEFS

router = APIRouter(prefix="/api/browser", tags=["浏览器测试"])


class BrowserTestInput(BaseModel):
    url: str
    cases: List[dict]
    viewport: Optional[dict] = None
    task_title: str = "浏览器自动化测试"


class AI_BROWSERTestInput(BaseModel):
    url: str
    feature: str
    priority: str = "P1"
    task_title: str = "AI 生成+执行测试"


@router.post("/execute")
async def execute_browser_test(
    input_data: BrowserTestInput,
    session=Depends(get_db)
):
    """执行浏览器自动化测试"""
    from app.executor import run_browser_test
    
    now = datetime.now(timezone.utc).isoformat()
    await _exec(session, """
        INSERT INTO task_executions (entry_type, title, input_data, ai_output, auto_exec_result, status, created_at)
        VALUES (:etype, :title, :input, '', '{}', 'running', :now)
    """, {"etype": "web_ui_test", "title": input_data.task_title,
          "input": json.dumps({"url": input_data.url, "cases": input_data.cases}, ensure_ascii=False),
          "now": now})

    async with AsyncSessionLocal() as s:
        from sqlalchemy import text as sa_text
        r = await s.execute(sa_text("SELECT last_insert_rowid()"))
        task_id = r.scalar()

    try:
        result = await run_browser_test(task_id, {
            "url": input_data.url,
            "cases_json": json.dumps(input_data.cases, ensure_ascii=False),
            "viewport": f"{input_data.viewport.get('width', 1920)}x{input_data.viewport.get('height', 1080)}" if input_data.viewport else "1920x1080"
        })
        
        now = datetime.now(timezone.utc).isoformat()
        await _exec(session, """
            UPDATE task_executions
            SET auto_exec_result = :auto_res, status = :status, completed_at = :now
            WHERE id = :id
        """, {"id": task_id, "auto_res": json.dumps(result, ensure_ascii=False),
              "status": "success" if result.get("failed", 0) == 0 else "success", "now": now})

        return {"task_id": task_id, "result": result}
    except Exception as e:
        now = datetime.now(timezone.utc).isoformat()
        await _exec(session, """
            UPDATE task_executions SET status = 'failed', completed_at = :now WHERE id = :id
        """, {"id": task_id, "now": now})
        raise HTTPException(500, str(e))


@router.post("/ai-execute")
async def execute_ai_browser_test(
    input_data: AI_BROWSERTestInput,
    session=Depends(get_db)
):
    """AI 生成用例 + 浏览器执行"""
    from app.executor import run_ai_browser_test
    
    now = datetime.now(timezone.utc).isoformat()
    await _exec(session, """
        INSERT INTO task_executions (entry_type, title, input_data, ai_output, auto_exec_result, status, created_at)
        VALUES (:etype, :title, :input, '', '{}', 'running', :now)
    """, {"etype": "ai_test_generation", "title": input_data.task_title,
          "input": json.dumps({"url": input_data.url, "feature": input_data.feature,
                               "priority": input_data.priority}, ensure_ascii=False),
          "now": now})

    async with AsyncSessionLocal() as s:
        from sqlalchemy import text as sa_text
        r = await s.execute(sa_text("SELECT last_insert_rowid()"))
        task_id = r.scalar()

    try:
        result = await run_ai_browser_test(task_id, {
            "url": input_data.url,
            "feature": input_data.feature,
            "priority": input_data.priority
        })
        
        now = datetime.now(timezone.utc).isoformat()
        await _exec(session, """
            UPDATE task_executions
            SET auto_exec_result = :auto_res, status = :status, completed_at = :now
            WHERE id = :id
        """, {"id": task_id, "auto_res": json.dumps(result, ensure_ascii=False),
              "status": "success", "now": now})

        return {"task_id": task_id, "result": result}
    except Exception as e:
        now = datetime.now(timezone.utc).isoformat()
        await _exec(session, """
            UPDATE task_executions SET status = 'failed', completed_at = :now WHERE id = :id
        """, {"id": task_id, "now": now})
        raise HTTPException(500, str(e))


@router.get("/results")
async def list_browser_results(limit: int = 20, session=Depends(get_db)):
    """获取浏览器测试结果历史"""
    result = await _exec(session, """
        SELECT id, task_id, url, cases, passed_count, failed_count, total_count,
               duration_ms, created_at
        FROM browser_test_results 
        ORDER BY created_at DESC LIMIT :limit
    """, {"limit": limit})
    rows = result.fetchall()
    return {
        "data": [{
            "id": r[0], "task_id": r[1], "url": r[2],
            "cases": json.loads(r[3] or "[]"),
            "passed": r[4], "failed": r[5], "total": r[6],
            "duration_ms": r[7], "created_at": r[8]
        } for r in rows],
        "total": len(rows)
    }


@router.get("/screenshots")
async def list_screenshots():
    """获取截图列表"""
    import os
    from pathlib import Path
    screenshot_dir = Path(__file__).parent.parent.parent / "screenshots"
    if not screenshot_dir.exists():
        return {"screenshots": []}
    
    files = sorted(screenshot_dir.glob("*.png"), key=lambda x: x.stat().st_mtime, reverse=True)
    return {
        "screenshots": [
            {"name": f.name, "size": f.stat().st_size, "path": f"/screenshots/{f.name}"}
            for f in files[:50]
        ]
    }


@router.get("/screenshot/{filename}")
async def get_screenshot(filename: str):
    """获取单张截图"""
    from fastapi.responses import FileResponse
    screenshot_path = Path(__file__).parent.parent.parent / "screenshots" / filename
    if not screenshot_path.exists():
        raise HTTPException(404, "Screenshot not found")
    return FileResponse(str(screenshot_path), media_type="image/png")


@router.get("/entries")
async def get_browser_entries():
    """获取浏览器测试入口定义"""
    return {"entries": {k: v for k, v in ENTRY_DEFS.items() 
                       if k in ("web_ui_test", "ai_test_generation")}}


@router.on_event("shutdown")
async def shutdown():
    await close_browser_executor()
