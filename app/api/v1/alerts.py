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
    Create a new alert
    
    If an alert with the same signature already exists, returns 409 Conflict.
    Otherwise creates a new alert with lifecycle tracking.
    """
    try:
        service = get_alert_service()
        
        # Convert Pydantic model to dict
        alert_dict = alert_data.model_dump(exclude_none=True)
        
        # Ensure timestamps are set
        now = datetime.utcnow()
        if 'first_seen' not in alert_dict or not alert_dict['first_seen']:
            alert_dict['first_seen'] = now
        if 'last_seen' not in alert_dict or not alert_dict['last_seen']:
            alert_dict['last_seen'] = now
        if 'created_at' not in alert_dict:
            alert_dict['created_at'] = now
        if 'updated_at' not in alert_dict:
            alert_dict['updated_at'] = now
        
        # Initialize lifecycle_history if not present
        if 'lifecycle_history' not in alert_dict:
            alert_dict['lifecycle_history'] = [{
                "timestamp": now,
                "old_status": None,
                "new_status": alert_dict.get('status', 'open'),
                "metadata": {"event": "alert_created"}
            }]
        
        # Create alert using service
        result = await service.create_alert(alert_dict)
        
        # Handle duplicate case
        if result["status"] == "duplicate":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail=result["message"]
            )
        
        # Return success response
        return SuccessResponse(
            message=result["message"],  
            data=AlertResponse(**result["alert"])
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError as e:
        # Handle validation errors
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        # Log the error and return 500
        import traceback
        print(f"Error creating alert: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create alert: {str(e)}"
        )


@router.get('/', response_model=PaginatedResponse[AlertResponse])
async def list_alerts(
    pagination: PaginationParams = Depends(get_pagination),
    filters: dict = Depends(get_alert_filters),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> PaginatedResponse[AlertResponse]:
    """
    List alerts with optional filtering and pagination
    
    Filters: severity, status, source_id, component, quality
    """
    try:
        service = get_alert_service()
        
        # Get alerts from service
        alerts = await service.list_alerts(
            status=filters.get("status"),
            severity=filters.get("severity"),
            source_id=filters.get("source_id"),
            component=filters.get("component"),
            quality=filters.get("quality"),
            limit=pagination.limit,
            skip=pagination.skip
        )
        
        # Count total matching documents
        total = await db.alerts.count_documents(filters)
        
        # Convert to response models
        items = [AlertResponse(**alert) for alert in alerts]
        
        return PaginatedResponse(
            items=items,
            total=total,
            skip=pagination.skip,
            limit=pagination.limit,
            has_more=(pagination.skip + len(items)) < total,
        )
    except Exception as e:
        import traceback
        print(f"Error listing alerts: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list alerts: {str(e)}"
        )


@router.get('/{alert_id}', response_model=AlertResponse)
async def get_alert(
    alert_id: str, 
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> AlertResponse:
    """
    Get a single alert by ID
    """
    try:
        service = get_alert_service()
        alert = await service.get_alert(alert_id)
        
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f'Alert {alert_id} not found'
            )
        
        return AlertResponse(**alert)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error getting alert: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alert: {str(e)}"
        )


@router.patch('/{alert_id}', response_model=SuccessResponse[AlertResponse])
async def update_alert(
    alert_id: str, 
    alert_update: AlertUpdate, 
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> SuccessResponse[AlertResponse]:
    """
    Update an alert

    Only non-None fields will be updated
    """
    try:
        # Check if alert exists
        existing = await db.alerts.find_one({'alert_id': alert_id})
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f'Alert {alert_id} not found'
            )

        # Prepare update data (exclude None values)
        update_data = alert_update.model_dump(exclude_none=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail='No fields to update'
            )

        # Add updated_at timestamp
        update_data['updated_at'] = datetime.utcnow()

        # Update in database
        await db.alerts.update_one(
            {'alert_id': alert_id}, 
            {'$set': update_data}
        )

        # Fetch updated alert
        updated_alert = await db.alerts.find_one({'alert_id': alert_id})

        return SuccessResponse(
            message='Alert updated successfully',
            data=AlertResponse(**updated_alert), # type: ignore
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error updating alert: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update alert: {str(e)}"
        )


@router.patch('/{alert_id}/status', response_model=SuccessResponse[AlertResponse])
async def update_alert_status(
    alert_id: str, 
    status_update: AlertStatusUpdate, 
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> SuccessResponse[AlertResponse]:
    """
    Update alert status with lifecycle tracking
    
    Automatically tracks status changes in lifecycle_history
    """
    try:
        service = get_alert_service()
        
        updated_alert = await service.update_status(
            alert_id=alert_id,
            new_status=status_update.status,
            event_metadata={"reason": status_update.reason} if status_update.reason else {}
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
    except Exception as e:
        import traceback
        print(f"Error updating alert status: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update alert status: {str(e)}"
        )


@router.delete('/{alert_id}', response_model=SuccessResponse[None])
async def delete_alert(
    alert_id: str, 
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> SuccessResponse[None]:
    """
    Delete an alert by ID
    """
    try:
        result = await db.alerts.delete_one({'alert_id': alert_id})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f'Alert {alert_id} not found'
            )
        
        return SuccessResponse(
            message=f'Alert {alert_id} deleted successfully', 
            data=None
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error deleting alert: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete alert: {str(e)}"
        )