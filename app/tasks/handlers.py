"""Task handlers for various operations"""
import time
import asyncio
from typing import Dict, Any, List, Optional
from celery.signals import task_prerun, task_postrun
from loguru import logger
from app.tasks.worker import celery_app


@task_prerun.connect
def task_prerun_handler(task_id, task, *args, **kwargs):
    """任务开始前"""
    logger.info(f"🚀 Task started: {task.name} | ID: {task_id[:8]}")
    task.meta['started_at'] = time.time()


@task_postrun.connect
def task_postrun_handler(task_id, task, *args, **kwargs):
    """任务结束后"""
    duration = time.time() - task.meta.get('started_at', time.time())
    logger.info(f"✅ Task completed: {task.name} | Duration: {duration:.2f}s | ID: {task_id[:8]}")


@celery_app.task(bind=True, name="execute_test_case")
def execute_test_case(self, case_id: int, environment: str = "test") -> Dict[str, Any]:
    """执行测试用例"""
    from app.database import AsyncSessionLocal, sa_text
    from app.test_runner import TestRunner
    
    start_time = time.time()
    logger.info(f"🧪 Executing test case {case_id} on {environment}")
    
    try:
        async def _run():
            async with AsyncSessionLocal() as session:
                # 获取用例
                result = await session.execute(
                    sa_text("SELECT * FROM test_cases WHERE id = :id"),
                    {"id": case_id}
                )
                case = result.fetchone()
                if not case:
                    return {"error": "Case not found", "case_id": case_id}
                
                # 执行测试
                runner = TestRunner()
                execution_result = await runner.execute_case(case, environment)
                
                # 保存结果
                exec_id = f"exec_{case_id}_{int(time.time())}"
                await session.execute(sa_text("""
                    INSERT INTO task_executions 
                    (entry_type, title, input_data, output_data, status, duration_ms, 
                     case_id, environment, started_at, completed_at)
                    VALUES (:entry_type, :title, :input_data, :output_data, :status, 
                            :duration_ms, :case_id, :environment, :started_at, :completed_at)
                """), {
                    "entry_type": "test_execution",
                    "title": f"Test Case {case_id}",
                    "input_data": f'{{"case_id": {case_id}, "environment": "{environment}"}}',
                    "output_data": str(execution_result),
                    "status": "success" if execution_result.get("passed") else "failed",
                    "duration_ms": execution_result.get("duration_ms", 0),
                    "case_id": case_id,
                    "environment": environment,
                    "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "completed_at": time.strftime("%Y-%m-%d %H:%M:%S")
                })
                await session.commit()
                
                return {
                    "case_id": case_id,
                    "execution_id": exec_id,
                    "status": "success" if execution_result.get("passed") else "failed",
                    "duration_ms": execution_result.get("duration_ms", 0),
                    "result": execution_result
                }
        
        return asyncio.run(_run())
    
    except Exception as e:
        logger.error(f"❌ Task failed: {e}")
        return {
            "case_id": case_id,
            "status": "error",
            "error": str(e)
        }


@celery_app.task(name="generate_report")
def generate_report(report_type: str, filters: Dict[str, Any] = None) -> Dict[str, Any]:
    """生成报告"""
    from datetime import datetime
    import json
    
    logger.info(f"📊 Generating report: {report_type}")
    
    # 模拟报告生成
    report_data = {
        "type": report_type,
        "generated_at": datetime.now().isoformat(),
        "filters": filters or {},
        "summary": {
            "total_cases": 156,
            "passed": 142,
            "failed": 8,
            "skipped": 6,
            "pass_rate": "91.0%"
        }
    }
    
    return report_data


@celery_app.task(name="sync_knowledge")
def sync_knowledge(source: str, category: str = "general") -> Dict[str, Any]:
    """同步知识库"""
    logger.info(f"📚 Syncing knowledge from {source}")
    
    return {
        "source": source,
        "category": category,
        "synced_count": 42,
        "status": "completed"
    }


@celery_app.task(name="send_notification")
def send_notification(platform: str, message: str, recipients: List[str]) -> bool:
    """发送通知"""
    logger.info(f"💬 Sending notification to {platform}: {len(recipients)} recipients")
    
    # 实际项目中调用相应 API
    return True


@celery_app.task(name="execute_regression")
def execute_regression(suite_id: int, environment: str = "test") -> Dict[str, Any]:
    """执行回归测试"""
    from app.database import AsyncSessionLocal, sa_text
    
    logger.info(f"🔄 Running regression for suite {suite_id}")
    
    async def _run():
        async with AsyncSessionLocal() as session:
            # 获取套件下的所有用例
            result = await session.execute(
                sa_text("SELECT id, name FROM test_cases WHERE suite_id = :suite_id"),
                {"suite_id": suite_id}
            )
            cases = result.fetchall()
            
            results = []
            for case in cases:
                case_result = await execute_test_case.delay(case[0], environment)
                results.append({
                    "case_id": case[0],
                    "case_name": case[1],
                    "status": case_result.get("status"),
                    "duration_ms": case_result.get("duration_ms")
                })
            
            return {
                "suite_id": suite_id,
                "total": len(results),
                "passed": sum(1 for r in results if r["status"] == "success"),
                "failed": sum(1 for r in results if r["status"] == "failed"),
                "results": results
            }
    
    return asyncio.run(_run())