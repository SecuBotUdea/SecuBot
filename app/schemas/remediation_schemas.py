# -*- coding: utf-8 -*-
"""
Remediation Schemas - API contracts for Remediation endpoints
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RemediationBase(BaseModel):
    """Base remediation schema with common fields"""

    alert_id: str = Field(..., description='Alert being remediated')
    user_id: str = Field(..., description='User performing remediation')
    team_id: str = Field(..., description='Team responsible')
    type: str = Field(..., description='Type of remediation action')
    notes: str | None = Field(None, description='Additional notes or comments')


class RemediationCreate(RemediationBase):
    """Schema for creating a new remediation"""

    remediation_id: str = Field(..., description='Unique remediation identifier')
    metadata: dict[str, Any] = Field(default_factory=dict, description='Additional metadata')


class RemediationUpdate(BaseModel):
    """Schema for updating a remediation (all fields optional)"""

    status: str | None = Field(None, description='Remediation status')
    notes: str | None = Field(None, description='Additional notes')
    metadata: dict[str, Any] | None = Field(None, description='Additional metadata')


class RemediationResponse(RemediationBase):
    """Schema for remediation responses"""

    remediation_id: str = Field(..., description='Unique remediation identifier')
    action_ts: datetime = Field(..., description='Timestamp of the remediation action')
    status: str = Field(..., description='Current status')
    metadata: dict[str, Any] = Field(default_factory=dict, description='Additional metadata')
    created_at: datetime = Field(..., description='Creation timestamp')
    updated_at: datetime = Field(..., description='Last update timestamp')

    class Config:
        from_attributes = True


class RemediationListFilter(BaseModel):
    """Filters for listing remediations"""

    alert_id: str | None = Field(None, description='Filter by alert')
    user_id: str | None = Field(None, description='Filter by user')
    team_id: str | None = Field(None, description='Filter by team')
    status: str | None = Field(None, description='Filter by status')
    type: str | None = Field(None, description='Filter by type')


class RemediationStatusUpdate(BaseModel):
    """Schema for updating remediation status"""

    status: str = Field(..., description='New status')
    reason: str | None = Field(None, description='Reason for status change')
    metadata: dict[str, Any] | None = Field(None, description='Additional metadata')


class RemediationVerificationRequest(BaseModel):
    """Schema for requesting remediation verification"""

    remediation_id: str = Field(..., description='Remediation to verify')
    trigger_rescan: bool = Field(default=True, description='Whether to trigger a rescan')
