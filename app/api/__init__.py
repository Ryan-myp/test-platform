from app.api.knowledge import router as knowledge_router
from app.api.tasks import router as tasks_router
from app.api.schedule import router as schedule_router
from app.api.config import router as config_router
from app.api.stats import router as stats_router

__all__ = ["knowledge_router", "tasks_router", "schedule_router", "config_router", "stats_router"]
