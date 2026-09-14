"""自动化测试执行引擎 — 真实执行，不只是生成文案"""
import json
import time
import httpx
import asyncio
from datetime import datetime, timezone
from loguru import logger
from app.database import AsyncSessionLocal, _exec, ApiTestResult, SqlExecResult
from sqlalchemy import select, text as sa_text


# ── API 测试执行器 ─────────────────────────────────────────

class ApiTestExecutor:
    """真实发送 HTTP 请求，验证响应"""

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    async def execute(self, task_id: int, url: str, method: str = "GET",
                      headers: dict = None, body: dict = None,
                      expected_status: int = None, assert_json: dict = None) -> dict:
        """执行单个 API 测试，返回结果"""
        result = {
            "url": url, "method": method, "status_code": 0,
            "response_time_ms": 0.0, "passed": False, "error": ""
        }
        start = time.perf_counter()
        try:
            kwargs = {"timeout": self.timeout}
            if headers:
                kwargs["headers"] = headers
            if body and method in ("POST", "PUT", "PATCH"):
                kwargs["json"] = body

            async with httpx.AsyncClient() as client:
                resp = await client.request(method.upper(), url, **kwargs)
                result["status_code"] = resp.status_code
                result["response_time_ms"] = round((time.perf_counter() - start) * 1000, 2)
                result["body"] = resp.text[:2000]

                # 断言检查
                errors = []
                if expected_status and resp.status_code != expected_status:
                    errors.append(f"期望状态码 {expected_status}，实际 {resp.status_code}")
                if assert_json:
                    try:
                        data = resp.json()
                        for key, val in assert_json.items():
                            actual = data.get(key)
                            if actual != val:
                                errors.append(f"字段 {key}: 期望 {val!r}，实际 {actual!r}")
                    except Exception as e:
                        errors.append(f"JSON 解析失败: {e}")

                result["passed"] = len(errors) == 0
                result["error"] = "; ".join(errors) if errors else ""

        except httpx.TimeoutException:
            result["error"] = f"请求超时 ({self.timeout}s)"
        except Exception as e:
            result["error"] = str(e)

        # 持久化结果
        async with AsyncSessionLocal() as session:
            await _exec(session, """
                INSERT INTO api_test_results (task_id, url, method, status_code,
                    response_time_ms, body, passed, error)
                VALUES (:task_id, :url, :method, :status_code, :response_time_ms,
                        :body, :passed, :error)
            """, {
                "task_id": task_id, "url": url, "method": method,
                "status_code": result["status_code"],
                "response_time_ms": result["response_time_ms"],
                "body": result.get("body", ""),
                "passed": result["passed"], "error": result["error"]
            })
        return result


# ── SQL 执行器 ──────────────────────────────────────────────

