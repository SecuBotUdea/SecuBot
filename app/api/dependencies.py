
"""
API Dependencies - Reusable dependency functions for FastAPI endpoints
"""

from fastapi import Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.mongodb import get_database
from app.schemas.common_schemas import PaginationParams


async def get_db() -> AsyncIOMotorDatabase:
    """
    Dependency to get database instance

    Usage in endpoint:
        @app.get("/items")
        async def list_items(db: AsyncIOMotorDatabase = Depends(get_db)):
            items = await db.items.find().to_list(100)
            return items
    """
    return get_database()


async def get_pagination(
    skip: int = Query(default=0, ge=0, description='Number of records to skip'),
    limit: int = Query(default=20, ge=1, le=100, description='Maximum records to return'),
) -> PaginationParams:
    """
    Dependency for pagination parameters

    Usage in endpoint:
        @app.get("/items")
        async def list_items(pagination: PaginationParams = Depends(get_pagination)):
            skip = pagination.skip
            limit = pagination.limit
    """
    return PaginationParams(skip=skip, limit=limit)


async def get_alert_filters(
    severity: str | None = Query(None, description='Filter by severity'),
    status: str | None = Query(None, description='Filter by status'),
    source_id: str | None = Query(None, description='Filter by source'),
    component: str | None = Query(None, description='Filter by component'),
) -> dict:
    """
    Dependency for alert filtering parameters

    Returns a dictionary with only non-None values for MongoDB queries
    """
    filters = {}
    if severity:
        filters['severity'] = severity
    if status:
        filters['status'] = status
    if source_id:
        filters['source_id'] = source_id
    if component:
        filters['component'] = component
    return filters


async def get_user_filters(
    role: str | None = Query(None, description='Filter by role'),
    team_id: str | None = Query(None, description='Filter by team'),
    is_active: bool | None = Query(None, description='Filter by active status'),
) -> dict:
    """
    Dependency for user filtering parameters

    Returns a dictionary with only non-None values for MongoDB queries
    """
    filters = {}
    if role:
        filters['role'] = role
    if team_id:
        filters['team_id'] = team_id
    if is_active is not None:
        filters['is_active'] = is_active
    return filters


async def get_remediation_filters(
    alert_id: str | None = Query(None, description='Filter by alert'),
    user_id: str | None = Query(None, description='Filter by user'),
    team_id: str | None = Query(None, description='Filter by team'),
    status: str | None = Query(None, description='Filter by status'),
    type: str | None = Query(None, description='Filter by type'),
) -> dict:
    """
    Dependency for remediation filtering parameters

    Returns a dictionary with only non-None values for MongoDB queries
    """
    filters = {}
    if alert_id:
        filters['alert_id'] = alert_id
    if user_id:
        filters['user_id'] = user_id
    if team_id:
        filters['team_id'] = team_id
    if status:
        filters['status'] = status
    if type:
        filters['type'] = type
    return filters
