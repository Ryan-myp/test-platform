"""配置 API"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
import json

from app.database import get_db, _exec
from app.config import settings

router = APIRouter(prefix="/api/config", tags=["配置"])


class ConfigUpdate(BaseModel):
    ai_model: Optional[str] = None
    ai_api_key: Optional[str] = None
    ai_base_url: Optional[str] = None
    kibana_base_url: Optional[str] = None
    kibana_api_key: Optional[str] = None
    jira_base_url: Optional[str] = None
    jira_token: Optional[str] = None
    webhook_url: Optional[str] = None


@router.get("")
async def get_config():
    return {
        "ai_model": settings.ai_model,
        "has_ai_key": bool(settings.ai_api_key),
        "has_kibana": bool(settings.kibana_base_url),
        "has_jira": bool(settings.jira_base_url),
        "has_webhook": bool(settings.webhook_url),
        "version": settings.version
    }


@router.put("")
async def update_config(cfg: ConfigUpdate, session=Depends(get_db)):
    updates = {}
    if cfg.ai_model:
        updates["ai_model"] = cfg.ai_model
    if cfg.ai_api_key:
        updates["ai_api_key"] = cfg.ai_api_key
    if cfg.ai_base_url:
        updates["ai_base_url"] = cfg.ai_base_url
    if cfg.kibana_base_url:
        updates["kibana_base_url"] = cfg.kibana_base_url
    if cfg.kibana_api_key:
        updates["kibana_api_key"] = cfg.kibana_api_key
    if cfg.jira_base_url:
        updates["jira_base_url"] = cfg.jira_base_url
    if cfg.jira_token:
        updates["jira_token"] = cfg.jira_token
    if cfg.webhook_url:
        updates["webhook_url"] = cfg.webhook_url

    if updates:
        # 持久化到 configs 表
        for key, value in updates.items():
            await _exec(session, """
                INSERT INTO configs (key, value) VALUES (:key, :val)
                ON CONFLICT(key) DO UPDATE SET value = :val
            """, {"key": f"setting.{key}", "val": value})

    return {"message": "Config updated", "config": updates}
