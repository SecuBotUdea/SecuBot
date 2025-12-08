# -*- coding: utf-8 -*-
"""
Reset Database Script - Drop all collections
Run: python -m scripts.reset_db

WARNING: This will delete ALL data from the database!
"""

import asyncio

from app.database.connection import close_db_connection, init_db_connection, get_database
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Collections to drop
COLLECTIONS = [
    'alerts',
    'users',
    'remediations',
    'point_transactions',
    'badges',
    'awards',
]


async def reset_database():
    """Drop all collections from the database"""

    try:
        # Initialize database connection
        await init_db_connection()
        db = get_database()

        logger.warning('='*60)
        logger.warning('WARNING: This will delete ALL data!')
        logger.warning('='*60)

        # Drop each collection
        dropped_count = 0
        for collection_name in COLLECTIONS:
            try:
                await db[collection_name].drop()
                logger.info(f'Dropped collection: {collection_name}')
                dropped_count += 1
            except Exception as e:
                logger.warning(f'Could not drop {collection_name}: {e}')

        logger.info('='*60)
        logger.info(f'Database reset completed!')
        logger.info(f'Dropped {dropped_count}/{len(COLLECTIONS)} collections')
        logger.info('='*60)

    except Exception as e:
        logger.error(f'Error resetting database: {type(e).__name__}: {e}')
        raise

    finally:
        # Close connection
        await close_db_connection()


if __name__ == '__main__':
    # Simple confirmation prompt
    print('\n' + '='*60)
    print('WARNING: This will DELETE ALL DATA from the database!')
    print('='*60)
    response = input('Are you sure you want to continue? (yes/no): ')

    if response.lower() in ['yes', 'y']:
        asyncio.run(reset_database())
    else:
        print('Operation cancelled.')
