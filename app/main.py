"""TestPilot Pro — 主应用入口"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from loguru import logger
import sys

from app.config import settings
from app.database import init_db, seed_prompts, AsyncSessionLocal
from app.api import knowledge_router, tasks_router, schedule_router, config_router, stats_router, browser_router
from app.api import test_cases as test_cases_router
from app.api import test_suites as test_suites_router
from app.api import executions as executions_router
from app.api import bugs as bugs_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # Startup
    logger.info(f"🚀 Starting {settings.app_name} v{settings.version}")
    await init_db()
    async with AsyncSessionLocal() as session:
        await seed_prompts()
    logger.info("✅ Database initialized")
    logger.info(f"🤖 AI Model: {settings.ai_model} | API Key: {'✅' if settings.ai_api_key else '❌'}")
    logger.info(f"📊 Kibana: {'✅' if settings.kibana_base_url else '❌'} | Jira: {'✅' if settings.jira_base_url else '❌'}")
    yield
    # Shutdown
    logger.info("🛑 Shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="AI 测试工作台 — 知识库沉淀 + 六大入口 + 自动化执行引擎 + 多系统联动",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(knowledge_router)
app.include_router(tasks_router)
app.include_router(schedule_router)
app.include_router(config_router)
app.include_router(stats_router)
app.include_router(browser_router)
app.include_router(test_cases_router.router)
app.include_router(test_suites_router.router)
app.include_router(executions_router.router)
app.include_router(bugs_router.router)


@app.get("/", response_class=HTMLResponse)
async def root():
    with open("templates/index.html", encoding="utf-8") as f:
        return f.read()


@app.get("/health")
async def health():
    return {"status": "ok", "name": settings.app_name, "version": settings.version}


if __name__ == "__main__":
    import uvicorn
    # 配置 loguru
    logger.remove()
    logger.add(sys.stderr, level="INFO",
               format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
