"""Scheduled task executor"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
import schedule
import time

logger = logging.getLogger(__name__)


class TaskScheduler:
    """定时任务调度器"""
    
    def __init__(self):
        self.jobs: Dict[str, Any] = {}
        self.running = False
    
    def add_job(self, job_id: str, cron: str, callback, description: str = ""):
        """添加定时任务"""
        self.jobs[job_id] = {
            "cron": cron,
            "callback": callback,
            "description": description,
            "next_run": None,
            "last_run": None,
            "status": "scheduled"
        }
        
        # Schedule the job
        try:
            schedule.every().day.at(cron).do(callback, job_id)
            logger.info(f" Scheduled job '{job_id}' at {cron}")
        except Exception as e:
            logger.error(f"Failed to schedule job '{job_id}': {e}")
    
    def remove_job(self, job_id: str):
        """移除定时任务"""
        if job_id in self.jobs:
            del self.jobs[job_id]
            logger.info(f" Removed job '{job_id}'")
    
    def get_jobs(self) -> List[Dict[str, Any]]:
        """获取所有任务"""
        return list(self.jobs.values())
    
    def run_now(self, job_id: str):
        """立即执行任务"""
        if job_id in self.jobs:
            self.jobs[job_id]["status"] = "running"
            self.jobs[job_id]["last_run"] = datetime.now().isoformat()
            asyncio.create_task(self.jobs[job_id]["callback"](job_id))
    
    def start(self):
        """启动调度器"""
        self.running = True
        logger.info(" Scheduler started")
        
        while self.running:
            schedule.run_pending()
            time.sleep(1)
    
    def stop(self):
        """停止调度器"""
        self.running = False
        logger.info(" Scheduler stopped")


# 全局调度器实例
scheduler = TaskScheduler()
