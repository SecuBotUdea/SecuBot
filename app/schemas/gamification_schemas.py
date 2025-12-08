# -*- coding: utf-8 -*-
"""
Gamification Schemas - API contracts for Points, Badges, and Awards
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ============================================
# POINT TRANSACTION SCHEMAS
# ============================================


class PointTransactionBase(BaseModel):
    """Base point transaction schema"""

    user_id: str = Field(..., description='User receiving points')
    points: int = Field(..., description='Points awarded (positive) or deducted (negative)')
    reason: str = Field(..., description='Reason for point transaction')
    alert_id: str | None = Field(None, description='Related alert if applicable')


class PointTransactionCreate(PointTransactionBase):
    """Schema for creating a point transaction"""

    team_id: str = Field(..., description='Team reference')
    rule_id: str = Field(..., description='Rule that triggered the transaction')
    evidence_refs: list[str] = Field(default_factory=list, description='Supporting evidence')


class PointTransactionResponse(PointTransactionBase):
    """Schema for point transaction responses"""

    team_id: str = Field(..., description='Team reference')
    rule_id: str = Field(..., description='Rule that triggered the transaction')
    timestamp: datetime = Field(..., description='Transaction timestamp')
    evidence_refs: list[str] = Field(default_factory=list, description='Supporting evidence')
    penalty_reason: str | None = Field(None, description='Penalty reason if applicable')
    created_at: datetime = Field(..., description='Creation timestamp')

    class Config:
        from_attributes = True


# ============================================
# BADGE SCHEMAS
# ============================================


class BadgeBase(BaseModel):
    """Base badge schema"""

    name: str = Field(..., description='Badge name')
    description: str = Field(..., description='Badge description')
    icon_url: str = Field(..., description='Badge icon URL')
    category: str = Field(..., description='Badge category')


class BadgeCreate(BadgeBase):
    """Schema for creating a badge"""

    badge_id: str = Field(..., description='Unique badge identifier')
    criteria_ref: dict[str, Any] = Field(
        default_factory=dict, description='Badge criteria definition'
    )
    active: bool = Field(default=True, description='Whether badge is active')


class BadgeUpdate(BaseModel):
    """Schema for updating a badge"""

    name: str | None = Field(None, description='Badge name')
    description: str | None = Field(None, description='Badge description')
    icon_url: str | None = Field(None, description='Badge icon URL')
    category: str | None = Field(None, description='Badge category')
    active: bool | None = Field(None, description='Whether badge is active')


class BadgeResponse(BadgeBase):
    """Schema for badge responses"""

    badge_id: str = Field(..., description='Unique badge identifier')
    criteria_ref: dict[str, Any] = Field(..., description='Badge criteria definition')
    active: bool = Field(..., description='Whether badge is active')
    created_at: datetime = Field(..., description='Creation timestamp')
    updated_at: datetime = Field(..., description='Last update timestamp')

    class Config:
        from_attributes = True


# ============================================
# AWARD SCHEMAS
# ============================================


class AwardBase(BaseModel):
    """Base award schema"""

    user_id: str = Field(..., description='User receiving the award')
    badge_id: str = Field(..., description='Badge being awarded')


class AwardCreate(AwardBase):
    """Schema for creating an award"""

    reason: str | None = Field(None, description='Reason for awarding badge')
    metadata: dict[str, Any] = Field(default_factory=dict, description='Additional award metadata')


class AwardResponse(AwardBase):
    """Schema for award responses"""

    awarded_at: datetime = Field(..., description='Award timestamp')
    reason: str | None = Field(None, description='Reason for awarding badge')
    metadata: dict[str, Any] = Field(default_factory=dict, description='Additional award metadata')

    class Config:
        from_attributes = True


# ============================================
# LEADERBOARD SCHEMAS
# ============================================


class LeaderboardEntry(BaseModel):
    """Single leaderboard entry"""

    rank: int = Field(..., description='Rank position')
    username: str = Field(..., description='Username')
    display_name: str = Field(..., description='Display name')
    total_points: int = Field(..., description='Total points earned')
    alerts_remediated: int = Field(default=0, description='Alerts remediated')
    badges_count: int = Field(default=0, description='Number of badges earned')
    level: int = Field(default=1, description='User level')


class LeaderboardResponse(BaseModel):
    """Leaderboard response"""

    entries: list[LeaderboardEntry] = Field(..., description='Leaderboard entries')
    period: str = Field(..., description='Leaderboard period (weekly/monthly/all-time)')
    updated_at: datetime = Field(..., description='Last update timestamp')


# ============================================
# GAMIFICATION STATS
# ============================================


class GamificationStats(BaseModel):
    """Overall gamification statistics"""

    total_users: int = Field(..., description='Total active users')
    total_points_awarded: int = Field(..., description='Total points awarded')
    total_badges_earned: int = Field(..., description='Total badges earned')
    total_alerts_remediated: int = Field(..., description='Total alerts remediated')
    average_success_rate: float = Field(..., description='Average remediation success rate')
