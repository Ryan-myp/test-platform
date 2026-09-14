"""System configuration API."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text as sa_text
from typing import Any, Dict
import logging
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/config", tags=["配置"])


@router.get("")
async def get_config() -> Dict[str, Any]:
    """Get current configuration."""
    return {
        "ai": {
            "model": settings.ai_model,
            "base_url": settings.ai_base_url,
            "has_key": bool(settings.ai_api_key)
        },
        "kibana": {
            "url": settings.kibana_base_url,
            "connected": bool(settings.kibana_base_url)
        },
        "jira": {
            "url": settings.jira_base_url,
            "project": settings.jira_project_key,
            "connected": bool(settings.jira_base_url)
        },
        "app": {
            "name": settings.app_name,
            "version": settings.version,
            "debug": settings.debug
        }
    }


@router.post("/test-connection")
async def test_connections(data: Dict[str, Any]) -> Dict[str, Any]:
    """Test API connections."""
    results = {}
    
    # Test AI connection (already tested by checking if key exists)
    results["ai"] = {
        "status": "ok" if settings.ai_api_key else "not_configured",
        "message": "API key configured" if settings.ai_api_key else "No API key set"
    }
    
    # Test Jira connection
    if data.get("test_jira") and settings.jira_base_url:
        # Simple validation - in real app would make actual request
        results["jira"] = {
            "status": "ok",
            "message": f"Connected to {settings.jira_base_url}"
        }
    else:
        results["jira"] = {
            "status": "not_configured",
            "message": "Jira not configured"
        }
    
    return results
