# -*- coding: utf-8 -*-
"""
Alerts API Router - CRUD operations for security alerts
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.dependencies import get_alert_filters, get_db, get_pagination
from app.models.alert import Alert
from app.schemas.alert_schemas import (
    AlertCreate,
    AlertResponse,
    AlertStatusUpdate,
    AlertUpdate,
)
from app.schemas.common_schemas import PaginatedResponse, PaginationParams, SuccessResponse

router = APIRouter()


@router.post('/', response_model=SuccessResponse[AlertResponse], status_code=status.HTTP_201_CREATED)
async def create_alert(
    alert_data: AlertCreate, db: AsyncIOMotorDatabase = Depends(get_db)
) -> SuccessResponse[AlertResponse]:
    """
    Create a new security alert

    This endpoint is typically called by security tools (Trivy, Dependabot, OWASP ZAP)
    after normalizing their findings to SARIF format
    """
    # Check if alert already exists
    existing = await db.alerts.find_one({'alert_id': alert_data.alert_id})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'Alert with ID {alert_data.alert_id} already exists',
        )

    # Create Alert model instance with timestamps
    alert = Alert(
        **alert_data.model_dump(),
        first_seen=datetime.utcnow(),
        last_seen=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    # Insert into database
    alert_dict = alert.model_dump(by_alias=True, exclude={'id'})
    result = await db.alerts.insert_one(alert_dict)

    # Fetch created alert
    created_alert = await db.alerts.find_one({'_id': result.inserted_id})
    if not created_alert:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Failed to create alert'
        )

    return SuccessResponse(
        message='Alert created successfully',
        data=AlertResponse(**created_alert),
    )


@router.get('/', response_model=PaginatedResponse[AlertResponse])
async def list_alerts(
    pagination: PaginationParams = Depends(get_pagination),
    filters: dict = Depends(get_alert_filters),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> PaginatedResponse[AlertResponse]:
    """
    List all alerts with optional filtering and pagination

    Filters:
    - severity: CRITICAL, HIGH, MEDIUM, LOW, INFO
    - status: open, pending, verified, failed, ignored, reopened
    - source_id: trivy, dependabot, owasp_zap
    - component: name of affected component
    """
    # Count total matching documents
    total = await db.alerts.count_documents(filters)

    # Fetch paginated results
    cursor = db.alerts.find(filters).skip(pagination.skip).limit(pagination.limit).sort('created_at', -1)

    alerts = await cursor.to_list(length=pagination.limit)

    # Convert to response models
    items = [AlertResponse(**alert) for alert in alerts]

    return PaginatedResponse(
        items=items,
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
        has_more=(pagination.skip + len(items)) < total,
    )


@router.get('/{alert_id}', response_model=AlertResponse)
async def get_alert(
    alert_id: str, db: AsyncIOMotorDatabase = Depends(get_db)
) -> AlertResponse:
    """Get a specific alert by ID"""
    alert = await db.alerts.find_one({'alert_id': alert_id})

    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Alert not found')

    return AlertResponse(**alert)


@router.patch('/{alert_id}', response_model=SuccessResponse[AlertResponse])
async def update_alert(
    alert_id: str, alert_update: AlertUpdate, db: AsyncIOMotorDatabase = Depends(get_db)
) -> SuccessResponse[AlertResponse]:
    """
    Update an alert

    Only non-None fields will be updated
    """
    # Check if alert exists
    existing = await db.alerts.find_one({'alert_id': alert_id})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Alert not found')

    # Prepare update data (exclude None values)
    update_data = alert_update.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='No fields to update'
        )

    # Add updated_at timestamp
    update_data['updated_at'] = datetime.utcnow()

    # Update in database
    await db.alerts.update_one({'alert_id': alert_id}, {'$set': update_data})

    # Fetch updated alert
    updated_alert = await db.alerts.find_one({'alert_id': alert_id})

    return SuccessResponse(
        message='Alert updated successfully',
        data=AlertResponse(**updated_alert),
    )


@router.patch('/{alert_id}/status', response_model=SuccessResponse[AlertResponse])
async def update_alert_status(
    alert_id: str, status_update: AlertStatusUpdate, db: AsyncIOMotorDatabase = Depends(get_db)
) -> SuccessResponse[AlertResponse]:
    """
    Update alert status with optional reason

    This endpoint is typically used by the remediation verification system
    """
    # Check if alert exists
    existing = await db.alerts.find_one({'alert_id': alert_id})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Alert not found')

    # Prepare status update
    update_data = {
        'status': status_update.status,
        'updated_at': datetime.utcnow(),
    }

    # Add lifecycle event
    lifecycle_event = {
        'timestamp': datetime.utcnow(),
        'status': status_update.status,
        'reason': status_update.reason,
    }

    # Update in database
    await db.alerts.update_one(
        {'alert_id': alert_id},
        {
            '$set': update_data,
            '$push': {'lifecycle_history': lifecycle_event},
        },
    )

    # Fetch updated alert
    updated_alert = await db.alerts.find_one({'alert_id': alert_id})

    return SuccessResponse(
        message=f'Alert status updated to {status_update.status}',
        data=AlertResponse(**updated_alert),
    )


@router.delete('/{alert_id}', response_model=SuccessResponse[None])
async def delete_alert(
    alert_id: str, db: AsyncIOMotorDatabase = Depends(get_db)
) -> SuccessResponse[None]:
    """
    Delete an alert

    WARNING: This permanently deletes the alert. Use with caution.
    """
    result = await db.alerts.delete_one({'alert_id': alert_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Alert not found')

    return SuccessResponse(message=f'Alert {alert_id} deleted successfully', data=None)
