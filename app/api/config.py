"""System configuration API."""
from fastapi import APIRouter
from typing import Any, Dict
import logging
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/config", tags=["配置"])


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
            "project": getattr(settings, "jira_project", ""),
            "connected": bool(settings.jira_base_url)
        },
        "app": {
            "name": settings.app_name,
            "version": settings.version
        }
    }


@router.post("/test-connection")
async def test_connections(data: Dict[str, Any]) -> Dict[str, Any]:
    """Test API connections."""
    results = {}
    
    results["ai"] = {
        "status": "ok" if settings.ai_api_key else "not_configured",
        "message": "API key configured" if settings.ai_api_key else "No API key set"
    }
    
    if data.get("test_jira") and settings.jira_base_url:
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
