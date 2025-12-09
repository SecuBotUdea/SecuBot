# -*- coding: utf-8 -*-
"""
Users API Router - CRUD operations for users and gamification stats
"""

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.dependencies import get_db, get_pagination, get_user_filters
from app.schemas.common_schemas import PaginatedResponse, PaginationParams, SuccessResponse
from app.schemas.user_schemas import (
    UserCreate,
    UserResponse,
    UserStatsResponse,
    UserUpdate,
)
from app.services.user_service import get_user_service

router = APIRouter()


@router.post('/', response_model=SuccessResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate, 
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> SuccessResponse[UserResponse]:
    """
    Create a new user

    This endpoint is typically called when a user joins the team or first interacts
    with the SecuBot system through Slack
    """
    service = get_user_service()
    
    try:
        user = await service.create_user(
            username=user_data.username,
            email=user_data.email,
            display_name=user_data.display_name,
            role=user_data.role if hasattr(user_data, 'role') else "developer",
            team_id=user_data.team_id if hasattr(user_data, 'team_id') else None,
            metadata=user_data.metadata if hasattr(user_data, 'metadata') else None
        )
        
        return SuccessResponse(
            message='User created successfully',
            data=UserResponse(**user),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.get('/', response_model=PaginatedResponse[UserResponse])
async def list_users(
    pagination: PaginationParams = Depends(get_pagination),
    filters: dict = Depends(get_user_filters),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> PaginatedResponse[UserResponse]:
    """
    List all users with optional filtering and pagination

    Filters:
    - role: super_admin, admin, member, viewer, auditor
    - team_id: team identifier
    - is_active: true/false
    """
    service = get_user_service()
    
    # Obtener usuarios filtrados
    users = await service.list_users(
        role=filters.get("role"),
        team_id=filters.get("team_id"),
        is_active=filters.get("is_active"),
        limit=pagination.limit,
        skip=pagination.skip
    )
    
    # Total (usar db directamente para el count)
    total = await db.users.count_documents(filters)
    
    # Convert to response models
    items = [UserResponse(**user) for user in users]
    
    return PaginatedResponse(
        items=items,
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
        has_more=(pagination.skip + len(items)) < total,
    )


@router.get('/{username}', response_model=UserResponse)
async def get_user(
    username: str, 
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> UserResponse:
    """Get a specific user by username"""
    service = get_user_service()
    user = await service.get_user_by_username(username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail='User not found'
        )
    
    return UserResponse(**user)


@router.patch('/{username}', response_model=SuccessResponse[UserResponse])
async def update_user(
    username: str, 
    user_update: UserUpdate, 
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> SuccessResponse[UserResponse]:
    """
    Update a user

    Only non-None fields will be updated
    """
    service = get_user_service()
    
    # Verificar que el usuario existe
    existing = await service.get_user_by_username(username)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail='User not found'
        )
    
    # Preparar datos para actualizar
    update_data = user_update.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail='No fields to update'
        )
    
    try:
        # Actualizar usando el user_id del documento existente
        user_id = str(existing["_id"])
        updated_user = await service.update_user(user_id, **update_data)
        
        return SuccessResponse(
            message='User updated successfully',
            data=UserResponse(**updated_user),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete('/{username}', response_model=SuccessResponse[None])
async def delete_user(
    username: str, 
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> SuccessResponse[None]:
    """
    Delete a user (soft delete)

    This marks the user as inactive instead of permanently deleting them.
    Use hard_delete for permanent deletion (not exposed via API by default).
    """
    service = get_user_service()
    
    # Verificar que el usuario existe
    existing = await service.get_user_by_username(username)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail='User not found'
        )
    
    # Soft delete
    user_id = str(existing["_id"])
    success = await service.delete_user(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Failed to delete user'
        )
    
    return SuccessResponse(
        message=f'User {username} deleted successfully', 
        data=None
    )


@router.get('/{username}/stats', response_model=UserStatsResponse)
async def get_user_stats(
    username: str, 
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> UserStatsResponse:
    """
    Get gamification statistics for a user

    Returns:
    - Total points earned
    - Number of alerts remediated
    - Success rate (verified vs failed)
    - Badges earned
    - Current level
    """
    service = get_user_service()
    
    # Verificar que el usuario existe
    user = await service.get_user_by_username(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail='User not found'
        )
    
    user_id = user.get('user_id') or username
    
    # Calculate total points
    total_points_pipeline = [
        {'$match': {'user_id': user_id}},
        {'$group': {'_id': None, 'total': {'$sum': '$points'}}},
    ]
    points_result = await db.point_transactions.aggregate(total_points_pipeline).to_list(1)
    total_points = points_result[0]['total'] if points_result else 0
    
    # Count remediations by status
    total_remediated = await db.remediations.count_documents({'user_id': user_id})
    verified_count = await db.remediations.count_documents(
        {'user_id': user_id, 'status': 'verified'}
    )
    failed_count = await db.remediations.count_documents(
        {'user_id': user_id, 'status': 'failed'}
    )
    
    # Calculate success rate
    success_rate = (verified_count / total_remediated * 100) if total_remediated > 0 else 0.0
    
    # Count badges
    badges_earned = await db.awards.count_documents({'user_id': user_id})
    
    # Calculate level (simple formula: 1 level per 100 points)
    level = (total_points // 100) + 1 if total_points >= 0 else 1
    
    return UserStatsResponse(
        username=username,
        total_points=total_points,
        alerts_remediated=total_remediated,
        success_rate=round(success_rate, 2),
        badges_earned=badges_earned,
        level=level,
    )


@router.get('/{username}/verify-email', response_model=SuccessResponse[UserResponse])
async def verify_user_email(
    username: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> SuccessResponse[UserResponse]:
    """
    Verify a user's email address
    """
    service = get_user_service()
    
    # Verificar que el usuario existe
    existing = await service.get_user_by_username(username)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found'
        )
    
    user_id = str(existing["_id"])
    updated_user = await service.verify_email(user_id)
    
    return SuccessResponse(
        message='Email verified successfully',
        data=UserResponse(**updated_user)
    )


@router.patch('/{username}/role', response_model=SuccessResponse[UserResponse])
async def change_user_role(
    username: str,
    new_role: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> SuccessResponse[UserResponse]:
    """
    Change a user's role
    
    Valid roles: developer, team_lead, admin, super_admin
    """
    service = get_user_service()
    
    # Verificar que el usuario existe
    existing = await service.get_user_by_username(username)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found'
        )
    
    try:
        user_id = str(existing["_id"])
        updated_user = await service.change_role(user_id, new_role)
        
        return SuccessResponse(
            message=f'Role changed to {new_role} successfully',
            data=UserResponse(**updated_user)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )