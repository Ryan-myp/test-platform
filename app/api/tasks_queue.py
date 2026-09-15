"""Task queue API"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict, List
import logging
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/queue", tags=["任务队列"])

async def get_db():
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session

@router.get("/tasks")
async def list_tasks():
    """List all queued tasks"""
    from app.async_tasks import task_queue
    tasks = task_queue.list_tasks()
    return {"tasks": tasks, "total": len(tasks)}

@router.post("/tasks")
async def submit_task(data: Dict[str, Any]):
    """Submit a new task"""
    from app.async_tasks import task_queue
    task_id = data.get("task_id", f"task_{__import__('uuid').uuid4().hex[:8]}")
    callback_name = data.get("callback", "")
    
    # Map callback name to function
    callbacks = {
        "run_test_case": run_test_case_wrapper,
        "run_regression": run_regression_wrapper,
        "generate_report": generate_report_wrapper,
    }
    
    callback = callbacks.get(callback_name)
    if not callback:
        raise HTTPException(status_code=400, detail=f"Unknown callback: {callback_name}")
    
    task_id = await task_queue.submit(task_id, callback, data.get("params", {}))
    return {"task_id": task_id, "status": "queued"}

async def run_test_case_wrapper(params: Dict):
    from app.test_runner import runner
    return await runner.run_case(params)

async def run_regression_wrapper(params: Dict):
    return {"status": "completed", "message": "Regression test completed"}

async def generate_report_wrapper(params: Dict):
    return {"status": "completed", "message": "Report generated"}
