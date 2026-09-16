"""Test case schemas"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime


class TestCaseBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    module: str = Field(default="", max_length=100)
    priority: str = Field(default="P2", pattern=r"^P[0-3]$")
    case_type: str = Field(default="api", pattern=r"^(api|sql|browser|manual)$")
    status: str = Field(default="draft", pattern=r"^(draft|active|archived)$")
    preconditions: str = ""
    steps: str = ""
    expected: str = ""
    api_config: Optional[Dict[str, Any]] = None
    suite_id: Optional[int] = None
    owner: str = ""


class TestCaseCreate(TestCaseBase):
    pass


class TestCaseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    module: Optional[str] = Field(None, max_length=100)
    priority: Optional[str] = Field(None, pattern=r"^P[0-3]$")
    case_type: Optional[str] = Field(None, pattern=r"^(api|sql|browser|manual)$")
    status: Optional[str] = Field(None, pattern=r"^(draft|active|archived)$")
    preconditions: Optional[str] = None
    steps: Optional[str] = None
    expected: Optional[str] = None
    api_config: Optional[Dict[str, Any]] = None
    suite_id: Optional[int] = None
    owner: Optional[str] = None


class TestCaseOut(TestCaseBase):
    id: int
    is_automated: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
