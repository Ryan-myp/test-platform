"""TestPilot Pro — 主应用入口"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from loguru import logger
import sys

from app.config import settings
from app.database import init_db, seed_prompts, seed_admin_user, AsyncSessionLocal
from app.exceptions import register_exceptions
from app.middleware import RateLimitMiddleware, AuditMiddleware
from app.cache import RedisClient, stats_cache
from app.telemetry.instrumentation import telemetry
from app.metrics import metrics
from app.tenants.manager import tenant_manager

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
from app.api.tasks_queue import router as tasks_queue_router
from app.graphql.router import router as graphql_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info(f"🚀 Starting {settings.app_name} v{settings.version}")
    
    # 初始化数据库
    await init_db()
    await seed_prompts()
    await seed_admin_user()
    logger.info("✅ Database initialized")
    
    # 初始化 Redis
    redis_client = RedisClient()
    await redis_client.connect()
    app.state.redis = redis_client
    
    # 初始化租户
    tenant_manager.register_tenant(tenant_manager._default_tenant)
    logger.info("🏢 Tenant manager initialized")
    
    # 初始化遥测
    telemetry.record_counter("system.startup.total")
    logger.info(f"🤖 AI Model: {settings.ai_model} | API Key: {'✅' if settings.ai_api_key else '❌'}")
    logger.info(f"📊 Kibana: {'✅' if settings.kibana_base_url else '❌'} | Jira: {'✅' if settings.jira_base_url else '❌'}")
    
    yield
    
    # 清理
    await redis_client.close()
    logger.info("🛑 Shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="AI 测试工作台 — 知识库沉淀 + 多入口 + 自动化执行引擎 + 多系统联动",
    lifespan=lifespan
)

# 中间件
app.add_middleware(AuditMiddleware)
app.add_middleware(RateLimitMiddleware)
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
app.include_router(tasks_queue_router)
app.include_router(graphql_router)

# 注册异常处理器
register_exceptions(app)


@app.get("/", response_class=HTMLResponse)
async def root():
    with open("templates/index.html", encoding="utf-8") as f:
        return f.read()


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "name": settings.app_name,
        "version": settings.version,
        "features": {
            "redis": app.state.redis.connected if hasattr(app.state, 'redis') else False,
            "celery": True,
            "graphql": True,
            "telemetry": telemetry._enabled,
            "metrics": True
        }
    }


@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus 指标端点"""
    from starlette.responses import Response
    return Response(content=metrics.collect(), media_type="text/plain")


@app.get("/api/telemetry/stats")
async def telemetry_stats():
    """遥测统计"""
    return {
        "enabled": telemetry._enabled,
        "tracer": telemetry._tracer is not None,
        "meter": telemetry._meter is not None
    }


if __name__ == "__main__":
    import uvicorn
    logger.remove()
    logger.add(sys.stderr, level="INFO",
               format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
