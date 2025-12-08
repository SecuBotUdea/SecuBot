# -*- coding: utf-8 -*-
"""
Seed Database Script - Populate MongoDB with sample data
Run: python -m scripts.seed_db
"""

import asyncio
from datetime import datetime, timedelta

from app.database.connection import close_db_connection, init_db_connection, get_database
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def seed_database():
    """Populate database with sample data for testing"""

    try:
        # Initialize database connection
        await init_db_connection()
        db = get_database()

        logger.info('Starting database seeding...')

        # ============================================
        # USERS
        # ============================================
        logger.info('Creating users...')

        users = [
            {
                'user_id': 'U001',
                'username': 'alice_dev',
                'email': 'alice@example.com',
                'slack_id': 'U12345678',
                'team_id': 'team-alpha',
                'role': 'developer',
                'is_active': True,
                'total_points': 250,
                'level': 2,
                'created_at': datetime.utcnow() - timedelta(days=30),
                'updated_at': datetime.utcnow(),
            },
            {
                'user_id': 'U002',
                'username': 'bob_security',
                'email': 'bob@example.com',
                'slack_id': 'U87654321',
                'team_id': 'team-alpha',
                'role': 'security',
                'is_active': True,
                'total_points': 500,
                'level': 3,
                'created_at': datetime.utcnow() - timedelta(days=60),
                'updated_at': datetime.utcnow(),
            },
        ]

        result = await db.users.insert_many(users)
        logger.info(f'Created {len(result.inserted_ids)} users')

        # ============================================
        # ALERTS
        # ============================================
        logger.info('Creating alerts...')

        alerts = [
            {
                'alert_id': 'ALT-001',
                'signature': 'CVE-2024-1234-nodejs-express',
                'source_id': 'dependabot',
                'severity': 'CRITICAL',
                'component': 'express',
                'status': 'verified',
                'first_seen': datetime.utcnow() - timedelta(days=5),
                'last_seen': datetime.utcnow() - timedelta(days=5),
                'quality': 'high',
                'normalized_payload': {
                    'title': 'SQL Injection in Express middleware',
                    'description': 'Unvalidated user input in query parameters',
                    'cvss_score': 9.8,
                    'cwe': 'CWE-89',
                    'affected_version': '4.17.1',
                    'fixed_version': '4.18.0',
                },
                'created_at': datetime.utcnow() - timedelta(days=5),
                'updated_at': datetime.utcnow() - timedelta(days=2),
            },
            {
                'alert_id': 'ALT-002',
                'signature': 'CVE-2024-5678-lodash',
                'source_id': 'trivy',
                'severity': 'HIGH',
                'component': 'lodash',
                'status': 'failed',
                'first_seen': datetime.utcnow() - timedelta(days=3),
                'last_seen': datetime.utcnow() - timedelta(hours=6),
                'quality': 'high',
                'normalized_payload': {
                    'title': 'Prototype Pollution in lodash',
                    'description': 'Prototype pollution vulnerability in merge function',
                    'cvss_score': 7.5,
                    'cwe': 'CWE-1321',
                    'affected_version': '4.17.20',
                    'fixed_version': '4.17.21',
                },
                'reopen_count': 1,
                'last_reopened_at': datetime.utcnow() - timedelta(hours=6),
                'created_at': datetime.utcnow() - timedelta(days=3),
                'updated_at': datetime.utcnow() - timedelta(hours=6),
            },
            {
                'alert_id': 'ALT-003',
                'signature': 'XSS-login-page',
                'source_id': 'owasp_zap',
                'severity': 'MEDIUM',
                'component': 'auth-frontend',
                'status': 'open',
                'first_seen': datetime.utcnow() - timedelta(days=1),
                'last_seen': datetime.utcnow() - timedelta(days=1),
                'quality': 'medium',
                'normalized_payload': {
                    'title': 'Reflected XSS in login page',
                    'description': 'User input reflected without sanitization',
                    'cvss_score': 6.1,
                    'cwe': 'CWE-79',
                    'url': 'https://app.example.com/login',
                },
                'created_at': datetime.utcnow() - timedelta(days=1),
                'updated_at': datetime.utcnow() - timedelta(days=1),
            },
            {
                'alert_id': 'ALT-004',
                'signature': 'missing-rate-limit-api',
                'source_id': 'owasp_zap',
                'severity': 'LOW',
                'component': 'api-gateway',
                'status': 'pending',
                'first_seen': datetime.utcnow() - timedelta(hours=12),
                'last_seen': datetime.utcnow() - timedelta(hours=12),
                'quality': 'low',
                'normalized_payload': {
                    'title': 'Missing rate limiting on API endpoints',
                    'description': 'API endpoints do not implement rate limiting',
                    'cvss_score': 3.7,
                },
                'created_at': datetime.utcnow() - timedelta(hours=12),
                'updated_at': datetime.utcnow() - timedelta(hours=12),
            },
            {
                'alert_id': 'ALT-005',
                'signature': 'outdated-python-version',
                'source_id': 'trivy',
                'severity': 'INFO',
                'component': 'base-image',
                'status': 'ignored',
                'first_seen': datetime.utcnow() - timedelta(days=7),
                'last_seen': datetime.utcnow() - timedelta(days=7),
                'quality': 'medium',
                'normalized_payload': {
                    'title': 'Python version 3.9 is outdated',
                    'description': 'Consider upgrading to Python 3.11+',
                },
                'created_at': datetime.utcnow() - timedelta(days=7),
                'updated_at': datetime.utcnow() - timedelta(days=7),
            },
        ]

        result = await db.alerts.insert_many(alerts)
        logger.info(f'Created {len(result.inserted_ids)} alerts')

        # ============================================
        # REMEDIATIONS
        # ============================================
        logger.info('Creating remediations...')

        remediations = [
            {
                'remediation_id': 'REM-001',
                'alert_id': 'ALT-001',
                'user_id': 'U001',
                'team_id': 'team-alpha',
                'type': 'user_mark',
                'action_ts': datetime.utcnow() - timedelta(days=3),
                'status': 'verified',
                'details': {
                    'commit_sha': 'abc123def456',
                    'pr_url': 'https://github.com/org/repo/pull/42',
                },
                'verified_at': datetime.utcnow() - timedelta(days=2),
                'created_at': datetime.utcnow() - timedelta(days=3),
                'updated_at': datetime.utcnow() - timedelta(days=2),
            },
            {
                'remediation_id': 'REM-002',
                'alert_id': 'ALT-002',
                'user_id': 'U002',
                'team_id': 'team-alpha',
                'type': 'user_mark',
                'action_ts': datetime.utcnow() - timedelta(days=1),
                'status': 'failed',
                'details': {
                    'commit_sha': 'xyz789abc012',
                    'pr_url': 'https://github.com/org/repo/pull/43',
                },
                'verified_at': datetime.utcnow() - timedelta(hours=6),
                'failure_reason': 'Vulnerability still detected in rescan',
                'created_at': datetime.utcnow() - timedelta(days=1),
                'updated_at': datetime.utcnow() - timedelta(hours=6),
            },
        ]

        result = await db.remediations.insert_many(remediations)
        logger.info(f'Created {len(result.inserted_ids)} remediations')

        # ============================================
        # POINT TRANSACTIONS
        # ============================================
        logger.info('Creating point transactions...')

        transactions = [
            {
                'user_id': 'U001',
                'points': 100,
                'reason': 'Verified remediation for CRITICAL alert',
                'alert_id': 'ALT-001',
                'remediation_id': 'REM-001',
                'multiplier': 1.0,
                'created_at': datetime.utcnow() - timedelta(days=2),
            },
            {
                'user_id': 'U001',
                'points': 50,
                'reason': 'Speed bonus for quick remediation (<24h)',
                'alert_id': 'ALT-001',
                'remediation_id': 'REM-001',
                'multiplier': 1.5,
                'created_at': datetime.utcnow() - timedelta(days=2),
            },
            {
                'user_id': 'U002',
                'points': -25,
                'reason': 'Penalty for failed remediation verification',
                'alert_id': 'ALT-002',
                'remediation_id': 'REM-002',
                'multiplier': 1.0,
                'created_at': datetime.utcnow() - timedelta(hours=6),
            },
        ]

        result = await db.point_transactions.insert_many(transactions)
        logger.info(f'Created {len(result.inserted_ids)} point transactions')

        # ============================================
        # SUMMARY
        # ============================================
        logger.info('\n' + '='*60)
        logger.info('Database seeding completed successfully!')
        logger.info('='*60)
        logger.info(f'Users created: 2')
        logger.info(f'Alerts created: 5')
        logger.info(f'  - CRITICAL: 1 (verified)')
        logger.info(f'  - HIGH: 1 (failed)')
        logger.info(f'  - MEDIUM: 1 (open)')
        logger.info(f'  - LOW: 1 (pending)')
        logger.info(f'  - INFO: 1 (ignored)')
        logger.info(f'Remediations created: 2 (1 verified, 1 failed)')
        logger.info(f'Point transactions: 3 (+100, +50, -25)')
        logger.info('='*60)

    except Exception as e:
        logger.error(f'Error seeding database: {type(e).__name__}: {e}')
        raise

    finally:
        # Close connection
        await close_db_connection()


if __name__ == '__main__':
    asyncio.run(seed_database())
