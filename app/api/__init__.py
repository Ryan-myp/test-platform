from .knowledge import router as knowledge_router
from .tasks import router as tasks_router
from .schedule import router as schedule_router
from .config import router as config_router
from .stats import router as stats_router
from .browser import router as browser_router

__all__ = ["knowledge_router", "tasks_router", "schedule_router", "config_router", "stats_router", "browser_router"]
