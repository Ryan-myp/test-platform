"""Celery application configuration"""
import os
from celery import Celery
from loguru import logger
from app.config import settings


def make_celery() -> Celery:
    """创建 Celery 应用"""
    # Celery 配置
    broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
    
    app = Celery(
        "testpilot",
        broker=broker_url,
        backend=result_backend,
        include=["app.tasks.handlers"]
    )
    
    # 自动发现任务
    app.autodiscover_tasks(["app.tasks"])
    
    # Celery 配置
    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="Asia/Shanghai",
        enable_utc=True,
        
        # 任务配置
        task_track_started=True,
        task_time_limit=300,  # 5分钟硬超时
        task_soft_time_limit=240,  # 4分钟软超时
        worker_prefetch_multiplier=1,
        
        # 重试配置
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_max_tasks_per_child=1000,
        
        # 结果过期
        result_expires=3600,  # 1小时
        
        # 并发配置
        worker_concurrency=4,
        worker_prefetch_multiplier=1,
    )
    
    logger.info(f"📦 Celery configured | Broker: {broker_url[:50]}...")
    return app


# 创建实例
celery_app = make_celery()


class TaskResult:
    """任务结果包装器"""
    
    def __init__(self, task_id: str):
        self.task_id = task_id
    
    def get_result(self, timeout: int = 30) -> dict:
        """获取任务结果"""
        from celery.result import AsyncResult
        result = AsyncResult(self.task_id, app=celery_app)
        
        if result.ready():
            return {
                "status": result.status,
                "result": result.result if result.successful() else None,
                "traceback": result.traceback if result.failed() else None
            }
        
        return {
            "status": result.status,
            "info": result.info if hasattr(result, 'info') else None
        }
    
    def is_done(self) -> bool:
        """检查任务是否完成"""
        from celery.result import AsyncResult
        return AsyncResult(self.task_id, app=celery_app).ready()