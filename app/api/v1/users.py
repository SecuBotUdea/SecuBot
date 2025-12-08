# -*- coding: utf-8 -*-
"""
Users API Router - CRUD operations for users and gamification stats
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.dependencies import get_db, get_pagination, get_user_filters
from app.models.user import User
from app.schemas.common_schemas import PaginatedResponse, PaginationParams, SuccessResponse
from app.schemas.user_schemas import (
    UserCreate,
    UserResponse,
    UserStatsResponse,
    UserUpdate,
)

router = APIRouter()


@router.post('/', response_model=SuccessResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate, db: AsyncIOMotorDatabase = Depends(get_db)
) -> SuccessResponse[UserResponse]:
    """
    Create a new user

    This endpoint is typically called when a user joins the team or first interacts
    with the SecuBot system through Slack
    """
    # Check if username or email already exists
    existing = await db.users.find_one(
        {'$or': [{'username': user_data.username}, {'email': user_data.email}]}
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='User with this username or email already exists',
        )

    # Create User model instance
    user = User(**user_data.model_dump(), created_at=datetime.utcnow(), updated_at=datetime.utcnow())

    # Insert into database
    user_dict = user.model_dump(by_alias=True, exclude={'id'})
    result = await db.users.insert_one(user_dict)

    # Fetch created user
    created_user = await db.users.find_one({'_id': result.inserted_id})
    if not created_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Failed to create user'
        )

    return SuccessResponse(
        message='User created successfully',
        data=UserResponse(**created_user),
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
    # Count total matching documents
    total = await db.users.count_documents(filters)

    # Fetch paginated results
    cursor = db.users.find(filters).skip(pagination.skip).limit(pagination.limit).sort('created_at', -1)

    users = await cursor.to_list(length=pagination.limit)

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
async def get_user(username: str, db: AsyncIOMotorDatabase = Depends(get_db)) -> UserResponse:
    """Get a specific user by username"""
    user = await db.users.find_one({'username': username})

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

    return UserResponse(**user)


@router.patch('/{username}', response_model=SuccessResponse[UserResponse])
async def update_user(
    username: str, user_update: UserUpdate, db: AsyncIOMotorDatabase = Depends(get_db)
) -> SuccessResponse[UserResponse]:
    """
    Update a user

    Only non-None fields will be updated
    """
    # Check if user exists
    existing = await db.users.find_one({'username': username})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

    # Prepare update data (exclude None values)
    update_data = user_update.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='No fields to update'
        )

    # Add updated_at timestamp
    update_data['updated_at'] = datetime.utcnow()

    # Update in database
    await db.users.update_one({'username': username}, {'$set': update_data})

    # Fetch updated user
    updated_user = await db.users.find_one({'username': username})

    return SuccessResponse(
        message='User updated successfully',
        data=UserResponse(**updated_user),
    )


@router.delete('/{username}', response_model=SuccessResponse[None])
async def delete_user(
    username: str, db: AsyncIOMotorDatabase = Depends(get_db)
) -> SuccessResponse[None]:
    """
    Delete a user

    WARNING: This permanently deletes the user. Use with caution.
    """
    result = await db.users.delete_one({'username': username})

    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

    return SuccessResponse(message=f'User {username} deleted successfully', data=None)


@router.get('/{username}/stats', response_model=UserStatsResponse)
async def get_user_stats(
    username: str, db: AsyncIOMotorDatabase = Depends(get_db)
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
    # Check if user exists
    user = await db.users.find_one({'username': username})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

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
    failed_count = await db.remediations.count_documents({'user_id': user_id, 'status': 'failed'})

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
