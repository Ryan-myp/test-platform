"""测试数据模型"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from app.database import Base
from datetime import datetime, timezone


def now_str():
    return datetime.now(timezone.utc).isoformat()


class TestData(Base):
    __tablename__ = "test_data"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    
    # 数据类型
    data_type = Column(String(20), default="json")  # json/csv/sql/fixture
    
    # 数据内容
    data = Column(Text, default="")
    data_config = Column(JSON, default={})
    
    # 关联
    suite_ids = Column(JSON, default=[])
    case_ids = Column(JSON, default=[])
    
    # 状态
    status = Column(String(20), default="active")
    
    creator = Column(String(100), default="")
    version = Column(String(20), default="1.0.0")
    
    created_at = Column(DateTime, default=now_str)
    updated_at = Column(DateTime, default=now_str)
    
    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "data_type": self.data_type,
            "status": self.status, "creator": self.creator,
            "version": self.version, "created_at": self.created_at
        }
