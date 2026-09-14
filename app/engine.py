"""Test execution engine."""
import asyncio
import time
import uuid
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ApiTestExecutor:
    """Execute API test cases."""
    
    async def execute(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute API test."""
        start_time = time.time()
        
        try:
            import httpx
            url = config.get("url", "")
            method = config.get("method", "GET").upper()
            headers = config.get("headers", {})
            body = config.get("body")
            assertions = config.get("assertions", {})
            
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=body,
                    timeout=30.0
                )
                
                duration_ms = (time.time() - start_time) * 1000
                
                # Check assertions
                passed = True
                errors = []
                
                if "status_code" in assertions:
                    if response.status_code != assertions["status_code"]:
                        passed = False
                        errors.append(f"Status code mismatch: expected {assertions['status_code']}, got {response.status_code}")
                
                return {
                    "status": "passed" if passed else "failed",
                    "status_code": response.status_code,
                    "response_time_ms": round(duration_ms, 2),
                    "response_body": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                    "passed": passed,
                    "errors": errors
                }
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return {
                "status": "error",
                "error": str(e),
                "response_time_ms": round(duration_ms, 2),
                "passed": False
            }


class SqlExecutor:
    """Execute SQL test cases."""
    
    async def execute(self, task_id: int, sql: str, db_url: str) -> Dict[str, Any]:
        """Execute SQL query."""
        import sqlite3
        import json
        from datetime import datetime
        
        start_time = time.time()
        
        try:
            # Connect to database
            if db_url.startswith("sqlite"):
                db_path = db_url.replace("sqlite:///", "").replace("sqlite:///", "")
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute(sql)
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                conn.close()
                
                duration_ms = (time.time() - start_time) * 1000
                
                result_data = []
                for row in rows[:10]:  # Limit to first 10 rows
                    result_data.append(dict(zip(columns, row)))
                
                return {
                    "status": "success",
                    "rows_affected": len(rows),
                    "result_data": result_data,
                    "execution_time_ms": round(duration_ms, 2)
                }
            else:
                return {
                    "status": "error",
                    "error": "Only SQLite supported"
                }
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return {
                "status": "error",
                "error": str(e),
                "execution_time_ms": round(duration_ms, 2)
            }


class TestRunner:
    """Main test runner."""
    
    def __init__(self):
        self.api_executor = ApiTestExecutor()
        self.sql_executor = SqlExecutor()
    
    async def execute_case(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single test case."""
        case_type = case_data.get("case_type", "api")
        execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        started_at = datetime.now().isoformat()
        
        logger.info(f"Executing case {case_data.get('id')}: {case_data.get('name')}")
        
        try:
            if case_type == "api":
                api_config = case_data.get("api_config", {})
                if isinstance(api_config, str):
                    import json
                    api_config = json.loads(api_config)
                result = await self.api_executor.execute(api_config)
            elif case_type == "sql":
                sql_config = case_data.get("sql_config", {})
                result = await self.sql_executor.execute(0, sql_config.get("sql", ""), sql_config.get("db_url", ""))
            else:
                result = {"status": "error", "error": f"Unknown case type: {case_type}"}
            
            completed_at = datetime.now().isoformat()
            
            return {
                "execution_id": execution_id,
                "case_id": case_data.get("id"),
                "status": result.get("status", "failed"),
                "duration_ms": result.get("response_time_ms", 0),
                "actual_result": result,
                "expected": case_data.get("expected", ""),
                "error": result.get("error", ""),
                "started_at": started_at,
                "completed_at": completed_at
            }
        except Exception as e:
            logger.error(f"Case execution failed: {e}")
            return {
                "execution_id": execution_id,
                "case_id": case_data.get("id"),
                "status": "error",
                "error": str(e),
                "started_at": started_at,
                "completed_at": datetime.now().isoformat()
            }
    
    async def run_cases(self, case_ids: List[int], execution_id: str) -> List[Dict[str, Any]]:
        """Run multiple test cases."""
        from app.database import AsyncSessionLocal
        from sqlalchemy import text as sa_text
        
        results = []
        
        async with AsyncSessionLocal() as session:
            for case_id in case_ids:
                r = await session.execute(sa_text("SELECT * FROM test_cases WHERE id = :id"), {"id": case_id})
                row = r.fetchone()
                
                if row:
                    case_data = {
                        "id": row[0],
                        "name": row[1],
                        "case_type": row[4] or "api",
                        "api_config": __import__('json').loads(row[11] or "{}"),
                        "sql_config": __import__('json').loads(row[12] or "{}"),
                        "expected": row[10] or ""
                    }
                    result = await self.execute_case(case_data)
                    result["execution_id"] = execution_id
                    results.append(result)
        
        return results
    
    async def run_suite(self, suite_id: int) -> Dict[str, Any]:
        """Run all cases in a suite."""
        from app.database import AsyncSessionLocal
        from sqlalchemy import text as sa_text
        import json
        
        execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        
        async with AsyncSessionLocal() as session:
            # Get suite
            r = await session.execute(sa_text("SELECT * FROM test_suites WHERE id = :id"), {"id": suite_id})
            suite = r.fetchone()
            if not suite:
                return {"error": "Suite not found"}
            
            # Get cases
            r = await session.execute(sa_text("SELECT id FROM test_cases WHERE suite_id = :id"), {"id": suite_id})
            case_ids = [row[0] for row in r.fetchall()]
            
            # Run cases
            results = await self.run_cases(case_ids, execution_id)
            
            # Save execution record
            await session.execute(sa_text("""
                INSERT INTO test_results 
                (suite_id, case_id, execution_id, status, duration_ms, actual_result, expected_result, 
                 error_message, started_at, completed_at)
                VALUES (:suite_id, :case_id, :execution_id, :status, :duration_ms, :actual_result, :expected_result,
                        :error_message, :started_at, :completed_at)
            """), {
                "suite_id": suite_id,
                "case_id": None,
                "execution_id": execution_id,
                "status": "completed",
                "duration_ms": sum(r.get("duration_ms", 0) for r in results),
                "actual_result": "{}",
                "expected_result": "",
                "error_message": "",
                "started_at": "",
                "completed_at": ""
            })
            await session.commit()
            
            return {
                "execution_id": execution_id,
                "suite_id": suite_id,
                "suite_name": suite[1],
                "total": len(results),
                "passed": sum(1 for r in results if r["status"] == "passed"),
                "failed": sum(1 for r in results if r["status"] == "failed"),
                "results": results
            }
