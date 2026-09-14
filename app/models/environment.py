"""测试环境模型"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from app.database import Base
from datetime import datetime, timezone


def now_str():
    return datetime.now(timezone.utc).isoformat()


class Environment(Base):
    __tablename__ = "environments"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(100), default="")
    description = Column(Text, default="")
    
    # 配置
    config = Column(JSON, default={})  # 环境配置
    base_url = Column(String(500), default="")
    api_key = Column(String(500), default="")
    
    # 状态
    status = Column(String(20), default="active")  # active/inactive/maintenance
    
    # 连接测试
    health_check = Column(String(20), default="unknown")
    last_check_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=now_str)
    
    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "display_name": self.display_name,
            "base_url": self.base_url, "status": self.status,
            "health_check": self.health_check,
            "last_check_at": self.last_check_at
        }
