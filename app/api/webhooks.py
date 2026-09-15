"""Webhook management API."""
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy import text as sa_text
from typing import Any, Dict, List, Optional
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webhooks", tags=["Webhook"])

async def get_db():
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session


@router.get("")
async def list_webhooks(session=Depends(get_db)) -> Dict[str, Any]:
    """List webhooks."""
    try:
        r = await session.execute(sa_text("SELECT rowid, * FROM configs WHERE category = 'webhook' ORDER BY rowid"))
        rows = r.fetchall()
        
        webhooks = []
        for row in rows:
            try:
                config = json.loads(row[1] or "{}")
            except:
                config = {}
            webhooks.append({
                "id": row[1],
                "key": row[2],
                "name": config.get("name", ""),
                "url": config.get("url", ""),
                "events": config.get("events", []),
                "secret": config.get("secret", "")[:8] + "..." if config.get("secret") else "",
                "active": config.get("active", True),
                "created_at": row[3]
            })
        
        return {"webhooks": webhooks, "total": len(webhooks)}
    except Exception as e:
        logger.error(f"Failed to list webhooks: {e}")
        return {"webhooks": [], "total": 0}


@router.post("")
async def create_webhook(data: Dict[str, Any], session=Depends(get_db)):
    """Create webhook."""
    try:
        now = datetime.now().isoformat()
        config = {
            "name": data.get("name", "未命名Webhook"),
            "url": data.get("url", ""),
            "events": data.get("events", ["test.completed"]),
            "secret": data.get("secret", ""),
            "active": data.get("active", True)
        }
        
        key = f"webhook_{int(datetime.now().timestamp())}"
        await session.execute(sa_text("""
            INSERT INTO configs (key, value, category, description, updated_at)
            VALUES (:key, :value, :category, :description, :updated_at)
        """), {
            "key": key,
            "value": json.dumps(config, ensure_ascii=False),
            "category": "webhook",
            "description": config["name"],
            "updated_at": now
        })
        await session.commit()
        
        return {"key": key, "message": "Webhook created"}
    except Exception as e:
        logger.error(f"Failed to create webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{key}")
async def delete_webhook(key: str, session=Depends(get_db)):
    """Delete webhook."""
    try:
        await session.execute(sa_text("DELETE FROM configs WHERE key = :key AND category = 'webhook'"), {"key": key})
        await session.commit()
        
        return {"message": "Webhook deleted"}
    except Exception as e:
        logger.error(f"Failed to delete webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
