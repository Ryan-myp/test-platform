"""测试用例模型"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime, timezone


def now_str():
    return datetime.now(timezone.utc).isoformat()


class TestCase(Base):
    __tablename__ = "test_cases"
    
    id = Column(Integer, primary_key=True, index=True)
    suite_id = Column(Integer, ForeignKey("test_suites.id"), nullable=True)
    name = Column(String(255), nullable=False, index=True)
    module = Column(String(100), default="")
    priority = Column(String(10), default="P2")  # P0/P1/P2/P3
    
    # 用例内容
    precondition = Column(Text, default="")  # 前置条件
    steps = Column(Text, default="")  # 步骤 (JSON array)
    expected = Column(Text, default="")  # 预期结果
    actual = Column(Text, default="")  # 实际结果
    
    # 用例类型
    case_type = Column(String(20), default="manual")  # manual/api/browser/sql/script
    api_config = Column(JSON, default={})  # API测试配置
    sql_config = Column(JSON, default={})  # SQL测试配置
    browser_config = Column(JSON, default={})  # 浏览器测试配置
    
    # 状态管理
    status = Column(String(20), default="draft")  # draft/active/archived
    is_automated = Column(Boolean, default=False)
    automation_type = Column(String(20), default="")  # api/sql/browser/script
    
    # 标签和关联
    tags = Column(JSON, default=[])
    related_bugs = Column(JSON, default=[])
    related_requirements = Column(JSON, default=[])
    
    # 统计
    run_count = Column(Integer, default=0)
    pass_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    
    # 元数据
    owner = Column(String(100), default="")
    creator = Column(String(100), default="")
    description = Column(Text, default="")
    version = Column(String(20), default="1.0.0")
    
    created_at = Column(DateTime, default=now_str)
    updated_at = Column(DateTime, default=now_str, onupdate=now_str)
    
    # 关联
    suite = relationship("TestSuite", back_populates="cases")
    results = relationship("TestResult", back_populates="case", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": self.id, "suite_id": self.suite_id,
            "name": self.name, "module": self.module,
            "priority": self.priority, "status": self.status,
            "case_type": self.case_type, "is_automated": self.is_automated,
            "tags": self.tags or [], "owner": self.owner,
            "run_count": self.run_count, "pass_count": self.pass_count,
            "fail_count": self.fail_count,
            "version": self.version, "created_at": self.created_at,
            "updated_at": self.updated_at
        }
