"""任务执行 API — 六大入口 + 自动化执行 + 多入口联动"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, Any, List
import json
import asyncio
from datetime import datetime, timezone

from app.database import get_db, _exec, AsyncSessionLocal
from app.ai import call_ai
from app.executor import ApiTestExecutor, SqlExecutor, TestCaseExecutor, KibanaAdapter, JiraAdapter, Notifier
from app.entries import ENTRY_DEFS, PIPELINE_TEMPLATES
from app.config import settings

router = APIRouter(prefix="/api/tasks", tags=["任务执行"])


class TaskInput(BaseModel):
    entry_type: str
    title: str
    data: dict[str, Any]
    auto_exec: bool = True  # 是否执行自动化测试


class PipelineInput(BaseModel):
    template: str  # bug_investigation / sql_optimization / release_check / custom
    custom_steps: Optional[List[dict]] = None  # 自定义步骤
    inputs: dict[str, dict] = {}  # 每个步骤的输入数据


@router.get("/entries")
async def list_entries():
    return {"entries": ENTRY_DEFS}


@router.get("")
async def list_tasks(
    entry_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    session=Depends(get_db)
):
    sql = "SELECT id, entry_type, title, input_data, ai_output, auto_exec_result, status, linked_task_ids, created_at, completed_at FROM task_executions"
    params = {}
    conditions = []
    if entry_type:
        conditions.append("entry_type = :etype")
        params["etype"] = entry_type
    if status:
        conditions.append("status = :status")
        params["status"] = status
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += f" ORDER BY created_at DESC LIMIT {limit}"
    result = await _exec(session, sql, params)
    rows = result.fetchall()
    return {
        "data": [{
            "id": r[0], "entry_type": r[1], "title": r[2],
            "status": r[6], "created_at": r[8], "completed_at": r[9],
            "auto_exec_result": json.loads(r[5] or "{}")
        } for r in rows],
        "total": len(rows)
    }


@router.post("")
async def create_task(task: TaskInput, session=Depends(get_db)):
    """创建任务并执行（AI + 可选自动化）"""
    if task.entry_type not in ENTRY_DEFS:
        raise HTTPException(400, f"Unknown entry type: {task.entry_type}")

    now = datetime.now(timezone.utc).isoformat()
    await _exec(session, """
        INSERT INTO task_executions (entry_type, title, input_data, ai_output, auto_exec_result, status, created_at)
        VALUES (:etype, :title, :input, '', '{}', 'running', :now)
    """, {"etype": task.entry_type, "title": task.title,
          "input": json.dumps(task.data, ensure_ascii=False), "now": now})

    # 获取新任务 ID
    async with AsyncSessionLocal() as s:
        from sqlalchemy import text as sa_text
        r = await s.execute(sa_text("SELECT last_insert_rowid()"))
        task_id = r.scalar()

    try:
        # 1. AI 生成输出
        ai_result = await call_ai(task.entry_type, task.data)

        # 2. 自动化执行（如果启用）
        auto_result = {}
        if task.auto_exec:
            auto_result = await _run_auto_execution(
                task.entry_type, task.data, task_id, session
            )

        # 3. 更新任务
        now = datetime.now(timezone.utc).isoformat()
        await _exec(session, """
            UPDATE task_executions
            SET ai_output = :ai_out, auto_exec_result = :auto_res,
                status = :status, completed_at = :now
            WHERE id = :id
        """, {
            "id": task_id,
            "ai_out": ai_result.get("output", ""),
            "auto_res": json.dumps(auto_result, ensure_ascii=False),
            "status": ai_result.get("status", "failed"),
            "now": now
        })

        return {
            "task_id": task_id,
            "ai_output": ai_result.get("output", ""),
            "auto_exec_result": auto_result,
            "status": ai_result.get("status", "failed")
        }

    except Exception as e:
        now = datetime.now(timezone.utc).isoformat()
        await _exec(session, """
            UPDATE task_executions SET status = 'failed', completed_at = :now
            WHERE id = :id
        """, {"id": task_id, "now": now})
        raise HTTPException(500, str(e))


async def _run_auto_execution(entry_type: str, data: dict, task_id: int, session) -> dict:
    """根据入口类型执行相应的自动化测试"""
    executor = ENTRY_DEFS.get(entry_type, {}).get("auto_execute")
    if not executor:
        return {}

    result = {}
    etype = executor["type"]

    if etype == "api_test":
        result = await _run_api_tests(data, task_id)
    elif etype == "sql_exec":
        result = await _run_sql_exec(data, task_id, session)
    elif etype == "kibana_search":
        result = await _run_kibana_search(data)
    elif etype == "browser_test":
        result = await _run_browser_tests(data, task_id)
    elif etype == "ai_browser_test":
        result = await _run_ai_browser_tests(data, task_id)

    return result


async def _run_api_tests(data: dict, task_id: int) -> dict:
    """执行 API 自动化测试"""
    executor = ApiTestExecutor()
    # 从数据中提取测试请求
    url = data.get("test_url") or data.get("url")
    if not url:
        return {"note": "未提供 test_url，跳过自动化测试"}

    method = data.get("method", "GET")
    headers = data.get("headers", {})
    body = data.get("body")
    expected_status = data.get("expected_status", 200)
    assert_json = data.get("assert_json")

    test_result = await executor.execute(
        task_id=task_id, url=url, method=method,
        headers=headers, body=body,
        expected_status=expected_status, assert_json=assert_json
    )
    return {"api_test": test_result}


async def _run_sql_exec(data: dict, task_id: int, session) -> dict:
    """执行 SQL 查询"""
    sql = data.get("sql", "")
    if not sql:
        return {"note": "未提供 SQL，跳过执行"}

    executor = SqlExecutor()
    db_url = data.get("db_url", settings.database_url.replace("sqlite+aiosqlite://", "sqlite://"))
    result = await executor.execute(task_id, sql, db_url)
    return {"sql_exec": result}


async def _run_kibana_search(data: dict) -> dict:
    """查询 Kibana 日志"""
    adapter = KibanaAdapter(settings.kibana_base_url, settings.kibana_api_key)
    query = data.get("log_snippet", "") or data.get("description", "")
    time_range = data.get("time_range", "last_15_minutes")
    logs = await adapter.search_logs(query, time_range)
    return {"kibana_logs": logs[:5]}  # 返回前5条


@router.get("/{task_id}")
async def get_task(task_id: int, session=Depends(get_db)):
    result = await _exec(session, "SELECT * FROM task_executions WHERE id = :id", {"id": task_id})
    row = result.fetchone()
    if not row:
        raise HTTPException(404, "Task not found")
    return {
        "id": row[0], "entry_type": row[1], "title": row[2],
        "input_data": json.loads(row[3]), "ai_output": row[4],
        "auto_exec_result": json.loads(row[5] or "{}"),
        "status": row[6], "linked_task_ids": json.loads(row[7] or "[]"),
        "created_at": row[8], "completed_at": row[9]
    }


@router.delete("/{task_id}")
async def delete_task(task_id: int, session=Depends(get_db)):
    await _exec(session, "DELETE FROM task_executions WHERE id = :id", {"id": task_id})
    return {"message": "Deleted"}


# ── 联动流水线 ─────────────────────────────────────────────

@router.post("/pipeline")
async def create_pipeline(pipeline: PipelineInput, session=Depends(get_db)):
    """创建并执行联动流水线"""
    if pipeline.template == "custom" and not pipeline.custom_steps:
        raise HTTPException(400, "Custom pipeline requires steps")

    template = pipeline.template
    if template != "custom" and template not in PIPELINE_TEMPLATES:
        raise HTTPException(400, f"Unknown pipeline template: {template}")

    # 构建步骤
    if template != "custom":
        steps_def = PIPELINE_TEMPLATES[template]["steps"]
        steps = []
        for i, step in enumerate(steps_def):
            step_input = pipeline.inputs.get(step["entry_type"], {})
            steps.append({
                "step_number": i + 1,
                "entry_type": step["entry_type"],
                "description": step["desc"],
                "input_data": step_input
            })
    else:
        steps = pipeline.custom_steps or []

    now = datetime.now(timezone.utc).isoformat()
    await _exec(session, """
        INSERT INTO pipelines (name, steps, status, current_step, results, triggered_by, created_at)
        VALUES (:name, :steps, 'running', 0, '{}', '', :now)
    """, {"name": PIPELINE_TEMPLATES.get(template, {}).get("name", "Custom Pipeline"),
          "steps": json.dumps(steps, ensure_ascii=False), "now": now})

    async with AsyncSessionLocal() as s:
        from sqlalchemy import text as sa_text
        r = await s.execute(sa_text("SELECT last_insert_rowid()"))
        pipeline_id = r.scalar()

    # 执行流水线
    results = {}
    for step in steps:
        step_result = await _exec_pipeline_step(step, pipeline_id, session)
        results[step["step_number"]] = step_result

    # 更新流水线状态
    await _exec(session, """
        UPDATE pipelines SET status = 'completed', results = :results,
            completed_at = :now WHERE id = :id
    """, {"id": pipeline_id, "results": json.dumps(results, ensure_ascii=False),
          "now": datetime.now(timezone.utc).isoformat()})

    return {"pipeline_id": pipeline_id, "steps": len(steps), "results": results}


async def _exec_pipeline_step(step: dict, pipeline_id: int, session) -> dict:
    """执行流水线中的一个步骤"""
    entry_type = step["entry_type"]
    input_data = step.get("input_data", {})
    description = step.get("description", "")

    # 调用 AI
    ai_result = await call_ai(entry_type, input_data)

    # 记录任务
    now = datetime.now(timezone.utc).isoformat()
    await _exec(session, """
        INSERT INTO task_executions (entry_type, title, input_data, ai_output, auto_exec_result, status, created_at)
        VALUES (:etype, :title, :input, :ai_out, '{}', :status, :now)
    """, {
        "etype": entry_type, "title": f"Pipeline Step: {description}",
        "input": json.dumps(input_data, ensure_ascii=False),
        "ai_out": ai_result.get("output", ""),
        "status": ai_result.get("status", "failed"),
        "now": now
    })

    async with AsyncSessionLocal() as s:
        from sqlalchemy import text as sa_text
        r = await s.execute(sa_text("SELECT last_insert_rowid()"))
        task_id = r.scalar()

    # 可能的自动化执行
    auto_result = {}
    if ENTRY_DEFS.get(entry_type, {}).get("auto_execute"):
        auto_result = await _run_auto_execution(entry_type, input_data, task_id, session)

    return {
        "task_id": task_id,
        "ai_output": ai_result.get("output", ""),
        "auto_exec_result": auto_result
    }


@router.get("/pipeline/{pipeline_id}")
async def get_pipeline(pipeline_id: int, session=Depends(get_db)):
    result = await _exec(session, "SELECT * FROM pipelines WHERE id = :id", {"id": pipeline_id})
    row = result.fetchone()
    if not row:
        raise HTTPException(404, "Pipeline not found")
    return {
        "id": row[0], "name": row[1],
        "steps": json.loads(row[2] or "[]"),
        "status": row[3], "current_step": row[4],
        "results": json.loads(row[5] or "{}"),
        "created_at": row[6], "completed_at": row[7]
    }


@router.get("/pipeline")
async def list_pipelines(session=Depends(get_db), limit: int = 20):
    result = await _exec(session,
        "SELECT id, name, status, results, created_at FROM pipelines ORDER BY created_at DESC LIMIT :limit",
        {"limit": limit})
    rows = result.fetchall()
    return {
        "data": [{"id": r[0], "name": r[1], "status": r[2],
                  "results_count": len(json.loads(r[3] or "{}")),
                  "created_at": r[4]} for r in rows],
        "total": len(rows)
    }


@router.get("/templates")
async def get_pipeline_templates():
    return {"templates": PIPELINE_TEMPLATES}

async def _run_browser_tests(data: dict, task_id: int) -> dict:
    """执行浏览器自动化测试"""
    try:
        from app.executor import run_browser_test
        return await run_browser_test(task_id, data)
    except Exception as e:
        logger.opt(exception=True).error(f"浏览器测试执行失败: {e}")
        return {"error": str(e)}


async def _run_ai_browser_tests(data: dict, task_id: int) -> dict:
    """AI 生成用例 + 浏览器执行"""
    try:
        from app.executor import run_ai_browser_test
        return await run_ai_browser_test(task_id, data)
    except Exception as e:
        logger.opt(exception=True).error(f"AI浏览器测试执行失败: {e}")
        return {"error": str(e)}
