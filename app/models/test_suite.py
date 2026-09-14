"""测试套件模型"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime, timezone


def now_str():
    return datetime.now(timezone.utc).isoformat()


class TestSuite(Base):
    __tablename__ = "test_suites"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    module = Column(String(100), default="")
    priority = Column(String(10), default="P1")
    
    # 执行配置
    concurrent = Column(Integer, default=1)  # 并发数
    retry_count = Column(Integer, default=0)  # 重试次数
    timeout_seconds = Column(Integer, default=300)
    
    # 状态
    status = Column(String(20), default="active")  # active/archived
    
    # 统计
    total_cases = Column(Integer, default=0)
    pass_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    last_run_at = Column(DateTime, nullable=True)
    
    owner = Column(String(100), default="")
    tags = Column(String(500), default="")
    
    created_at = Column(DateTime, default=now_str)
    updated_at = Column(DateTime, default=now_str)
    
    cases = relationship("TestCase", back_populates="suite", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "module": self.module, "priority": self.priority,
            "status": self.status, "concurrent": self.concurrent,
            "total_cases": self.total_cases,
            "pass_rate": f"{self.pass_count/(self.pass_count+self.fail_count)*100:.1f}%" if (self.pass_count+self.fail_count) > 0 else "0%",
            "last_run_at": self.last_run_at,
            "created_at": self.created_at
        }
