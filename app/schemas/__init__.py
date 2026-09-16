"""Pydantic v2 schemas for request/response validation"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Any, Dict, List, Optional, Generic, TypeVar
from datetime import datetime

T = TypeVar("T")

class ApiResponse(BaseModel):
    """统一响应格式"""
    success: bool
    message: str = "OK"
    data: Optional[Any] = None
    errors: Optional[List[str]] = None
    meta: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})

class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    
    @classmethod
    def from_data(cls, items: List[T], total: int, page: int, page_size: int):
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size
        )

class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    message: str
    errors: Optional[List[Dict[str, Any]]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

# 导入具体模型
from .test_cases import TestCaseCreate, TestCaseUpdate, TestCaseOut
from .bugs import BugCreate, BugUpdate, BugOut
from .knowledge import KnowledgeCreate, KnowledgeUpdate, KnowledgeOut
from .environments import EnvironmentCreate, EnvironmentUpdate, EnvironmentOut
