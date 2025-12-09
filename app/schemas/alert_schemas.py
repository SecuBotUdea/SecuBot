# -*- coding: utf-8 -*-
"""
Alert Schemas - API contracts for Alert endpoints
"""
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class AlertBase(BaseModel):
    """Base alert schema with common fields"""
    signature: str = Field(..., description='Unique signature of the finding')
    source_id: str = Field(..., description='Source that generated the alert')
    severity: str = Field(..., description='Alert severity (CRITICAL/HIGH/MEDIUM/LOW/INFO)')
    component: str = Field(..., description='Affected component or module')
    quality: str = Field(..., description='Quality or confidence level')
    normalized_payload: dict[str, Any] = Field(
        default_factory=dict, description='Normalized payload independent of source'
    )


class AlertCreate(AlertBase):
    """Schema for creating a new alert"""
    alert_id: str = Field(..., description='Unique alert identifier')
    status: str = Field(default='open', description='Alert status')
    
    # 🆕 Campos opcionales con defaults - el router los llenará si no vienen
    first_seen: datetime | None = Field(None, description='First detection timestamp')
    last_seen: datetime | None = Field(None, description='Last seen timestamp')
    created_at: datetime | None = Field(None)
    updated_at: datetime | None = Field(None)
    lifecycle_history: list[dict[str, Any]] = Field(
        default_factory=list, description='Lifecycle event history'
    )
    reopen_count: int = Field(default=0, description='Number of times reopened')
    last_reopened_at: datetime | None = Field(None, description='Last reopened timestamp')
    version: int = Field(default=1, description='Version number')


class AlertUpdate(BaseModel):
    """Schema for updating an alert (all fields optional)"""
    status: str | None = Field(None, description='Alert status')
    severity: str | None = Field(None, description='Alert severity')
    component: str | None = Field(None, description='Affected component')
    quality: str | None = Field(None, description='Quality level')
    normalized_payload: dict[str, Any] | None = Field(None, description='Normalized payload')


class AlertResponse(AlertBase):
    """Schema for alert responses"""
    alert_id: str = Field(..., description='Unique alert identifier')
    status: str = Field(..., description='Alert lifecycle status')
    first_seen: datetime = Field(..., description='First detection timestamp')
    last_seen: datetime = Field(..., description='Last seen timestamp')
    lifecycle_history: list[dict[str, Any]] = Field(
        default_factory=list, description='Lifecycle event history'
    )
    reopen_count: int = Field(default=0, description='Number of times reopened')
    last_reopened_at: datetime | None = Field(None, description='Last reopened timestamp')
    version: int = Field(default=1, description='Version number')
    created_at: datetime = Field(..., description='Creation timestamp')
    updated_at: datetime = Field(..., description='Last update timestamp')

    class Config:
        from_attributes = True


class AlertListFilter(BaseModel):
    """Filters for listing alerts"""
    severity: str | None = Field(None, description='Filter by severity')
    status: str | None = Field(None, description='Filter by status')
    source_id: str | None = Field(None, description='Filter by source')
    component: str | None = Field(None, description='Filter by component')


class AlertStatusUpdate(BaseModel):
    """Schema for updating alert status"""
    status: str = Field(..., description='New status')
    reason: str | None = Field(None, description='Reason for status change')
