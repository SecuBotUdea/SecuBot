# -*- coding: utf-8 -*-
"""
Remediations API Router - CRUD operations for alert remediations
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.dependencies import get_db, get_pagination, get_remediation_filters
from app.models.remediation import Remediation
from app.schemas.common_schemas import PaginatedResponse, PaginationParams, SuccessResponse
from app.schemas.remediation_schemas import (
    RemediationCreate,
    RemediationResponse,
    RemediationStatusUpdate,
    RemediationUpdate,
)

router = APIRouter()


@router.post('/', response_model=SuccessResponse[RemediationResponse], status_code=status.HTTP_201_CREATED)
async def create_remediation(
    remediation_data: RemediationCreate, db: AsyncIOMotorDatabase = Depends(get_db)
) -> SuccessResponse[RemediationResponse]:
    """
    Create a new remediation

    This endpoint is typically called when a user marks an alert as fixed through Slack
    or when a code fix is pushed that references an alert
    """
    # Check if remediation already exists
    existing = await db.remediations.find_one({'remediation_id': remediation_data.remediation_id})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'Remediation with ID {remediation_data.remediation_id} already exists',
        )

    # Verify alert exists
    alert = await db.alerts.find_one({'alert_id': remediation_data.alert_id})
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Alert {remediation_data.alert_id} not found',
        )

    # Create Remediation model instance
    remediation = Remediation(
        **remediation_data.model_dump(),
        action_ts=datetime.utcnow(),
        status='pending',
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    # Insert into database
    remediation_dict = remediation.model_dump(by_alias=True, exclude={'id'})
    result = await db.remediations.insert_one(remediation_dict)

    # Fetch created remediation
    created_remediation = await db.remediations.find_one({'_id': result.inserted_id})
    if not created_remediation:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Failed to create remediation',
        )

    return SuccessResponse(
        message='Remediation created successfully',
        data=RemediationResponse(**created_remediation),
    )


@router.get('/', response_model=PaginatedResponse[RemediationResponse])
async def list_remediations(
    pagination: PaginationParams = Depends(get_pagination),
    filters: dict = Depends(get_remediation_filters),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> PaginatedResponse[RemediationResponse]:
    """
    List all remediations with optional filtering and pagination

    Filters:
    - alert_id: filter by alert
    - user_id: filter by user
    - team_id: filter by team
    - status: pending, verified, failed
    - type: user_mark, auto_fixed, manual_patch
    """
    # Count total matching documents
    total = await db.remediations.count_documents(filters)

    # Fetch paginated results
    cursor = (
        db.remediations.find(filters)
        .skip(pagination.skip)
        .limit(pagination.limit)
        .sort('created_at', -1)
    )

    remediations = await cursor.to_list(length=pagination.limit)

    # Convert to response models
    items = [RemediationResponse(**remediation) for remediation in remediations]

    return PaginatedResponse(
        items=items,
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
        has_more=(pagination.skip + len(items)) < total,
    )


@router.get('/{remediation_id}', response_model=RemediationResponse)
async def get_remediation(
    remediation_id: str, db: AsyncIOMotorDatabase = Depends(get_db)
) -> RemediationResponse:
    """Get a specific remediation by ID"""
    remediation = await db.remediations.find_one({'remediation_id': remediation_id})

    if not remediation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Remediation not found')

    return RemediationResponse(**remediation)


@router.patch('/{remediation_id}', response_model=SuccessResponse[RemediationResponse])
async def update_remediation(
    remediation_id: str,
    remediation_update: RemediationUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> SuccessResponse[RemediationResponse]:
    """
    Update a remediation

    Only non-None fields will be updated
    """
    # Check if remediation exists
    existing = await db.remediations.find_one({'remediation_id': remediation_id})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Remediation not found')

    # Prepare update data (exclude None values)
    update_data = remediation_update.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='No fields to update'
        )

    # Add updated_at timestamp
    update_data['updated_at'] = datetime.utcnow()

    # Update in database
    await db.remediations.update_one({'remediation_id': remediation_id}, {'$set': update_data})

    # Fetch updated remediation
    updated_remediation = await db.remediations.find_one({'remediation_id': remediation_id})

    return SuccessResponse(
        message='Remediation updated successfully',
        data=RemediationResponse(**updated_remediation),
    )


@router.patch('/{remediation_id}/status', response_model=SuccessResponse[RemediationResponse])
async def update_remediation_status(
    remediation_id: str,
    status_update: RemediationStatusUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> SuccessResponse[RemediationResponse]:
    """
    Update remediation status

    This endpoint is typically called by the rescan verification system after
    running security tools to verify if the vulnerability was actually fixed

    Status transitions:
    - pending -> verified (rescan confirms fix)
    - pending -> failed (rescan still detects vulnerability)
    """
    # Check if remediation exists
    existing = await db.remediations.find_one({'remediation_id': remediation_id})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Remediation not found')

    # Prepare status update
    update_data = {
        'status': status_update.status,
        'updated_at': datetime.utcnow(),
    }

    # If verified or failed, set timestamp
    if status_update.status in ['verified', 'failed']:
        update_data['verified_at'] = datetime.utcnow()

    # If failed, add failure reason
    if status_update.status == 'failed' and status_update.reason:
        update_data['failure_reason'] = status_update.reason

    # Add metadata if provided
    if status_update.metadata:
        update_data['metadata'] = status_update.metadata

    # Update in database
    await db.remediations.update_one({'remediation_id': remediation_id}, {'$set': update_data})

    # Fetch updated remediation
    updated_remediation = await db.remediations.find_one({'remediation_id': remediation_id})

    return SuccessResponse(
        message=f'Remediation status updated to {status_update.status}',
        data=RemediationResponse(**updated_remediation),
    )


@router.delete('/{remediation_id}', response_model=SuccessResponse[None])
async def delete_remediation(
    remediation_id: str, db: AsyncIOMotorDatabase = Depends(get_db)
) -> SuccessResponse[None]:
    """
    Delete a remediation

    WARNING: This permanently deletes the remediation. Use with caution.
    """
    result = await db.remediations.delete_one({'remediation_id': remediation_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Remediation not found')

    return SuccessResponse(message=f'Remediation {remediation_id} deleted successfully', data=None)
