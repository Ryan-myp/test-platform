"""Test execution engine - 真实测试执行"""
import asyncio
import time
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class TestRunner:
    """通用测试执行器"""
    
    def __init__(self):
        self.executions = {}
    
    async def run_case(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个测试用例"""
        execution_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        
        case_type = case.get("case_type", "api")
        api_config = case.get("api_config", {})
        
        result = {
            "execution_id": execution_id,
            "case_id": case.get("id"),
            "case_name": case.get("name", ""),
            "case_type": case_type,
            "status": "pending",
            "duration_ms": 0,
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "error": None,
            "details": {}
        }
        
        try:
            if case_type == "api":
                result = await self._run_api_test(case, api_config, start_time)
            elif case_type == "sql":
                result = await self._run_sql_test(case, api_config, start_time)
            elif case_type == "browser":
                result = await self._run_browser_test(case, api_config, start_time)
            else:
                result["status"] = "skipped"
                result["error"] = f"Unknown case type: {case_type}"
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            result["status"] = "error"
            result["error"] = str(e)
        
        result["completed_at"] = datetime.now().isoformat()
        result["duration_ms"] = round((time.time() - start_time) * 1000, 2)
        
        return result
    
    async def _run_api_test(self, case: Dict, config: Dict, start_time: float) -> Dict:
        """执行 API 测试"""
        import httpx
        
        url = config.get("url", "")
        method = config.get("method", "GET").upper()
        headers = config.get("headers", {})
        body = config.get("body")
        assertions = config.get("assertions", {})
        
        result = {
            "status": "pending",
            "status_code": None,
            "response_time_ms": 0,
            "response_body": None,
            "assertions": {},
            "passed": False,
            "errors": []
        }
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=body,
                    follow_redirects=True
                )
            
            result["status_code"] = resp.status_code
            result["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
            
            # Parse response
            content_type = resp.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    result["response_body"] = resp.json()
                except:
                    result["response_body"] = resp.text
            else:
                result["response_body"] = resp.text[:1000]
            
            # Check assertions
            passed = True
            errors = []
            
            if "status_code" in assertions:
                expected = assertions["status_code"]
                if resp.status_code != expected:
                    passed = False
                    errors.append(f"Status code mismatch: expected {expected}, got {resp.status_code}")
            
            if "response_time" in assertions:
                max_time = assertions["response_time"]
                if result["response_time_ms"] > max_time:
                    passed = False
                    errors.append(f"Response time {result['response_time_ms']:.0f}ms exceeds limit {max_time}ms")
            
            if "body_contains" in assertions:
                body_str = json.dumps(result["response_body"]) if result["response_body"] else ""
                if assertions["body_contains"] not in body_str:
                    passed = False
                    errors.append(f"Response body does not contain: {assertions['body_contains']}")
            
            result["assertions"] = assertions
            result["passed"] = passed
            result["errors"] = errors
            result["status"] = "passed" if passed else "failed"
            
        except httpx.TimeoutException:
            result["status"] = "error"
            result["error"] = "Request timeout"
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
        
        return result
    
    async def _run_sql_test(self, case: Dict, config: Dict, start_time: float) -> Dict:
        """执行 SQL 测试"""
        import sqlite3
        
        sql = config.get("sql", "")
        db_url = config.get("db_url", "")
        assertions = config.get("assertions", {})
        
        result = {
            "status": "pending",
            "rows": 0,
            "duration_ms": 0,
            "data": [],
            "passed": False,
            "errors": []
        }
        
        try:
            if not db_url or not sql:
                result["status"] = "skipped"
                result["error"] = "Missing db_url or sql"
                return result
            
            db_path = db_url.replace("sqlite:///", "").replace("sqlite:///", "")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute(sql)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            
            result["rows"] = len(rows)
            result["data"] = [{"columns": columns, "rows": rows[:100]}]  # Limit to 100 rows
            result["duration_ms"] = round((time.time() - start_time) * 1000, 2)
            
            # Check assertions
            passed = True
            errors = []
            
            if "min_rows" in assertions:
                if len(rows) < assertions["min_rows"]:
                    passed = False
                    errors.append(f"Expected at least {assertions['min_rows']} rows, got {len(rows)}")
            
            if "max_rows" in assertions:
                if len(rows) > assertions["max_rows"]:
                    passed = False
                    errors.append(f"Expected at most {assertions['max_rows']} rows, got {len(rows)}")
            
            result["passed"] = passed
            result["errors"] = errors
            result["status"] = "passed" if passed else "failed"
            
            conn.close()
            
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
        
        return result
    
    async def _run_browser_test(self, case: Dict, config: Dict, start_time: float) -> Dict:
        """执行浏览器测试"""
        result = {
            "status": "pending",
            "url": config.get("url", ""),
            "actions": config.get("actions", []),
            "screenshots": [],
            "passed": False,
            "errors": []
        }
        
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(viewport={"width": 1920, "height": 1080})
                
                try:
                    await page.goto(config.get("url", ""), wait_until="networkidle", timeout=30000)
                    
                    screenshots = []
                    for action in config.get("actions", []):
                        action_type = action.get("type", "")
                        selector = action.get("selector", "")
                        value = action.get("value", "")
                        
                        if action_type == "fill":
                            await page.fill(selector, value)
                        elif action_type == "click":
                            await page.click(selector)
                        elif action_type == "screenshot":
                            screenshot_path = f"/tmp/testpilot-pro/screenshots/{result['status']}.png"
                            await page.screenshot(path=screenshot_path, full_page=True)
                            screenshots.append(screenshot_path)
                        elif action_type == "assert_visible":
                            await page.wait_for_selector(selector, timeout=5000)
                    
                    result["screenshots"] = screenshots
                    result["passed"] = True
                    result["status"] = "passed"
                    
                except Exception as e:
                    result["error"] = str(e)
                    result["status"] = "error"
                
                await browser.close()
                
        except ImportError:
            result["status"] = "skipped"
            result["error"] = "Playwright not installed"
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
        
        result["duration_ms"] = round((time.time() - start_time) * 1000, 2)
        return result
    
    async def run_suite(self, suite: Dict[str, Any]) -> Dict[str, Any]:
        """执行测试套件"""
        execution_id = str(uuid.uuid4())[:8]
        cases = suite.get("cases", [])
        
        results = []
        for case in cases:
            result = await self.run_case(case)
            results.append(result)
        
        passed = sum(1 for r in results if r.get("status") == "passed")
        failed = sum(1 for r in results if r.get("status") == "failed")
        error = sum(1 for r in results if r.get("status") == "error")
        
        return {
            "execution_id": execution_id,
            "suite_id": suite.get("id"),
            "suite_name": suite.get("name", ""),
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "error": error,
            "pass_rate": round(passed / max(len(results), 1) * 100, 1),
            "results": results,
            "started_at": suite.get("started_at"),
            "completed_at": datetime.now().isoformat()
        }


# 全局执行器实例
runner = TestRunner()
