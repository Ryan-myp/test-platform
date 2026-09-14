"""缺陷管理模型"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from app.database import Base
from datetime import datetime, timezone


def now_str():
    return datetime.now(timezone.utc).isoformat()


class Bug(Base):
    __tablename__ = "bugs"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, default="")
    severity = Column(String(20), default="medium")  # critical/major/minor/trivial
    priority = Column(String(10), default="P2")
    
    # 状态
    status = Column(String(20), default="open")  # open/confirmed/fixed/closed/duplicate
    type = Column(String(20), default="bug")  # bug/feature/improvement
    
    # 关联
    related_case_ids = Column(JSON, default=[])
    related_run_ids = Column(JSON, default=[])
    fixed_in_version = Column(String(50), default="")
    
    # 外部系统
    external_id = Column(String(100), default="")  # Jira/禅道 ID
    external_url = Column(String(500), default="")
    
    # 处理信息
    assignee = Column(String(100), default="")
    reporter = Column(String(100), default="")
    resolved_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    
    # 截图和日志
    screenshots = Column(JSON, default=[])
    logs = Column(Text, default="")
    
    created_at = Column(DateTime, default=now_str)
    updated_at = Column(DateTime, default=now_str)
    
    def to_dict(self):
        return {
            "id": self.id, "title": self.title, "severity": self.severity,
            "status": self.status, "priority": self.priority,
            "assignee": self.assignee, "reporter": self.reporter,
            "external_id": self.external_id,
            "related_case_ids": self.related_case_ids or [],
            "created_at": self.created_at, "resolved_at": self.resolved_at
        }
