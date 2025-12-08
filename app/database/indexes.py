# -*- coding: utf-8 -*-
"""
MongoDB Indexes - Create critical indexes for performance
"""

from app.database.connection import get_database
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def create_indexes() -> None:
    """
    Create MongoDB indexes for all collections
    Called during application startup after DB connection
    """
    db = get_database()

    try:
        logger.info('Creating MongoDB indexes...')

        # ============================================
        # ALERTS Collection Indexes
        # ============================================
        await db.alerts.create_index('alert_id', unique=True)
        await db.alerts.create_index('signature')  # Para deduplicacion
        await db.alerts.create_index([('severity', 1), ('status', 1)])  # Queries frecuentes
        await db.alerts.create_index('source_id')
        await db.alerts.create_index('created_at')

        logger.info('Created indexes for alerts collection')

        # ============================================
        # USERS Collection Indexes
        # ============================================
        await db.users.create_index('username', unique=True)
        await db.users.create_index('email', unique=True)
        await db.users.create_index('team_id')
        await db.users.create_index([('role', 1), ('is_active', 1)])

        logger.info('Created indexes for users collection')

        # ============================================
        # REMEDIATIONS Collection Indexes
        # ============================================
        await db.remediations.create_index('remediation_id', unique=True)
        await db.remediations.create_index('alert_id')
        await db.remediations.create_index('user_id')
        await db.remediations.create_index([('status', 1), ('created_at', -1)])

        logger.info('Created indexes for remediations collection')

        # ============================================
        # POINT_TRANSACTIONS Collection Indexes
        # ============================================
        await db.point_transactions.create_index('user_id')
        await db.point_transactions.create_index('created_at')
        await db.point_transactions.create_index([('user_id', 1), ('created_at', -1)])

        logger.info('Created indexes for point_transactions collection')

        # ============================================
        # BADGES Collection Indexes
        # ============================================
        await db.badges.create_index('badge_id', unique=True)
        await db.badges.create_index('tier')

        logger.info('Created indexes for badges collection')

        # ============================================
        # AWARDS Collection Indexes
        # ============================================
        await db.awards.create_index([('user_id', 1), ('badge_id', 1)], unique=True)
        await db.awards.create_index('user_id')
        await db.awards.create_index('awarded_at')

        logger.info('Created indexes for awards collection')

        logger.info('All indexes created successfully')

    except Exception as e:
        logger.error(f'Error creating indexes: {type(e).__name__}: {e}')
        raise