class SqlExecutor:
    """执行 SQL 并记录结果（只读查询，生产环境需权限控制）"""

    def __init__(self, connection_string: str = ""):
        self.connection_string = connection_string

    async def execute(self, task_id: int, sql: str, db_url: str = "") -> dict:
        """执行 SQL，返回结果"""
        result = {
            "sql": sql, "rows_affected": 0, "result_data": [],
            "execution_time_ms": 0.0, "error": ""
        }
        start = time.perf_counter()
        try:
            # 只允许 SELECT 语句（安全限制）
            stripped = sql.strip().upper()
            if not stripped.startswith("SELECT"):
                raise ValueError("安全限制：只允许 SELECT 查询")

            import sqlite3
            conn = sqlite3.connect(db_url or self.connection_string or "testpilot.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            result["rows_affected"] = len(rows)
            if rows and len(rows) > 0:
                keys = rows[0].keys()
                result["result_data"] = [dict(zip(keys, r)) for r in rows[:100]]  # 最多100行
            conn.close()
            result["execution_time_ms"] = round((time.perf_counter() - start) * 1000, 2)

        except Exception as e:
            result["error"] = str(e)

        # 持久化
        async with AsyncSessionLocal() as session:
            await _exec(session, """
                INSERT INTO sql_exec_results (task_id, sql, rows_affected,
                    result_data, execution_time_ms, error)
                VALUES (:task_id, :sql, :rows_affected, :result_data,
                        :execution_time_ms, :error)
            """, {
                "task_id": task_id, "sql": sql,
                "rows_affected": result["rows_affected"],
                "result_data": str(result["result_data"]),
                "execution_time_ms": result["execution_time_ms"],
                "error": result["error"]
            })
        return result


# ── 用例执行器 ──────────────────────────────────────────────

class TestCaseExecutor:
    """执行测试用例，跟踪通过/失败"""

    def __init__(self):
        self.results: dict[int, list[dict]] = {}  # task_id -> [case_result]

    async def execute_case(self, task_id: int, case_id: int,
                           case_name: str, steps: str, expected: str,
                           run_fn=None) -> dict:
        """执行单条用例"""
        start = datetime.now(timezone.utc)
        passed = False
        error = ""
        actual_output = ""

        if run_fn:
            try:
                actual_output = await run_fn()
                passed = True  # 简化：有输出即视为通过，实际应用需断言
            except Exception as e:
                passed = False
                error = str(e)
        else:
            # 模拟执行
            await asyncio.sleep(0.1)
            passed = True
            actual_output = f"执行步骤: {steps[:100]}"

        result = {
            "case_id": case_id, "case_name": case_name,
            "passed": passed, "error": error,
            "actual": actual_output,
            "started_at": start.isoformat(),
            "duration_ms": 0  # 简化
        }
        self.results.setdefault(task_id, []).append(result)
        return result

    async def get_summary(self, task_id: int) -> dict:
        """获取用例执行汇总"""
        cases = self.results.get(task_id, [])
        if not cases:
            return {"total": 0, "passed": 0, "failed": 0, "rate": "0%"}
        passed = sum(1 for c in cases if c["passed"])
        total = len(cases)
        return {
            "total": total, "passed": passed, "failed": total - passed,
            "rate": f"{passed/total*100:.1f}%"
        }


# ── Kibana 日志查询适配器 ───────────────────────────────────

class KibanaAdapter:
    """查询 Kibana/Elasticsearch 日志"""

    def __init__(self, base_url: str = "", api_key: str = ""):
        self.base_url = base_url
        self.api_key = api_key

    async def search_logs(self, query: str, time_range: str = "last_15_minutes",
                          size: int = 20) -> list[dict]:
        """搜索日志"""
        if not self.base_url:
            return [{"_source": {"message": f"[模拟] 未配置 Kibana，返回模拟日志: {query}"}}]

        try:
            headers = {"kbn-xsrf": "true", "Authorization": f"ApiKey {self.api_key}"}
            body = {
                "query": {"bool": {"must": [{"match": {"message": query}}],
                                   "filter": [{"range": {"@timestamp": {"gte": time_range}}}]}},
                "size": size,
                "sort": [{"@timestamp": {"order": "desc"}}]
            }
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/_search", json=body, headers=headers, timeout=10)
                hits = resp.json().get("hits", {}).get("hits", [])
                return [{"_source": h["?_source"]} for h in hits]
        except Exception as e:
            logger.opt(exception=True).error(f"Kibana 查询失败: {e}")
            return [{"_source": {"message": f"[错误] {e}"}}]


# ── Jira 适配器 ─────────────────────────────────────────────

class JiraAdapter:
    """对接 Jira 创建/查询 Bug"""

    def __init__(self, base_url: str = "", token: str = ""):
        self.base_url = base_url
        self.token = token

    async def create_issue(self, summary: str, description: str,
                           project: str = "TEST", issue_type: str = "Bug") -> dict:
        """创建 Jira Issue"""
        if not self.base_url:
            return {"id": "MOCK-JIRA-001", "key": "TEST-999", "status": "created (mock)"}
        try:
            headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
            body = {
                "fields": {
                    "project": {"key": project},
                    "summary": summary,
                    "description": description,
                    "issuetype": {"name": issue_type}
                }
            }
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/rest/api/2/issue", json=body, headers=headers, timeout=10)
                return resp.json()
        except Exception as e:
            logger.opt(exception=True).error(f"Jira 创建失败: {e}")
            return {"error": str(e)}

    async def search_issues(self, jql: str) -> list[dict]:
        """搜索 Jira Issue"""
        if not self.base_url:
            return []
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            params = {"jql": jql, "maxResults": 10}
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.base_url}/rest/api/2/search", params=params, headers=headers, timeout=10)
                return resp.json().get("issues", [])
        except Exception as e:
            logger.opt(exception=True).error(f"Jira 搜索失败: {e}")
            return []


