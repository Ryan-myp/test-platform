"""数据库层：SQLite + SQLAlchemy"""
import json
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import text
from loguru import logger
from app.config import settings

Base = declarative_base()
engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

now_str = lambda: datetime.now(timezone.utc).isoformat()

class ApiTestResult(Base):
    __tablename__ = "api_test_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int]
    url: Mapped[str]
    method: Mapped[str]
    status_code: Mapped[int] = mapped_column(default=0)
    response_time_ms: Mapped[float] = mapped_column(default=0.0)
    body: Mapped[str] = mapped_column(default="")
    passed: Mapped[int] = mapped_column(default=0)
    error: Mapped[str] = mapped_column(default="")
    created_at: Mapped[str] = mapped_column(default=now_str)

class SqlExecResult(Base):
    __tablename__ = "sql_exec_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int]
    sql: Mapped[str]
    rows_affected: Mapped[int] = mapped_column(default=0)
    result_data: Mapped[str] = mapped_column(default="[]")
    execution_time_ms: Mapped[float] = mapped_column(default=0.0)
    error: Mapped[str] = mapped_column(default="")
    created_at: Mapped[str] = mapped_column(default=now_str)


async def _exec(session, sql, params=None):
    r = await session.execute(text(sql), params or {})
    await session.commit()
    return r


async def init_db():
    """用原始 SQL 建表，确保所有 NOT NULL 列都有默认值"""
    tables = {
        "knowledge": """CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            tags TEXT NOT NULL DEFAULT '[]',
            meta TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
        )""",
        "bugs": """CREATE TABLE IF NOT EXISTS bugs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            severity TEXT NOT NULL DEFAULT 'P2',
            status TEXT NOT NULL DEFAULT 'open',
            error_log TEXT NOT NULL DEFAULT '',
            trace_id TEXT NOT NULL DEFAULT '',
            environment TEXT NOT NULL DEFAULT '',
            related_case_ids TEXT NOT NULL DEFAULT '[]',
            root_cause TEXT NOT NULL DEFAULT '',
            fix_suggestion TEXT NOT NULL DEFAULT '',
            source_task_id INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now','utc')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
        )""",
        "test_cases": """CREATE TABLE IF NOT EXISTS test_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            module TEXT NOT NULL DEFAULT '',
            priority TEXT NOT NULL DEFAULT 'P2',
            precondition TEXT NOT NULL DEFAULT '',
            steps TEXT NOT NULL DEFAULT '',
            expected TEXT NOT NULL DEFAULT '',
            tags TEXT NOT NULL DEFAULT '[]',
            source_task_id INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
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
            created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
        )""",
        "task_executions": """CREATE TABLE IF NOT EXISTS task_executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_type TEXT NOT NULL,
            title TEXT NOT NULL,
            input_data TEXT NOT NULL DEFAULT '{}',
            ai_output TEXT NOT NULL DEFAULT '',
            auto_exec_result TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'pending',
            linked_task_ids TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL DEFAULT (datetime('now','utc')),
            completed_at TEXT
        )""",
        "pipelines": """CREATE TABLE IF NOT EXISTS pipelines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            steps TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'idle',
            current_step INTEGER NOT NULL DEFAULT 0,
            results TEXT NOT NULL DEFAULT '{}',
            triggered_by TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now','utc')),
            completed_at TEXT
        )""",
        "scheduled_jobs": """CREATE TABLE IF NOT EXISTS scheduled_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            entry_type TEXT NOT NULL,
            schedule_expr TEXT NOT NULL,
            last_run_at TEXT,
            next_run_at TEXT,
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
        )""",
        "configs": """CREATE TABLE IF NOT EXISTS configs (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT '{}'
        )""",
    }
    
    async with AsyncSessionLocal() as session:
        for table_name, create_sql in tables.items():
            try:
                await session.execute(text(create_sql))
                await session.commit()
                logger.info(f"✅ Table '{table_name}' ready")
            except Exception as e:
                logger.warning(f"⚠️ Table '{table_name}' may already exist: {e}")


async def seed_prompts(session):
    """初始化 AI Prompt 模板"""
    prompts = {
        "generate_cases": "你是资深测试工程师。根据需求生成测试用例。覆盖正常/异常/边界/安全场景，输出表格（编号/前置条件/步骤/预期/优先级）。需求：{requirement}，优先级：{priority}，模块：{module}",
        "analyze_bug": "你是资深测试工程师。分析 Bug 根因。输出：现象还原、根因推断、验证方案、修复建议、相似历史Bug。现象：{description}，日志：{error_log}，TraceID：{trace_id}，环境：{environment}",
        "troubleshoot_logs": "你是资深测试工程师。分析日志定位问题。输出：调用链路图、错误环节、根因推断、排查建议。日志：{log_snippet}，TraceID：{trace_id}，时间范围：{time_range}",
        "analyze_sql": "你是资深测试工程师。分析 SQL 性能与规范。输出：语法检查、性能风险、安全审查、优化建议。SQL：{sql}，场景：{scenario}，期望：{expected}",
        "generate_report": "你是测试负责人。根据数据生成标准测试报告。输出：测试概况、通过率、风险评估、上线建议。轮次：{round}，总用例：{total_cases}，通过：{passed}，失败：{failed}，Bug：{bug_stats}",
        "regression": "你是测试工程师。根据变更生成回归测试清单。输出：影响分析、受影响用例、新增用例建议。变更：{change_description}，影响范围：{impact_scope}，已有用例：{existing_cases}",
    }
    
    result = await session.execute(text("SELECT key FROM configs WHERE key = 'prompts'"))
    if not result.fetchone():
        await session.execute(
            text("INSERT INTO configs (key, value) VALUES (:key, :value)"),
            {"key": "prompts", "value": json.dumps(prompts, ensure_ascii=False)}
        )
        await session.commit()
        logger.info("✅ Prompts seeded")


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
