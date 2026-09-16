"""Task execution history API."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text as sa_text
from typing import Any, Dict, List, Optional
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tasks", tags=["任务执行"])


async def get_db():
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session



@router.post("")
async def create_task(data: Dict[str, Any], session=Depends(get_db)) -> Dict[str, Any]:
    """Create a new task."""
    try:
        entry_type = data.get("entry_type", "manual")
        title = data.get("title", "未命名任务")
        input_data = data.get("input_data", {})
        
        now = datetime.now().isoformat()
        
        # 调用 AI 生成输出
        from app.ai import call_ai
        ai_result = await call_ai(entry_type, input_data)
        
        # 保存任务
        await session.execute(sa_text(
            "INSERT INTO task_executions (entry_type, title, status, input_data, ai_output, created_at) "
            "VALUES (:entry_type, :title, :status, :input_data, :ai_output, :created_at)"
        ), {
            "entry_type": entry_type,
            "title": title,
            "status": ai_result.get("status", "success"),
            "input_data": json.dumps(input_data, ensure_ascii=False),
            "ai_output": ai_result.get("output", ""),
            "created_at": now
        })
        await session.commit()
        
        # 获取 ID
        r = await session.execute(sa_text("SELECT last_insert_rowid()"))
        task_id = r.scalar()
        
        return {
            "id": task_id,
            "entry_type": entry_type,
            "title": title,
            "status": ai_result.get("status", "success"),
            "output": ai_result.get("output", "")
        }
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates")
async def get_templates() -> Dict[str, Any]:
    """Get task templates."""
    return {
        "templates": {
            "generate_cases": {
                "name": "生成测试用例",
                "desc": "根据需求描述自动生成测试用例",
                "prompt": "请为以下需求生成测试用例：\\n\\n{requirement}",
                "fields": ["requirement", "module"]
            },
            "analyze_bug": {
                "name": "分析Bug根因",
                "desc": "分析缺陷描述，定位根因并给出修复建议",
                "prompt": "请分析以下 Bug 并定位根因：\\n\\n{description}",
                "fields": ["description", "reproduction_steps"]
            }
        }
    }


@router.get("")
async def list_tasks(
    entry_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session=Depends(get_db)
) -> Dict[str, Any]:
    """List task executions with filtering."""
    try:
        conditions = []
        params = {"limit": limit, "offset": offset}
        
        if entry_type:
            conditions.append("entry_type = :entry_type")
            params["entry_type"] = entry_type
        if status:
            conditions.append("status = :status")
            params["status"] = status
        
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        # Get total count
        count_sql = f"SELECT COUNT(*) FROM task_executions {where}"
        r = await session.execute(sa_text(count_sql), params)
        total = r.scalar() or 0
        
        # Get tasks
        sql = f"""SELECT id, entry_type, title, input_data, ai_output, 
                  status, error, duration_ms, 
                  created_at, completed_at
                  FROM task_executions {where}
                  ORDER BY id DESC LIMIT :limit OFFSET :offset"""
        
        r = await session.execute(sa_text(sql), params)
        rows = r.fetchall()
        
        tasks = []
        for row in rows:
            tasks.append({
                "id": row[0],
                "entry_type": row[1] or "",
                "title": row[2] or "",
                "input_data": json.loads(row[3] or "{}"),
                "ai_output": row[4] or "",
                "auto_exec_result": {},
                "status": row[5] or "pending",
                "error": row[6] or "",
                "duration_ms": row[7] or 0,
                "created_at": row[8],
                "completed_at": row[9]
            })
        
        return {
            "items": tasks,
            "total": total,
            "limit": limit,
            "offset": offset,
            "pages": (total + limit - 1) // limit
        }
    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        return {"items": [], "total": 0, "limit": limit, "offset": offset, "pages": 0}



@router.get("/pipeline")
async def list_pipelines(session=Depends(get_db)) -> Dict[str, Any]:
    """List pipeline executions."""
    try:
        r = await session.execute(sa_text("SELECT * FROM task_executions WHERE entry_type = 'pipeline' ORDER BY id DESC LIMIT 20"))
        rows = r.fetchall()
        
        pipelines = []
        for row in rows:
            pipelines.append({
                "id": row[0],
                "name": row[2] or "",
                "steps": row[5] or "[]",
                "status": row[6] or "pending",
                "current_step": 0,
                "created_at": row[9]
            })
        
        return {"data": pipelines, "total": len(pipelines)}
    except Exception as e:
        logger.error(f"Failed to list pipelines: {e}")
        return {"data": [], "total": 0}




@router.post("/pipeline/{key}")
async def run_pipeline(key: str, session=Depends(get_db)) -> Dict[str, Any]:
    """Run a pipeline template."""
    # Get templates
    templates = {
        "generate_cases": {"name": "生成测试用例", "desc": "根据需求描述自动生成测试用例"},
        "analyze_bug": {"name": "分析Bug根因", "desc": "分析缺陷描述，定位根因并给出修复建议"}
    }
    
    if key not in templates:
        raise HTTPException(status_code=404, detail=f"Template '{key}' not found")
    
    template = templates[key]
    
    # Create a task execution record
    now = datetime.now().isoformat()
    import json
    steps = json.dumps([{"name": template['name'], "desc": template['desc']}, {"name": "执行中", "desc": "准备执行"}], ensure_ascii=False)
    
    await session.execute(sa_text(
        "INSERT INTO task_executions (entry_type, title, status, input_data, ai_output, steps, created_at) "
        "VALUES (:entry_type, :title, :status, :input_data, :ai_output, :steps, :created_at)"
    ), {
        "entry_type": "pipeline",
        "title": f"流水线: {template['name']}",
        "status": "running",
        "input_data": f'{{"key": "{key}"}}',
        "ai_output": f"流水线已启动: {template['name']}",
        "steps": steps,
        "created_at": now
    })
    await session.commit()
    
    return {
        "pipeline_id": f"pipeline_{key}_{int(datetime.now().timestamp())}",
        "name": template["name"],
        "desc": template["desc"],
        "status": "started"
    }


@router.get("/{task_id}")
async def get_task(task_id: int, session=Depends(get_db)):
    """Get a specific task execution."""
    try:
        r = await session.execute(
            sa_text("SELECT * FROM task_executions WHERE id = :id"),
            {"id": task_id}
        )
        row = r.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return {
            "id": row[0],
            "entry_type": row[1] or "",
            "title": row[2] or "",
            "input_data": json.loads(row[3] or "{}"),
            "ai_output": row[4] or "",
            "auto_exec_result": {},
            "status": row[5] or "pending",
            "error": row[6] or "",
            "duration_ms": row[7] or 0,
            "created_at": row[8],
            "completed_at": row[9]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{task_id}")
async def delete_task(task_id: int, session=Depends(get_db)):
    """Delete a task execution record."""
    try:
        r = await session.execute(
            sa_text("SELECT id FROM task_executions WHERE id = :id"),
            {"id": task_id}
        )
        if not r.fetchone():
            raise HTTPException(status_code=404, detail="Task not found")
        
        await session.execute(
            sa_text("DELETE FROM task_executions WHERE id = :id"),
            {"id": task_id}
        )
        await session.commit()
        
        return {"message": "Task deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear")
async def clear_tasks(session=Depends(get_db)):
    """Clear all task execution records."""
    try:
        await session.execute(sa_text("DELETE FROM task_executions"))
        await session.commit()
        return {"message": "All tasks cleared"}
    except Exception as e:
        logger.error(f"Failed to clear tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary")
async def task_stats(session=Depends(get_db)) -> Dict[str, Any]:
    """Get task execution statistics."""
    try:
        r = await session.execute(sa_text("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as success,
                SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN status='running' THEN 1 ELSE 0 END) as running,
                AVG(duration_ms) as avg_duration_ms
            FROM task_executions
            WHERE created_at >= datetime('now', '-7 days')
        """))
        row = r.fetchone()
        
        return {
            "total": row[0] or 0,
            "success": row[1] or 0,
            "failed": row[2] or 0,
            "running": row[3] or 0,
            "avg_duration_ms": round(row[4] or 0, 2),
            "success_rate": f"{((row[1] or 0) / (row[0] or 1) * 100):.1f}%"
        }
    except Exception as e:
        logger.error(f"Failed to get task stats: {e}")
        return {
            "total": 0,
            "success": 0,
            "failed": 0,
            "running": 0,
            "avg_duration_ms": 0,
            "success_rate": "0%"
        }


@router.get("/stats/by_type")
async def task_stats_by_type(session=Depends(get_db)) -> List[Dict[str, Any]]:
    """Get task statistics by entry type."""
    try:
        r = await session.execute(sa_text("""
            SELECT 
                entry_type,
                COUNT(*) as total,
                SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as success,
                SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed
            FROM task_executions
            GROUP BY entry_type
            ORDER BY total DESC
        """))
        rows = r.fetchall()
        
        return [
            {
                "type": row[0],
                "total": row[1] or 0,
                "success": row[2] or 0,
                "failed": row[3] or 0
            }
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Failed to get task stats by type: {e}")
        return []
