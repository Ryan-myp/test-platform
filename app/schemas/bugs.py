"""Bug schemas"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class BugBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str = ""
    severity: str = Field(default="medium", pattern=r"^(critical|major|minor|trivial)$")
    status: str = Field(default="open", pattern=r"^(open|investigating|fixed|closed|wontfix)$")
    module: str = ""
    priority: str = Field(default="P2", pattern=r"^P[0-3]$")
    reporter: str = ""
    assignee: str = ""
    steps: str = ""
    expected: str = ""
    actual: str = ""
    screenshots: List[str] = []


class BugCreate(BugBase):
    pass


class BugUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    module: Optional[str] = None
    priority: Optional[str] = None
    reporter: Optional[str] = None
    assignee: Optional[str] = None
    steps: Optional[str] = None
    expected: Optional[str] = None
    actual: Optional[str] = None
    screenshots: Optional[List[str]] = None
    resolution: Optional[str] = None


class BugOut(BugBase):
    id: int
    resolution: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
