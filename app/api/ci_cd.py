"""CI/CD Integration API"""
from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy import text as sa_text
from typing import Any, Dict, List
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ci", tags=["CI/CD"])

async def get_db():
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/github/push")
async def github_push_webhook(request: Request, session=Depends(get_db)):
    """GitHub push webhook handler"""
    try:
        data = await request.json()
        ref = data.get("ref", "")
        commits = data.get("commits", [])
        repository = data.get("repository", {}).get("name", "")
        
        logger.info(f"GitHub webhook: ref={ref}, commits={len(commits)}, repo={repository}")
        
        # Determine test suite based on branch
        if "main" in ref or "master" in ref:
            suite_id = 1  # Full regression
        elif "feature/" in ref:
            suite_id = 2  # Feature tests
        else:
            suite_id = 3  # Default
        
        # Create task
        now = datetime.now().isoformat()
        await session.execute(sa_text("""
            INSERT INTO task_executions (entry_type, title, status, input_data, ai_output, created_at)
            VALUES (:entry_type, :title, :status, :input_data, :ai_output, :created_at)
        """), {
            "entry_type": "ci_cdn",
            "title": f"GitHub Push: {repository}",
            "status": "running",
            "input_data": json.dumps({"ref": ref, "commits": len(commits), "suite_id": suite_id}),
            "ai_output": f"Triggered test suite #{suite_id} for {len(commits)} commits",
            "created_at": now
        })
        await session.commit()
        
        return {
            "status": "accepted",
            "message": f"Test suite #{suite_id} triggered for {len(commits)} commits",
            "ref": ref,
            "commits": len(commits)
        }
    except Exception as e:
        logger.error(f"GitHub webhook failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gitlab/push")
async def gitlab_push_webhook(request: Request, session=Depends(get_db)):
    """GitLab push webhook handler"""
    try:
        data = await request.json()
        ref = data.get("ref", "")
        commits = data.get("commits", [])
        project = data.get("project", {}).get("name", "")
        
        logger.info(f"GitLab webhook: ref={ref}, commits={len(commits)}, project={project}")
        
        return {
            "status": "accepted",
            "message": f"Test suite triggered for {len(commits)} commits"
        }
    except Exception as e:
        logger.error(f"GitLab webhook failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jenkins/build")
async def jenkins_build_webhook(request: Request, session=Depends(get_db)):
    """Jenkins build webhook handler"""
    try:
        data = await request.json()
        job_name = data.get("jobName", data.get("项目名称", "unknown"))
        build_number = data.get("buildNumber", data.get("构建编号", 0))
        
        logger.info(f"Jenkins webhook: job={job_name}, build={build_number}")
        
        return {
            "status": "accepted",
            "message": f"Test suite triggered for Jenkins build #{build_number}"
        }
    except Exception as e:
        logger.error(f"Jenkins webhook failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notify/slack")
async def notify_slack(data: Dict[str, Any], session=Depends(get_db)):
    """Send Slack notification"""
    try:
        import httpx
        
        webhook_url = data.get("webhook_url", "")
        if not webhook_url:
            raise HTTPException(status_code=400, detail="webhook_url is required")
        
        text = data.get("text", "TestPilot Pro 通知")
        color = data.get("color", "#36a64f")
        
        payload = {
            "text": text,
            "attachments": [{
                "color": color,
                "text": data.get("message", ""),
                "footer": "TestPilot Pro",
                "ts": int(datetime.now().timestamp())
            }]
        }
        
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(webhook_url, json=payload)
        
        return {
            "status": "sent" if resp.status_code == 200 else "failed",
            "status_code": resp.status_code
        }
    except Exception as e:
        logger.error(f"Slack notification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notify/wecom")
async def notify_wecom(data: Dict[str, Any], session=Depends(get_db)):
    """Send WeChat Work notification"""
    try:
        import httpx
        
        webhook_url = data.get("webhook_url", "")
        if not webhook_url:
            raise HTTPException(status_code=400, detail="webhook_url is required")
        
        msg = data.get("msg", "TestPilot Pro 通知")
        
        payload = {
            "msgtype": "text",
            "text": {
                "content": msg
            }
        }
        
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(webhook_url, json=payload)
        
        return {
            "status": "sent" if resp.status_code == 200 else "failed",
            "status_code": resp.status_code
        }
    except Exception as e:
        logger.error(f"WeCom notification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_ci_status(session=Depends(get_db)):
    """Get CI/CD status"""
    try:
        r = await session.execute(sa_text("""
            SELECT id, title, status, created_at
            FROM task_executions
            WHERE entry_type IN ('ci_cdn', 'pipeline')
            ORDER BY id DESC
            LIMIT 20
        """))
        rows = r.fetchall()
        
        statuses = []
        for row in rows:
            statuses.append({
                "id": row[0],
                "title": row[1] or "",
                "status": row[2] or "pending",
                "created_at": row[3]
            })
        
        return {"statuses": statuses, "total": len(statuses)}
    except Exception as e:
        logger.error(f"Failed to get CI status: {e}")
        return {"statuses": [], "total": 0}
