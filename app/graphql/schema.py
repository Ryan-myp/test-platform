"""GraphQL schema for flexible queries"""
import strawberry
from typing import List, Optional
from datetime import datetime
from app.models.test_case import TestCase
from app.models.bug import Bug
from app.models.test_suite import TestSuite
from app.cache.stats import stats_cache


@strawberry.type
class TestCaseType:
    id: int
    name: str
    module: str
    priority: str
    case_type: str
    status: str
    owner: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@strawberry.type
class BugType:
    id: int
    title: str
    description: str
    severity: str
    status: str
    module: str
    priority: str
    reporter: str
    assignee: str
    created_at: Optional[datetime] = None


@strawberry.type
class TestSuiteType:
    id: int
    name: str
    description: str
    module: str
    priority: str
    status: str


@strawberry.type
class Query:
    @strawberry.field
    async def test_cases(
        self,
        module: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[TestCaseType]:
        """查询测试用例"""
        from app.database import AsyncSessionLocal, sa_text
        
        async with AsyncSessionLocal() as session:
            sql = "SELECT id, name, module, priority, case_type, status, owner, created_at, updated_at FROM test_cases WHERE 1=1"
            params = {}
            
            if module:
                sql += " AND module = :module"
                params["module"] = module
            if priority:
                sql += " AND priority = :priority"
                params["priority"] = priority
            if status:
                sql += " AND status = :status"
                params["status"] = status
            
            sql += " ORDER BY id DESC LIMIT :limit OFFSET :offset"
            params["limit"] = limit
            params["offset"] = offset
            
            result = await session.execute(sa_text(sql), params)
            rows = result.fetchall()
            
            return [
                TestCaseType(
                    id=row[0],
                    name=row[1],
                    module=row[2] or "",
                    priority=row[3] or "P2",
                    case_type=row[4] or "api",
                    status=row[5] or "draft",
                    owner=row[6] or "",
                    created_at=row[7],
                    updated_at=row[8]
                )
                for row in rows
            ]
    
    @strawberry.field
    async def bugs(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 20
    ) -> List[BugType]:
        """查询 Bug"""
        from app.database import AsyncSessionLocal, sa_text
        
        async with AsyncSessionLocal() as session:
            sql = "SELECT id, title, description, severity, status, module, priority, reporter, assignee, created_at FROM bugs WHERE 1=1"
            params = {}
            
            if status:
                sql += " AND status = :status"
                params["status"] = status
            if severity:
                sql += " AND severity = :severity"
                params["severity"] = severity
            
            sql += " ORDER BY id DESC LIMIT :limit"
            params["limit"] = limit
            
            result = await session.execute(sa_text(sql), params)
            rows = result.fetchall()
            
            return [
                BugType(
                    id=row[0],
                    title=row[1],
                    description=row[2] or "",
                    severity=row[3] or "medium",
                    status=row[4] or "open",
                    module=row[5] or "",
                    priority=row[6] or "P2",
                    reporter=row[7] or "",
                    assignee=row[8] or "",
                    created_at=row[9]
                )
                for row in rows
            ]
    
    @strawberry.field
    async def dashboard_stats(self) -> dict:
        """获取仪表盘统计"""
        from app.api.stats import get_dashboard_stats
        return await get_dashboard_stats()
    
    @strawberry.field
    async def test_suite(self, id: int) -> Optional[TestSuiteType]:
        """获取单个测试套件"""
        from app.database import AsyncSessionLocal, sa_text
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                sa_text("SELECT id, name, description, module, priority, status FROM test_suites WHERE id = :id"),
                {"id": id}
            )
            row = result.fetchone()
            
            if not row:
                return None
            
            return TestSuiteType(
                id=row[0],
                name=row[1],
                description=row[2] or "",
                module=row[3] or "",
                priority=row[4] or "P2",
                status=row[5] or "active"
            )


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_test_case(
        self,
        name: str,
        module: str,
        priority: str = "P2",
        case_type: str = "api"
    ) -> TestCaseType:
        """创建测试用例"""
        from app.api.test_cases import create_test_case
        from app.database import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            result = await create_test_case(session, {
                "name": name,
                "module": module,
                "priority": priority,
                "case_type": case_type,
                "status": "draft"
            })
            
            return TestCaseType(
                id=result["id"],
                name=result["name"],
                module=result.get("module", ""),
                priority=result.get("priority", "P2"),
                case_type=result.get("case_type", "api"),
                status=result.get("status", "draft"),
                owner=result.get("owner", ""),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
    
    @strawberry.mutation
    async def update_bug_status(
        self,
        bug_id: int,
        status: str
    ) -> BugType:
        """更新 Bug 状态"""
        from app.api.bugs import update_bug
        from app.database import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            result = await update_bug(session, bug_id, {"status": status})
            
            return BugType(
                id=result["id"],
                title=result["title"],
                description=result.get("description", ""),
                severity=result.get("severity", "medium"),
                status=result.get("status", status),
                module=result.get("module", ""),
                priority=result.get("priority", "P2"),
                reporter=result.get("reporter", ""),
                assignee=result.get("assignee", ""),
                created_at=result.get("created_at")
            )


# 创建 schema
schema = strawberry.Schema(query=Query, mutation=Mutation)