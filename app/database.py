"""Database configuration with raw SQL for maximum compatibility."""
import os
from pathlib import Path
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text as sa_text
import logging

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
DATABASE_URL = f"sqlite+aiosqlite:///{BASE_DIR / 'testpilot.db'}"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables with proper schema for test management platform."""
    tables = {
        "knowledge": """CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            category TEXT NOT NULL DEFAULT 'general',
            tags TEXT NOT NULL DEFAULT '[]',
            source TEXT NOT NULL DEFAULT '',
            source_url TEXT NOT NULL DEFAULT '',
            meta TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
        )""",
        
        "bugs": """CREATE TABLE IF NOT EXISTS bugs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            severity TEXT NOT NULL DEFAULT 'medium',
            status TEXT NOT NULL DEFAULT 'open',
            module TEXT NOT NULL DEFAULT '',
            priority TEXT NOT NULL DEFAULT 'P2',
            reporter TEXT NOT NULL DEFAULT '',
            assignee TEXT NOT NULL DEFAULT '',
            steps TEXT NOT NULL DEFAULT '',
            expected TEXT NOT NULL DEFAULT '',
            actual TEXT NOT NULL DEFAULT '',
            screenshots TEXT NOT NULL DEFAULT '[]',
            related_cases TEXT NOT NULL DEFAULT '[]',
            resolution TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        
        "test_cases": """CREATE TABLE IF NOT EXISTS test_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            module TEXT NOT NULL DEFAULT '',
            priority TEXT NOT NULL DEFAULT 'P2',
            case_type TEXT NOT NULL DEFAULT 'api',
            automation_type TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'draft',
            is_automated INTEGER NOT NULL DEFAULT 0,
            preconditions TEXT NOT NULL DEFAULT '',
            steps TEXT NOT NULL DEFAULT '[]',
            expected TEXT NOT NULL DEFAULT '',
            api_config TEXT NOT NULL DEFAULT '{}',
            sql_config TEXT NOT NULL DEFAULT '{}',
            browser_config TEXT NOT NULL DEFAULT '{}',
            script_config TEXT NOT NULL DEFAULT '{}',
            tags TEXT NOT NULL DEFAULT '[]',
            owner TEXT NOT NULL DEFAULT '',
            version INTEGER NOT NULL DEFAULT 1,
            suite_id INTEGER,
            source_task_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        
        "test_suites": """CREATE TABLE IF NOT EXISTS test_suites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            module TEXT NOT NULL DEFAULT '',
            priority TEXT NOT NULL DEFAULT 'P2',
            status TEXT NOT NULL DEFAULT 'active',
            owner TEXT NOT NULL DEFAULT '',
            concurrent INTEGER NOT NULL DEFAULT 3,
            config TEXT NOT NULL DEFAULT '{}',
            tags TEXT NOT NULL DEFAULT '[]',
            case_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        
        "test_results": """CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            suite_id INTEGER,
            case_id INTEGER,
            execution_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            duration_ms REAL NOT NULL DEFAULT 0,
            actual_result TEXT NOT NULL DEFAULT '',
            expected_result TEXT NOT NULL DEFAULT '',
            error_message TEXT NOT NULL DEFAULT '',
            screenshots TEXT NOT NULL DEFAULT '[]',
            logs TEXT NOT NULL DEFAULT '',
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )""",
        
        "test_step_results": """CREATE TABLE IF NOT EXISTS test_step_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            result_id INTEGER,
            step_index INTEGER NOT NULL,
            action TEXT NOT NULL DEFAULT '',
            target TEXT NOT NULL DEFAULT '',
            value TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            duration_ms REAL NOT NULL DEFAULT 0,
            actual TEXT NOT NULL DEFAULT '',
            error TEXT NOT NULL DEFAULT '',
            screenshot TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        
        "environments": """CREATE TABLE IF NOT EXISTS environments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            base_url TEXT NOT NULL DEFAULT '',
            type TEXT NOT NULL DEFAULT 'api',
            config TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'active',
            owner TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        
        "test_data": """CREATE TABLE IF NOT EXISTS test_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'fixture',
            suite_id INTEGER,
            data TEXT NOT NULL DEFAULT '{}',
            description TEXT NOT NULL DEFAULT '',
            owner TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        
        "configs": """CREATE TABLE IF NOT EXISTS configs (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT '',
            category TEXT NOT NULL DEFAULT 'system',
            description TEXT NOT NULL DEFAULT '',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        
        "task_executions": """CREATE TABLE IF NOT EXISTS task_executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_type TEXT NOT NULL,
            title TEXT NOT NULL,
            input_data TEXT NOT NULL DEFAULT '{}',
            ai_output TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'running',
            error TEXT NOT NULL DEFAULT '',
            duration_ms REAL NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )""",
        
        "pipelines": """CREATE TABLE IF NOT EXISTS pipelines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            steps TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'inactive',
            owner TEXT NOT NULL DEFAULT '',
            last_run_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        
        "scheduled_jobs": """CREATE TABLE IF NOT EXISTS scheduled_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            job_type TEXT NOT NULL DEFAULT 'pipeline',
            target_id INTEGER,
            cron TEXT NOT NULL DEFAULT '',
            next_run_at TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'active',
            last_run_at TIMESTAMP,
            last_status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        
        "browser_test_results": """CREATE TABLE IF NOT EXISTS browser_test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            url TEXT NOT NULL,
            cases TEXT NOT NULL DEFAULT '[]',
            passed_count INTEGER NOT NULL DEFAULT 0,
            failed_count INTEGER NOT NULL DEFAULT 0,
            total_count INTEGER NOT NULL DEFAULT 0,
            duration_ms REAL NOT NULL DEFAULT 0,
            results TEXT NOT NULL DEFAULT '[]',
            screenshot_dir TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )"""
    }
    
    async with engine.begin() as conn:
        for table_name, schema in tables.items():
            try:
                await conn.execute(sa_text(schema))
                logger.info(f"✅ Table '{table_name}' ready")
            except Exception as e:
                logger.warning(f"⚠️  Table '{table_name}' may already exist: {e}")


async def seed_prompts():
    """Seed default AI prompts."""
    prompts = {
        "generate_cases": "请根据以下需求生成测试用例（JSON格式，包含id/name/precondition/steps/expected）：\n\n{requirement}",
        "analyze_bug": "请分析以下bug描述，提供结构化报告：\n\n{description}",
        "troubleshoot_logs": "请分析以下日志，找出问题根因：\n\n{logs}",
        "analyze_sql": "请分析以下SQL查询，优化性能：\n\n{sql}",
        "write_report": "请根据以下测试结果生成测试报告：\n\n{test_results}",
        "regression": "请分析代码变更，确定回归测试范围：\n\n{code_changes}",
        "web_ui_test": "请根据以下需求生成UI自动化测试用例（Playwright JSON格式）：\n\n{requirement}",
        "ai_test_generation": "请根据以下需求智能生成测试用例和测试脚本：\n\n{requirement}"
    }
    
    async with engine.begin() as conn:
        for key, prompt in prompts.items():
            try:
                await conn.execute(
                    sa_text("INSERT OR IGNORE INTO configs (key, value, category, description) VALUES (:key, :value, :category, :description)"),
                    {"key": f"prompt_{key}", "value": prompt, "category": "prompts", "description": f"{key} prompt template"}
                )
                logger.info(f"✅ Prompt '{key}' seeded")
            except Exception as e:
                logger.warning(f"⚠️  Prompt '{key}' seed failed: {e}")


# 导出数据库会话工厂
db_factory = AsyncSessionLocal
