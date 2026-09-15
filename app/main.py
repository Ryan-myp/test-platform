"""TestPilot Pro — 主应用入口"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from loguru import logger
import sys

from app.config import settings
from app.database import init_db, seed_prompts, seed_admin_user, AsyncSessionLocal

# 导入所有路由
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info(f"🚀 Starting {settings.app_name} v{settings.version}")
    await init_db()
    await seed_prompts()
    await seed_admin_user()
    logger.info("✅ Database initialized")
    logger.info(f"🤖 AI Model: {settings.ai_model} | API Key: {'✅' if settings.ai_api_key else '❌'}")
    logger.info(f"📊 Kibana: {'✅' if settings.kibana_base_url else '❌'} | Jira: {'✅' if settings.jira_base_url else '❌'}")
    yield
    logger.info("🛑 Shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="AI 测试工作台 — 知识库沉淀 + 多入口 + 自动化执行引擎 + 多系统联动",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册所有路由
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


@app.get("/", response_class=HTMLResponse)
async def root():
    with open("templates/index.html", encoding="utf-8") as f:
        return f.read()


@app.get("/health")
async def health():
    return {"status": "ok", "name": settings.app_name, "version": settings.version}


if __name__ == "__main__":
    import uvicorn
    logger.remove()
    logger.add(sys.stderr, level="INFO",
               format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
