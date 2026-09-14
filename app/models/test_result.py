"""测试执行结果模型"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime, timezone


def now_str():
    return datetime.now(timezone.utc).isoformat()


class TestResult(Base):
    __tablename__ = "test_results"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("test_cases.id"), nullable=True)
    suite_id = Column(Integer, ForeignKey("test_suites.id"), nullable=True)
    run_id = Column(String(50), nullable=False)  # 批次ID
    
    # 执行信息
    status = Column(String(20), default="pending")  # pending/running/pass/fail/skip/error
    started_at = Column(DateTime, default=now_str)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, default=0)
    
    # 结果
    expected = Column(Text, default="")
    actual = Column(Text, default="")
    error_message = Column(Text, default="")
    screenshot_path = Column(String(500), default="")
    
    # 步骤详情
    steps = Column(JSON, default=[])
    
    # 执行环境
    environment = Column(String(50), default="")
    executor = Column(String(100), default="")  # 执行人/系统
    
    created_at = Column(DateTime, default=now_str)
    
    # 关联
    case = relationship("TestCase", back_populates="results")
    step_results = relationship("TestStepResult", back_populates="result", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": self.id, "case_id": self.case_id, "suite_id": self.suite_id,
            "run_id": self.run_id, "status": self.status,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "screenshot_path": self.screenshot_path,
            "environment": self.environment,
            "started_at": self.started_at,
            "completed_at": self.completed_at
        }


class TestStepResult(Base):
    __tablename__ = "test_step_results"
    
    id = Column(Integer, primary_key=True, index=True)
    result_id = Column(Integer, ForeignKey("test_results.id"), nullable=True)
    step_index = Column(Integer, default=0)
    step_name = Column(String(255), default="")
    status = Column(String(20), default="pending")
    duration_ms = Column(Integer, default=0)
    expected = Column(Text, default="")
    actual = Column(Text, default="")
    error = Column(Text, default="")
    screenshot = Column(String(500), default="")
    
    created_at = Column(DateTime, default=now_str)
    
    result = relationship("TestResult", back_populates="step_results")
    
    def to_dict(self):
        return {
            "id": self.id, "step_index": self.step_index,
            "step_name": self.step_name, "status": self.status,
            "duration_ms": self.duration_ms,
            "error": self.error
        }
