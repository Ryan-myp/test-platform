"""Test data management API."""
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy import text as sa_text
from typing import Any, Dict, List, Optional
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/test-data", tags=["测试数据"])

async def get_db():
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session


@router.get("")
async def list_test_data(
    suite_id: Optional[int] = Query(None),
    type_filter: Optional[str] = Query(None),
    session=Depends(get_db)
) -> Dict[str, Any]:
    """List test data."""
    try:
        conditions = []
        params = {}
        
        if suite_id:
            conditions.append("suite_id = :suite_id")
            params["suite_id"] = suite_id
        if type_filter:
            conditions.append("type = :type")
            params["type"] = type_filter
        
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        r = await session.execute(sa_text(f"SELECT * FROM test_data {where} ORDER BY id DESC"), params)
        rows = r.fetchall()
        
        items = []
        for row in rows:
            items.append({
                "id": row[0],
                "name": row[1] or "",
                "type": row[2] or "json",
                "suite_id": row[3],
                "data": json.loads(row[4] or "{}") if row[4] else {},
                "description": row[5] or "",
                "owner": row[6] or "",
                "created_at": row[7]
            })
        
        return {"items": items, "total": len(items)}
    except Exception as e:
        logger.error(f"Failed to list test data: {e}")
        return {"items": [], "total": 0}


@router.post("")
async def create_test_data(data: Dict[str, Any], session=Depends(get_db)):
    """Create test data."""
    try:
        now = datetime.now().isoformat()
        r = await session.execute(sa_text("""
            INSERT INTO test_data (name, type, suite_id, data, description, owner, created_at, updated_at)
            VALUES (:name, :type, :suite_id, :data, :description, :owner, :created_at, :updated_at)
        """), {
            "name": data.get("name", "未命名数据"),
            "type": data.get("type", "json"),
            "suite_id": data.get("suite_id"),
            "data": json.dumps(data.get("data", {}), ensure_ascii=False),
            "description": data.get("description", ""),
            "owner": data.get("owner", ""),
            "created_at": now,
            "updated_at": now
        })
        await session.commit()
        
        return {"id": r.lastrowid, "message": "Test data created"}
    except Exception as e:
        logger.error(f"Failed to create test data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{data_id}")
async def update_test_data(data_id: int, data: Dict[str, Any], session=Depends(get_db)):
    """Update test data."""
    try:
        r = await session.execute(sa_text("SELECT id FROM test_data WHERE id = :id"), {"id": data_id})
        if not r.fetchone():
            raise HTTPException(status_code=404, detail="Test data not found")
        
        await session.execute(sa_text("""
            UPDATE test_data SET
                name=:name, type=:type, suite_id=:suite_id,
                data=:data, description=:description, owner=:owner, updated_at=:updated_at
            WHERE id=:id
        """), {
            "id": data_id,
            "name": data.get("name", ""),
            "type": data.get("type", "json"),
            "suite_id": data.get("suite_id"),
            "data": json.dumps(data.get("data", {}), ensure_ascii=False),
            "description": data.get("description", ""),
            "owner": data.get("owner", ""),
            "updated_at": datetime.now().isoformat()
        })
        await session.commit()
        
        return {"message": "Test data updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update test data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{data_id}")
async def delete_test_data(data_id: int, session=Depends(get_db)):
    """Delete test data."""
    try:
        r = await session.execute(sa_text("SELECT id FROM test_data WHERE id = :id"), {"id": data_id})
        if not r.fetchone():
            raise HTTPException(status_code=404, detail="Test data not found")
        
        await session.execute(sa_text("DELETE FROM test_data WHERE id = :id"), {"id": data_id})
        await session.commit()
        
        return {"message": "Test data deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete test data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
