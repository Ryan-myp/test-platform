"""TestPilot Pro - AI Testing Platform"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from loguru import logger
import sys

from app.config import settings

# 导入路由
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
from app.api.ci_cd import router as ci_cd_router
from app.api.auth import router as auth_router


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="AI 测试工作台",
)

# 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册所有路由（路由内部已有 prefix）
app.include_router(test_cases_router)
app.include_router(test_suites_router)
app.include_router(bugs_router)
app.include_router(knowledge_router)
app.include_router(tasks_router)
app.include_router(schedule_router)
app.include_router(config_router)
app.include_router(stats_router)
app.include_router(browser_router)
app.include_router(executions_router)
app.include_router(reports_router)
app.include_router(environments_router)
app.include_router(test_data_router)
app.include_router(webhooks_router)
app.include_router(entries_router)
app.include_router(ci_cd_router)
app.include_router(auth_router)


@app.on_event("startup")
async def startup():
    """启动时初始化"""
    from app.database import init_db, seed_admin_user
    logger.info(f"🚀 Starting {settings.app_name} v{settings.version}")
    await init_db()
    await seed_admin_user()
    logger.info("✅ Database initialized")


@app.get("/", response_class=HTMLResponse)
async def root():
    with open("templates/index.html", encoding="utf-8") as f:
        return f.read()


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "name": settings.app_name,
        "version": settings.version
    }


if __name__ == "__main__":
    import uvicorn
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