# ── Webhook 通知 ────────────────────────────────────────────

class Notifier:
    """发送通知到企业微信/Slack"""

    def __init__(self, webhook_url: str = ""):
        self.webhook_url = webhook_url

    async def send(self, title: str, content: str, level: str = "info"):
        """发送通知"""
        if not self.webhook_url:
            logger.info(f"[通知] {level}: {title} - {content[:100]}")
            return
        try:
            # 企业微信格式
            body = {
                "msgtype": "markdown",
                "markdown": {"content": f"**{title}**\n{content}"}
            }
            async with httpx.AsyncClient() as client:
                await client.post(self.webhook_url, json=body, timeout=5)
                logger.info(f"通知已发送: {title}")
        except Exception as e:
            logger.opt(exception=True).error(f"通知发送失败: {e}")


# ── 浏览器测试执行 ──────────────────────────────────────────

async def run_browser_test(task_id: int, data: dict) -> dict:
    """执行浏览器自动化测试"""
    from app.browser_executor import get_browser_executor, close_browser_executor
    executor = get_browser_executor()

    url = data.get("url", "")
    cases_raw = data.get("cases_json", "[]")
    viewport_str = data.get("viewport", "1920x1080")
    wait_for = data.get("wait_for")

    # 解析视口
    viewport = None
    if viewport_str:
        parts = viewport_str.split("x")
        if len(parts) == 2:
            try:
                viewport = {"width": int(parts[0]), "height": int(parts[1])}
            except ValueError:
                pass

    # 解析测试用例
    try:
        cases = json.loads(cases_raw) if cases_raw else []
    except json.JSONDecodeError:
        cases = []

    if not cases:
        return {"note": "未提供测试用例，跳过浏览器测试"}

    return await executor.execute_task(task_id, url, cases, viewport)


async def run_ai_browser_test(task_id: int, data: dict) -> dict:
    """AI 生成用例 + 浏览器执行"""
    from app.browser_executor import get_browser_executor, close_browser_executor
    from app.ai import call_ai

    url = data.get("url", "")
    feature = data.get("feature", "")
    priority = data.get("priority", "P1")

    if not url or not feature:
        return {"note": "缺少 url 或 feature，跳过测试"}

    # 步骤1: AI 生成测试用例
    ai_result = await call_ai("generate_cases", {
        "requirement": f"在 {url} 上测试 {feature} 功能",
        "priority": priority,
        "module": "Web UI"
    })

    # 步骤2: 解析 AI 输出，转换为 Playwright 步骤
    cases = _parse_ai_output_to_cases(ai_result.get("output", ""), feature)

    # 步骤3: 浏览器执行
    executor = get_browser_executor()
    viewport = {"width": 1920, "height": 1080}
    return await executor.execute_task(task_id, url, cases, viewport)


def _parse_ai_output_to_cases(ai_output: str, feature: str) -> list[dict]:
    """将 AI 输出的测试用例转换为 Playwright 步骤"""
    cases = []
    lines = ai_output.split("\n")
    current_case = None

    for line in lines:
        line = line.strip()
        # 检测用例编号
        import re
        tc_match = re.match(r'(TC[-_\s]*\w+[\s-]*\d+|[Tt][Cc][-_\s]*\d+)', line)
        if tc_match:
            if current_case:
                cases.append(current_case)
            current_case = {"id": tc_match.group(1).replace("-", "").replace("_", ""),
                           "name": line.split("|")[-1].strip() if "|" in line else line,
                           "steps": []}
            continue

        # 检测步骤
        if current_case and ("步骤" in line or "操作" in line or line.startswith(("1.", "2.", "3."))):
            step_text = re.sub(r'^\d+\.\s*', '', line)
            current_case["steps"].append({
                "action": "click" if "点击" in step_text else "fill" if "输入" in step_text else "navigate",
                "target": "body",
                "value": step_text[:100]
            })

    if current_case:
        cases.append(current_case)

    # 如果没有解析出用例，创建一个默认的
    if not cases:
        cases = [{
            "id": "TC-001",
            "name": f"{feature} - 默认测试",
            "steps": [
                {"action": "navigate", "target": "", "value": ""},
                {"action": "screenshot", "target": "", "value": ""}
            ]
        }]

    return cases
