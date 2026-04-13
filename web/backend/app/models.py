"""
数据库模型
"""
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


class User(BaseModel):
    """用户模型"""
    id: Optional[int] = None
    google_id: str = Field(..., unique=True, index=True)
    email: str = Field(..., unique=True, index=True)
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserCreate(BaseModel):
    """创建用户时使用的模型"""
    google_id: str
    email: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None


class Token(BaseModel):
    """JWT Token 响应"""
    access_token: str
    token_type: str = "bearer"
    user: User


class TokenData(BaseModel):
    """Token 中包含的数据"""
    user_id: int
    email: str
