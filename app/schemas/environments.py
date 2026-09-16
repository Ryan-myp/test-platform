"""Environment schemas"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class EnvironmentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    base_url: str = Field(..., min_length=1)
    type: str = Field(default="development", pattern=r"^(development|testing|staging|production)$")
    config: Dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="active", pattern=r"^(active|inactive)$")
    owner: str = ""


class EnvironmentCreate(EnvironmentBase):
    pass


class EnvironmentUpdate(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    type: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    owner: Optional[str] = None


class EnvironmentOut(EnvironmentBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
