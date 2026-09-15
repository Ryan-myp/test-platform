"""Knowledge base API."""
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy import text as sa_text
from typing import Any, Dict, List, Optional
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/knowledge", tags=["知识库"])


async def get_db():
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/stats/summary")
async def knowledge_stats(session=Depends(get_db)) -> Dict[str, Any]:
    """Get knowledge base statistics."""
    try:
        r = await session.execute(sa_text("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN type='case' THEN 1 ELSE 0 END) as cases,
                SUM(CASE WHEN type='bug' THEN 1 ELSE 0 END) as bugs,
                SUM(CASE WHEN type='spec' THEN 1 ELSE 0 END) as specs
            FROM knowledge
        """))
        row = r.fetchone()
        
        return {
            "total": row[0] or 0,
            "cases": row[1] or 0,
            "bugs": row[2] or 0,
            "specs": row[3] or 0
        }
    except Exception as e:
        logger.error(f"Failed to get knowledge stats: {e}")
        return {"total": 0, "cases": 0, "bugs": 0, "specs": 0}


@router.get("")
async def list_knowledge(
    type_filter: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    session=Depends(get_db)
) -> Dict[str, Any]:
    """List knowledge items."""
    try:
        where = "WHERE type = :type" if type_filter else ""
        r = await session.execute(sa_text(f"""
            SELECT * FROM knowledge {where}
            ORDER BY created_at DESC LIMIT :limit
        """), {"type": type_filter, "limit": limit})
        rows = r.fetchall()
        
        items = []
        for row in rows:
            items.append({
                "id": row[0],
                "type": row[1] or "",
                "title": row[2] or "",
                "content": row[3] or "",
                "tags": json.loads(row[4] or "[]"),
                "created_at": row[5]
            })
        
        return {"items": items, "total": len(items)}
    except Exception as e:
        logger.error(f"Failed to list knowledge: {e}")
        return {"items": [], "total": 0}


@router.post("")
async def create_knowledge(data: Dict[str, Any], session=Depends(get_db)):
    """Create knowledge item."""
    try:
        r = await session.execute(sa_text("""
            INSERT INTO knowledge (type, title, content, tags)
            VALUES (:type, :title, :content, :tags)
        """), {
            "type": data.get("type", "case"),
            "title": data.get("title", ""),
            "content": data.get("content", ""),
            "tags": json.dumps(data.get("tags", []), ensure_ascii=False)
        })
        await session.commit()
        
        return {"id": r.lastrowid, "message": "Knowledge created"}
    except Exception as e:
        logger.error(f"Failed to create knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{item_id}")
async def get_knowledge(item_id: int, session=Depends(get_db)):
    """Get knowledge item."""
    try:
        r = await session.execute(sa_text("SELECT * FROM knowledge WHERE id = :id"), {"id": item_id})
        row = r.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Knowledge not found")
        
        return {
            "id": row[0],
            "type": row[1] or "",
            "title": row[2] or "",
            "content": row[3] or "",
            "tags": json.loads(row[4] or "[]"),
            "created_at": row[5]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{item_id}")
async def update_knowledge(item_id: int, data: Dict[str, Any], session=Depends(get_db)):
    """Update knowledge item."""
    try:
        r = await session.execute(sa_text("SELECT id FROM knowledge WHERE id = :id"), {"id": item_id})
        if not r.fetchone():
            raise HTTPException(status_code=404, detail="Knowledge not found")
        
        await session.execute(sa_text("""
            UPDATE knowledge 
            SET title=:title, content=:content, tags=:tags, type=:type
            WHERE id = :id
        """), {
            "id": item_id,
            "type": data.get("type", "case"),
            "title": data.get("title", ""),
            "content": data.get("content", ""),
            "tags": json.dumps(data.get("tags", []), ensure_ascii=False)
        })
        await session.commit()
        
        return {"message": "Knowledge updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{item_id}")
async def delete_knowledge(item_id: int, session=Depends(get_db)):
    """Delete knowledge item."""
    try:
        r = await session.execute(sa_text("SELECT id FROM knowledge WHERE id = :id"), {"id": item_id})
        if not r.fetchone():
            raise HTTPException(status_code=404, detail="Knowledge not found")
        
        await session.execute(sa_text("DELETE FROM knowledge WHERE id = :id"), {"id": item_id})
        await session.commit()
        
        return {"message": "Knowledge deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e))
