# -*- coding: utf-8 -*-
"""
MongoDB Connection using Motor (Async Driver)
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Global client instance
_client: AsyncIOMotorClient | None = None
_database: AsyncIOMotorDatabase | None = None


async def init_db_connection() -> None:
    """
    Initialize MongoDB connection
    Called during application startup
    """
    global _client, _database

    try:
        logger.info(f'Connecting to MongoDB: {settings.database_name}')

        # Create Motor client
        _client = AsyncIOMotorClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
        )

        # Test connection
        await _client.admin.command('ping')

        # Get database
        _database = _client[settings.database_name]

        logger.info(f'Successfully connected to MongoDB: {settings.database_name}')

    except Exception as e:
        logger.error(f'Failed to connect to MongoDB: {type(e).__name__}: {e}')
        raise


async def close_db_connection() -> None:
    """
    Close MongoDB connection
    Called during application shutdown
    """
    global _client

    if _client:
        logger.info('Closing MongoDB connection')
        _client.close()
        logger.info('MongoDB connection closed')


def get_database() -> AsyncIOMotorDatabase:
    """
    Get MongoDB database instance

    Returns:
        AsyncIOMotorDatabase: Database instance

    Raises:
        RuntimeError: If database connection is not initialized
    """
    if _database is None:
        raise RuntimeError(
            'Database connection not initialized. Call init_db_connection() first.'
        )
    return _database


def get_collection(collection_name: str):
    """
    Get MongoDB collection

    Args:
        collection_name: Name of the collection

    Returns:
        AsyncIOMotorCollection: Collection instance
    """
    db = get_database()
    return db[collection_name]
