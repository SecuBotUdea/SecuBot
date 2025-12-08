# -*- coding: utf-8 -*-
"""
User Schemas - API contracts for User endpoints
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema with common fields"""

    username: str = Field(..., min_length=3, max_length=50, description='Unique username')
    display_name: str = Field(..., max_length=100, description='Display name')
    email: EmailStr = Field(..., description='Email address')
    role: str = Field(default='member', description='User role')
    team_id: str | None = Field(None, description='Team reference')


class UserCreate(UserBase):
    """Schema for creating a new user"""

    metadata: dict[str, Any] = Field(default_factory=dict, description='Additional user metadata')


class UserUpdate(BaseModel):
    """Schema for updating a user (all fields optional)"""

    display_name: str | None = Field(None, max_length=100, description='Display name')
    email: EmailStr | None = Field(None, description='Email address')
    role: str | None = Field(None, description='User role')
    team_id: str | None = Field(None, description='Team reference')
    is_active: bool | None = Field(None, description='Active status')
    metadata: dict[str, Any] | None = Field(None, description='Additional metadata')


class UserResponse(UserBase):
    """Schema for user responses"""

    is_active: bool = Field(..., description='Whether user is active')
    metadata: dict[str, Any] = Field(default_factory=dict, description='Additional user metadata')
    created_at: datetime = Field(..., description='Creation timestamp')
    updated_at: datetime = Field(..., description='Last update timestamp')

    class Config:
        from_attributes = True


class UserListFilter(BaseModel):
    """Filters for listing users"""

    role: str | None = Field(None, description='Filter by role')
    team_id: str | None = Field(None, description='Filter by team')
    is_active: bool | None = Field(None, description='Filter by active status')


class UserStatsResponse(BaseModel):
    """Schema for user statistics"""

    username: str = Field(..., description='Username')
    total_points: int = Field(default=0, description='Total points earned')
    alerts_remediated: int = Field(default=0, description='Number of alerts remediated')
    success_rate: float = Field(default=0.0, description='Remediation success rate')
    badges_earned: int = Field(default=0, description='Number of badges earned')
    level: int = Field(default=1, description='User level')
