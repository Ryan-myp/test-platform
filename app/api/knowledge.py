"""知识库 API"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List
import json
from datetime import datetime, timezone

from app.database import get_db, _exec

router = APIRouter(prefix="/api/knowledge", tags=["知识库"])


class KnowledgeCreate(BaseModel):
    category: str
    title: str
    content: str
    tags: List[str] = []
    meta: dict = {}


class KnowledgeUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None


@router.get("")
async def list_knowledge(category: Optional[str] = None, tag: Optional[str] = None, session=Depends(get_db)):
    sql = "SELECT id, category, title, content, tags, meta, created_at FROM knowledge"
    params = {}
    cond = []
    if category:
        cond.append("category = :cat"); params["cat"] = category
    if tag:
        cond.append("tags LIKE '%' || :tag || '%'"); params["tag"] = tag
    if cond:
        sql += " WHERE " + " AND ".join(cond)
    sql += " ORDER BY created_at DESC"
    result = await _exec(session, sql, params)
    rows = result.fetchall()
    return {"data": [{"id": r[0], "category": r[1], "title": r[2], "content": r[3],
                       "tags": json.loads(r[4] or "[]"), "meta": json.loads(r[5] or "{}"),
                       "created_at": r[6]} for r in rows], "total": len(rows)}


@router.post("")
async def create_knowledge(item: KnowledgeCreate, session=Depends(get_db)):
    now = datetime.now(timezone.utc).isoformat()
    logger = __import__("loguru").logger
    try:
        await _exec(session,
        "INSERT INTO knowledge (category, title, content, tags, meta, created_at) VALUES (:cat,:title,:content,:tags,:meta,:now)",
        {"cat": item.category, "title": item.title, "content": item.content,
         "tags": json.dumps(item.tags, ensure_ascii=False),
         "meta": json.dumps(item.meta, ensure_ascii=False), "now": now})
        return {"message": "Knowledge created"}
    except Exception as e:
        logger.error(f"CREATE_KNOWLEDGE_ERROR: {{e}}")
        raise


@router.put("/{item_id}")
async def update_knowledge(item_id: int, item: KnowledgeUpdate, session=Depends(get_db)):
    fields, params = [], {"id": item_id}
    if item.title: fields.append("title=:title"); params["title"] = item.title
    if item.content: fields.append("content=:content"); params["content"] = item.content
    if item.tags is not None: fields.append("tags=:tags"); params["tags"] = json.dumps(item.tags, ensure_ascii=False)
    if not fields: raise HTTPException(400, "No fields")
    from fastapi import HTTPException
    await _exec(session, f"UPDATE knowledge SET {', '.join(fields)} WHERE id=:id", params)
    return {"message": "Updated"}


@router.delete("/{item_id}")
async def delete_knowledge(item_id: int, session=Depends(get_db)):
    await _exec(session, "DELETE FROM knowledge WHERE id=:id", {"id": item_id})
    return {"message": "Deleted"}


@router.get("/search")
async def search_knowledge(keyword: str, session=Depends(get_db)):
    result = await _exec(session,
        "SELECT id, category, title, content FROM knowledge WHERE title LIKE :kw OR content LIKE :kw LIMIT 20",
        {"kw": f"%{keyword}%"})
    return {"data": [{"id": r[0], "category": r[1], "title": r[2], "content": r[3][:200]} for r in result.fetchall()]}


@router.get("/stats")
async def knowledge_stats(session=Depends(get_db)):
    result = await _exec(session, "SELECT category, COUNT(*) FROM knowledge GROUP BY category")
    return {row[0]: row[1] for row in result.fetchall()}
