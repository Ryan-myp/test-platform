"""Async task queue using asyncio"""
import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class TaskQueue:
    """Simple async task queue"""
    
    def __init__(self, concurrency: int = 5):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._workers: List[asyncio.Task] = []
        self._results: Dict[str, Dict[str, Any]] = {}
        self._concurrency = concurrency
        self._running = False
    
    async def start(self):
        self._running = True
        for i in range(self._concurrency):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self._workers.append(worker)
        logger.info(f" Task queue started with {self._concurrency} workers")
    
    async def stop(self):
        self._running = False
        for worker in self._workers:
            worker.cancel()
        logger.info(" Task queue stopped")
    
    async def submit(self, task_id: str, callback: Callable, *args, **kwargs) -> str:
        task_info = {
            "task_id": task_id,
            "callback": callback,
            "args": args,
            "kwargs": kwargs,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "result": None,
            "error": None
        }
        self._results[task_id] = task_info
        await self._queue.put(task_id)
        return task_id
    
    async def _worker(self, worker_id: str):
        while self._running:
            try:
                task_id = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                task_info = self._results.get(task_id)
                if task_info:
                    task_info["status"] = "running"
                    task_info["started_at"] = datetime.now().isoformat()
                    try:
                        result = await task_info["callback"](*task_info["args"], **task_info["kwargs"])
                        task_info["status"] = "completed"
                        task_info["result"] = result
                    except Exception as e:
                        task_info["status"] = "failed"
                        task_info["error"] = str(e)
                        logger.error(f"Task {task_id} failed: {e}")
                    task_info["completed_at"] = datetime.now().isoformat()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker error: {e}")
    
    def get_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self._results.get(task_id)
    
    def list_tasks(self) -> List[Dict[str, Any]]:
        return list(self._results.values())


# 全局任务队列
task_queue = TaskQueue(concurrency=5)
