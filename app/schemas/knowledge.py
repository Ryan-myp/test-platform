"""Knowledge schemas"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class KnowledgeBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    category: str = Field(default="general", max_length=100)
    tags: List[str] = Field(default_factory=list)
    source: str = ""
    source_url: str = ""


class KnowledgeCreate(KnowledgeBase):
    pass


class KnowledgeUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    source: Optional[str] = None
    source_url: Optional[str] = None


class KnowledgeOut(KnowledgeBase):
    id: int
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
