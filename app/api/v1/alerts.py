
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
from app.services.alert_service import get_alert_service

router = APIRouter()


@router.post('/', response_model=SuccessResponse[AlertResponse], status_code=status.HTTP_201_CREATED)
async def create_alert(
    alert_data: AlertCreate, 
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> SuccessResponse[AlertResponse]:
    """
    service = get_alert_service()
    alert_dict = alert_data.model_dump()
    result = await service.create_alert(alert_dict)
    
    if result["status"] == "duplicate":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail=result["message"]
        )
    
    return SuccessResponse(
        message=result["message"],  
        data=AlertResponse(**result["alert"])
    )
    """
    now = datetime.utcnow()

    dummy_alert = AlertResponse(
        signature="dummy-signature",
        source_id="test-source",
        severity="LOW",
        component="test-component",
        quality="good",
        normalized_payload={},
        alert_id="dummy-id",
        status="open",
        first_seen=now,
        last_seen=now,
        lifecycle_history=[],
        reopen_count=0,
        last_reopened_at=None,
        version=1,
        created_at=now,
        updated_at=now
    )

    return SuccessResponse(
        message="pong",
        data=dummy_alert
    )


@router.get('/', response_model=PaginatedResponse[AlertResponse])
async def list_alerts(
    pagination: PaginationParams = Depends(get_pagination),
    filters: dict = Depends(get_alert_filters),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> PaginatedResponse[AlertResponse]:
    service = get_alert_service()
    
    # Extraer filtros del dict
    alerts = await service.list_alerts(
        status=filters.get("status"),
        severity=filters.get("severity"),
        source_id=filters.get("source_id"),
        component=filters.get("component"),
        quality=filters.get("quality"),
        limit=pagination.limit,
        skip=pagination.skip
    )
    
    total = await db.alerts.count_documents(filters)
    
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
    alert_id: str, 
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> AlertResponse:
    service = get_alert_service()
    alert = await service.get_alert(alert_id)
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail='Alert not found'
        )
    
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
        data=AlertResponse(**updated_alert), # type: ignore
    )


@router.patch('/{alert_id}/status', response_model=SuccessResponse[AlertResponse])
async def update_alert_status(
    alert_id: str, 
    status_update: AlertStatusUpdate, 
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> SuccessResponse[AlertResponse]:
    service = get_alert_service()
    
    try:
        updated_alert = await service.update_status(
            alert_id=alert_id,
            new_status=status_update.status,
            event_metadata={"reason": status_update.reason}
        )
        
        return SuccessResponse(
            message=f'Alert status updated to {status_update.status}',
            data=AlertResponse(**updated_alert),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=str(e)
        )


@router.delete('/{alert_id}', response_model=SuccessResponse[None])
async def delete_alert(
    alert_id: str, 
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> SuccessResponse[None]:
    # Este endpoint no tiene método en el servicio, usa db directamente
    result = await db.alerts.delete_one({'alert_id': alert_id})
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail='Alert not found'
        )
    
    return SuccessResponse(
        message=f'Alert {alert_id} deleted successfully', 
        data=None
    )