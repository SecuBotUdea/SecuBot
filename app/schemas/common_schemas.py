# -*- coding: utf-8 -*-
"""
Common Schemas - Shared response models across all endpoints
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar('DataT')


class SuccessResponse(BaseModel, Generic[DataT]):
    """Generic success response wrapper"""

    success: bool = Field(default=True, description='Indicates operation success')
    message: str = Field(..., description='Human-readable message')
    data: DataT | None = Field(default=None, description='Response data')


class ErrorResponse(BaseModel):
    """Error response model"""

    success: bool = Field(default=False, description='Indicates operation failure')
    error: str = Field(..., description='Error type or code')
    message: str = Field(..., description='Human-readable error message')
    details: dict[str, Any] | None = Field(default=None, description='Additional error details')


class PaginationParams(BaseModel):
    """Common pagination parameters"""

    skip: int = Field(default=0, ge=0, description='Number of records to skip')
    limit: int = Field(default=20, ge=1, le=100, description='Maximum records to return')


class PaginatedResponse(BaseModel, Generic[DataT]):
    """Generic paginated response"""

    items: list[DataT] = Field(..., description='List of items')
    total: int = Field(..., description='Total number of items')
    skip: int = Field(..., description='Number of items skipped')
    limit: int = Field(..., description='Number of items per page')
    has_more: bool = Field(..., description='Whether there are more items')


class StatusResponse(BaseModel):
    """Simple status response"""

    status: str = Field(..., description='Status message')
    timestamp: str = Field(..., description='ISO timestamp')
