"""浏览器自动化测试执行器 — Playwright 驱动"""
import asyncio
import json
import time
from pathlib import Path
from datetime import datetime, timezone
from loguru import logger
from playwright.async_api import async_playwright, Page, Browser
from app.database import AsyncSessionLocal, _exec

SCREENSHOT_DIR = Path(__file__).parent.parent / "screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)


class BrowserTestResult:
    """浏览器测试用例执行结果"""
    def __init__(self, case_id: str, name: str):
        self.case_id = case_id
        self.name = name
        self.passed = False
        self.error = ""
        self.screenshot = ""
        self.steps: list[dict] = []
        self.duration_ms = 0.0
        self.started_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id, "name": self.name,
            "passed": self.passed, "error": self.error,
            "screenshot": self.screenshot, "steps": self.steps,
            "duration_ms": round(self.duration_ms, 2)
        }


class BrowserTestExecutor:
    """基于 Playwright 的浏览器自动化测试执行器"""

    def __init__(self, headless: bool = True, timeout: int = 30000):
        self.headless = headless
        self.timeout = timeout
        self._playwright = None
        self._browser: Browser = None

    async def start(self):
        """启动浏览器"""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        logger.info(f"🌐 浏览器已启动 (headless={self.headless})")

    async def stop(self):
        """关闭浏览器"""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("🌐 浏览器已关闭")

    async def execute_task(self, task_id: int, url: str, cases: list[dict],
                           viewport: dict = None) -> dict:
        """执行一组浏览器测试用例"""
        if not self._browser:
            await self.start()

        results = []
        total_start = time.perf_counter()

        for case in cases:
            case_start = time.perf_counter()
            result = BrowserTestResult(case.get("id", "TC-001"), case.get("name", "测试用例"))
            try:
                page = await self._browser.new_page()
                if viewport:
                    await page.set_viewport_size(viewport)

                # 导航到目标页面
                await page.goto(url, wait_until="networkidle", timeout=self.timeout)
                result.steps.append({"action": f"导航到 {url}", "time_ms": 0})

                # 执行测试步骤
                steps = case.get("steps", [])
                for i, step in enumerate(steps):
                    step_start = time.perf_counter()
                    action = step.get("action", "")
                    target = step.get("target", "")
                    value = step.get("value", "")
                    assert_type = step.get("assert", "visible")
                    assert_value = step.get("assert_value", "")

                    try:
                        if action == "click":
                            await page.click(target, timeout=5000)
                        elif action == "fill":
                            await page.fill(target, value, timeout=5000)
                        elif action == "select":
                            await page.select_option(target, value, timeout=5000)
                        elif action == "check":
                            await page.check(target, timeout=5000)
                        elif action == "screenshot":
                            screenshot_path = SCREENSHOT_DIR / f"task_{task_id}_{result.case_id}_{i}.png"
                            await page.screenshot(path=str(screenshot_path))
                            result.screenshot = str(screenshot_path)
                        elif action == "wait":
                            await page.wait_for_timeout(int(value) if value.isdigit() else 1000)
                        elif action == "navigate":
                            await page.goto(value, wait_until="networkidle", timeout=self.timeout)

                        # 断言检查
                        if assert_type:
                            passed, error = await self._assert(page, assert_type, target, assert_value)
                            if not passed:
                                result.error += f"步骤{i+1}断言失败: {error}; "
                                await self._take_screenshot(page, result)
                                continue

                        elapsed = (time.perf_counter() - step_start) * 1000
                        result.steps.append({
                            "action": action, "target": target,
                            "elapsed_ms": round(elapsed, 2), "passed": True
                        })

                    except Exception as e:
                        result.error += f"步骤{i+1}执行失败({action}): {str(e)[:100]}; "
                        await self._take_screenshot(page, result)
                        result.steps.append({
                            "action": action, "target": target,
                            "error": str(e)[:100], "passed": False
                        })

                result.passed = not result.error
                result.duration_ms = time.perf_counter() - case_start

            except Exception as e:
                result.error = f"执行失败: {str(e)[:200]}"
                result.duration_ms = time.perf_counter() - case_start
            finally:
                await page.close()
                results.append(result.to_dict())

        total_duration = time.perf_counter() - total_start
        passed = sum(1 for r in results if r["passed"])

        # 持久化结果
        async with AsyncSessionLocal() as session:
            await _exec(session, """
                INSERT INTO browser_test_results (task_id, url, cases, passed_count,
                    failed_count, total_count, duration_ms, results, screenshot_dir)
                VALUES (:task_id, :url, :cases, :passed, :failed, :total, :duration_ms, :results, :dir)
            """, {
                "task_id": task_id, "url": url,
                "cases": json.dumps([c.get("name", "") for c in cases], ensure_ascii=False),
                "passed": passed, "failed": len(results) - passed,
                "total": len(results), "duration_ms": round(total_duration * 1000, 2),
                "results": json.dumps(results, ensure_ascii=False),
                "dir": str(SCREENSHOT_DIR)
            })

        return {
            "total": len(results), "passed": passed, "failed": len(results) - passed,
            "rate": f"{passed/len(results)*100:.1f}%" if results else "0%",
            "duration_ms": round(total_duration * 1000, 2),
            "results": results,
            "screenshot_dir": str(SCREENSHOT_DIR)
        }

    async def _assert(self, page: Page, assert_type: str, target: str,
                      assert_value: str) -> tuple[bool, str]:
        """执行断言检查"""
        if not target:
            # 没有目标元素时，只检查基本状态
            if assert_type == "url_contains":
                url_match = assert_value in page.url
                return url_match, "" if url_match else f"URL不匹配: 期望包含'{assert_value}'"
            return True, ""  # 无目标元素，跳过断言
        try:
            if assert_type == "visible":
                el = await page.query_selector(target)
                if not el:
                    return False, f"元素不存在: {target}"
                visible = await el.is_visible()
                return visible, "" if visible else f"元素不可见: {target}"

            elif assert_type == "text":
                el = await page.query_selector(target)
                if not el:
                    return False, f"元素不存在: {target}"
                text = (await el.text_content() or "").strip()
                matched = assert_value in text
                return matched, "" if matched else f"文本不匹配: 期望包含'{assert_value}', 实际'{text[:50]}'"

            elif assert_type == "checked":
                el = await page.query_selector(target)
                if not el:
                    return False, f"元素不存在: {target}"
                checked = await el.is_checked()
                return checked, "" if checked else f"元素未勾选: {target}"

            elif assert_type == "url_contains":
                url_match = assert_value in page.url
                return url_match, "" if url_match else f"URL不匹配: 期望包含'{assert_value}', 实际'{page.url}'"

            elif assert_type == "count":
                els = await page.query_selector_all(target)
                expected = int(assert_value)
                actual = len(els)
                return actual == expected, f"数量不匹配: 期望{expected}, 实际{actual}"

            elif assert_type == "disabled":
                el = await page.query_selector(target)
                if not el:
                    return False, f"元素不存在: {target}"
                disabled = await el.is_disabled()
                return disabled, "" if disabled else f"元素未禁用: {target}"

        except Exception as e:
            return False, f"断言执行异常: {str(e)[:100]}"

        return True, ""  # 无断言类型，通过

    async def _take_screenshot(self, page: Page, result: BrowserTestResult):
        """失败时截图"""
        try:
            screenshot_path = SCREENSHOT_DIR / f"task_{result.case_id}_error.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            result.screenshot = str(screenshot_path)
        except Exception:
            pass

    async def navigate(self, url: str, wait_for: str = None, timeout: int = 30000) -> dict:
        """简单导航，用于预浏览"""
        if not self._browser:
            await self.start()
        page = await self._browser.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=timeout)
            title = await page.title()
            url_actual = page.url
            if wait_for:
                await page.wait_for_selector(wait_for, timeout=timeout)
            screenshot_path = SCREENSHOT_DIR / f"preview_{int(time.time())}.png"
            await page.screenshot(path=str(screenshot_path))
            return {"url": url_actual, "title": title, "screenshot": str(screenshot_path)}
        finally:
            await page.close()


def get_browser_executor() -> BrowserTestExecutor:
    """每次调用创建新的浏览器执行器，避免并发问题"""
    return BrowserTestExecutor(headless=True)


async def close_browser_executor(executor=None):
    """关闭指定的浏览器执行器"""
    if executor:
        await executor.stop()
