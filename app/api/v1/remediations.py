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


@router.post("/", status_code=201)
async def create_remediation(
    request: CreateRemediationRequest,
    remediation_service = Depends(get_remediation_service)
) -> Dict[str, Any]:
    """
    El usuario marca que ya remedió una alerta.
    
    Esto automáticamente:
    - Crea el registro de remediación
    - Dispara el rescan para verificar
    - Ejecuta el gamificador (puntos/penalizaciones)
    """
    try:
        result = await remediation_service.create_remediation(
            alert_id=request.alert_id,
            user_id=request.user_id,
            notes=request.notes,
            team_id=request.team_id
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        logger.error(f"Error al crear remediación: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
