"""
MongoDB Indexes
Define y crea los índices necesarios para optimizar queries
"""

import logging

from pymongo import ASCENDING, DESCENDING

from app.database.mongodb import get_database

logger = logging.getLogger(__name__)


async def create_indexes() -> None:
    """
    Crea todos los índices necesarios en las colecciones
    Se ejecuta automáticamente al iniciar la aplicación
    """
    try:
        db = get_database()

        logger.info("Creando índices en MongoDB...")

        # ==========================================
        # ALERTS
        # ==========================================
        await db.alerts.create_index(
            [("signature", ASCENDING)],
            unique=True,
            name="idx_signature_unique"
        )
        logger.info("✅ Índice creado: alerts.signature (unique)")

        await db.alerts.create_index(
            [("status", ASCENDING), ("severity", DESCENDING)],
            name="idx_status_severity"
        )
        logger.info("✅ Índice creado: alerts.status + severity")

        await db.alerts.create_index(
            [("first_seen", DESCENDING)],
            name="idx_first_seen"
        )
        logger.info("✅ Índice creado: alerts.first_seen")

        # ==========================================
        # REMEDIATIONS
        # ==========================================
        await db.remediations.create_index(
            [("alert_id", ASCENDING)],
            name="idx_alert_id"
        )
        logger.info("✅ Índice creado: remediations.alert_id")

        await db.remediations.create_index(
            [("user_id", ASCENDING), ("created_at", DESCENDING)],
            name="idx_user_created"
        )
        logger.info("✅ Índice creado: remediations.user_id + created_at")

        await db.remediations.create_index(
            [("status", ASCENDING)],
            name="idx_status"
        )
        logger.info("✅ Índice creado: remediations.status")

        # ==========================================
        # POINT TRANSACTIONS (Ledger Inmutable)
        # ==========================================
        await db.point_transactions.create_index(
            [("user_id", ASCENDING), ("timestamp", DESCENDING)],
            name="idx_user_timestamp"
        )
        logger.info("✅ Índice creado: point_transactions.user_id + timestamp")

        await db.point_transactions.create_index(
            [("rule_id", ASCENDING)],
            name="idx_rule_id"
        )
        logger.info("✅ Índice creado: point_transactions.rule_id")

        # ==========================================
        # USERS
        # ==========================================
        await db.users.create_index(
            [("user_id", ASCENDING)],
            unique=True,
            name="idx_user_id_unique"
        )
        logger.info("✅ Índice creado: users.user_id (unique)")

        await db.users.create_index(
            [("email", ASCENDING)],
            unique=True,
            sparse=True,  # Permite nulls
            name="idx_email_unique"
        )
        logger.info("✅ Índice creado: users.email (unique, sparse)")

        # ==========================================
        # AWARDS (Badges)
        # ==========================================
        await db.awards.create_index(
            [("user_id", ASCENDING), ("badge_id", ASCENDING)],
            unique=True,
            name="idx_user_badge_unique"
        )
        logger.info("✅ Índice creado: awards.user_id + badge_id (unique)")

        await db.awards.create_index(
            [("awarded_at", DESCENDING)],
            name="idx_awarded_at"
        )
        logger.info("✅ Índice creado: awards.awarded_at")

        # ==========================================
        # RESCAN RESULTS
        # ==========================================
        await db.rescan_results.create_index(
            [("remediation_id", ASCENDING)],
            name="idx_remediation_id"
        )
        logger.info("✅ Índice creado: rescan_results.remediation_id")

        await db.rescan_results.create_index(
            [("alert_id", ASCENDING), ("executed_at", DESCENDING)],
            name="idx_alert_executed"
        )
        logger.info("✅ Índice creado: rescan_results.alert_id + executed_at")

        logger.info("🎉 Todos los índices creados exitosamente")

    except Exception as e:
        logger.error(f"❌ Error creando índices: {e}")
        # No lanzamos excepción para no romper el inicio de la app
        # Los índices no son críticos para que la app funcione


async def drop_all_indexes() -> None:
    """
    Elimina todos los índices (útil para desarrollo/testing)
    ⚠️ CUIDADO: Solo usar en desarrollo
    """
    try:
        db = get_database()

        collections = [
            "alerts",
            "remediations",
            "point_transactions",
            "users",
            "awards",
            "rescan_results"
        ]

        for collection_name in collections:
            await db[collection_name].drop_indexes()
            logger.info(f"🗑️  Índices eliminados: {collection_name}")

    except Exception as e:
        logger.error(f"❌ Error eliminando índices: {e}")


async def list_indexes() -> dict:
    """
    Lista todos los índices de todas las colecciones
    Útil para debugging
    """
    db = get_database()

    result = {}
    collections = await db.list_collection_names()

    for collection_name in collections:
        indexes = await db[collection_name].list_indexes().to_list(None)
        result[collection_name] = [idx['name'] for idx in indexes]

    return result
