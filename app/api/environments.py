"""Environment management API."""
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy import text as sa_text
from typing import Any, Dict, List, Optional
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/environments", tags=["环境管理"])

async def get_db():
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session


@router.get("")
async def list_environments(
    type_filter: Optional[str] = Query(None),
    session=Depends(get_db)
) -> Dict[str, Any]:
    """List environments."""
    try:
        where = "WHERE type = :type" if type_filter else ""
        params = {"type": type_filter} if type_filter else {}
        
        r = await session.execute(sa_text(f"SELECT * FROM environments {where} ORDER BY id"), params)
        rows = r.fetchall()
        
        envs = []
        for row in rows:
            envs.append({
                "id": row[0],
                "name": row[1] or "",
                "base_url": row[2] or "",
                "type": row[3] or "dev",
                "config": json.loads(row[4] or "{}") if row[4] else {},
                "status": row[5] or "active",
                "owner": row[6] or "",
                "created_at": row[7],
                "updated_at": row[8]
            })
        
        return {"environments": envs, "total": len(envs)}
    except Exception as e:
        logger.error(f"Failed to list environments: {e}")
        return {"environments": [], "total": 0}


@router.post("")
async def create_environment(data: Dict[str, Any], session=Depends(get_db)):
    """Create environment."""
    try:
        now = datetime.now().isoformat()
        r = await session.execute(sa_text("""
            INSERT INTO environments (name, base_url, type, config, status, owner, created_at, updated_at)
            VALUES (:name, :base_url, :type, :config, :status, :owner, :created_at, :updated_at)
        """), {
            "name": data.get("name", "未命名环境"),
            "base_url": data.get("base_url", ""),
            "type": data.get("type", "dev"),
            "config": json.dumps(data.get("config", {}), ensure_ascii=False),
            "status": data.get("status", "active"),
            "owner": data.get("owner", ""),
            "created_at": now,
            "updated_at": now
        })
        await session.commit()
        
        return {"id": r.lastrowid, "message": "Environment created"}
    except Exception as e:
        logger.error(f"Failed to create environment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{env_id}")
async def update_environment(env_id: int, data: Dict[str, Any], session=Depends(get_db)):
    """Update environment."""
    try:
        r = await session.execute(sa_text("SELECT id FROM environments WHERE id = :id"), {"id": env_id})
        if not r.fetchone():
            raise HTTPException(status_code=404, detail="Environment not found")
        
        await session.execute(sa_text("""
            UPDATE environments SET
                name=:name, base_url=:base_url, type=:type,
                config=:config, status=:status, owner=:owner, updated_at=:updated_at
            WHERE id=:id
        """), {
            "id": env_id,
            "name": data.get("name", ""),
            "base_url": data.get("base_url", ""),
            "type": data.get("type", "dev"),
            "config": json.dumps(data.get("config", {}), ensure_ascii=False),
            "status": data.get("status", "active"),
            "owner": data.get("owner", ""),
            "updated_at": datetime.now().isoformat()
        })
        await session.commit()
        
        return {"message": "Environment updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update environment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{env_id}")
async def delete_environment(env_id: int, session=Depends(get_db)):
    """Delete environment."""
    try:
        r = await session.execute(sa_text("SELECT id FROM environments WHERE id = :id"), {"id": env_id})
        if not r.fetchone():
            raise HTTPException(status_code=404, detail="Environment not found")
        
        await session.execute(sa_text("DELETE FROM environments WHERE id = :id"), {"id": env_id})
        await session.commit()
        
        return {"message": "Environment deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete environment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-connection")
async def test_connection(data: Dict[str, Any], session=Depends(get_db)):
    """Test environment connection."""
    try:
        import httpx
        base_url = data.get("base_url", "")
        if not base_url:
            raise HTTPException(status_code=400, detail="base_url is required")
        
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(base_url.rstrip('/') + "/health", follow_redirects=True)
            return {
                "connected": resp.status_code < 500,
                "status_code": resp.status_code,
                "response_time_ms": resp.elapsed.total_seconds() * 1000
            }
    except httpx.ConnectError:
        return {"connected": False, "error": "Connection refused"}
    except Exception as e:
        return {"connected": False, "error": str(e)}
