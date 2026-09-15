"""API router initialization."""
from fastapi import APIRouter
from app.api.test_cases import router as test_cases_router
from app.api.test_suites import router as test_suites_router
from app.api.bugs import router as bugs_router
from app.api.knowledge import router as knowledge_router
from app.api.tasks import router as tasks_router
from app.api.schedule import router as schedule_router
from app.api.config import router as config_router
from app.api.stats import router as stats_router
from app.api.browser import router as browser_router
from app.api.executions import router as executions_router
from app.api.reports import router as reports_router
from app.api.environments import router as environments_router
from app.api.test_data import router as test_data_router
from app.api.webhooks import router as webhooks_router
from app.api.entries import router as entries_router

api_router = APIRouter(prefix="/api")

api_router.include_router(test_cases_router)
api_router.include_router(test_suites_router)
api_router.include_router(bugs_router)
api_router.include_router(knowledge_router)
api_router.include_router(tasks_router)
api_router.include_router(schedule_router)
api_router.include_router(config_router)
api_router.include_router(stats_router)
api_router.include_router(browser_router)
api_router.include_router(executions_router)
api_router.include_router(reports_router)
api_router.include_router(environments_router)
api_router.include_router(test_data_router)
api_router.include_router(webhooks_router)
api_router.include_router(entries_router)
