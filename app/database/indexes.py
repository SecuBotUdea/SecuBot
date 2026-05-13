"""
MongoDB Indexes
Define y crea los índices necesarios para optimizar queries
"""

import logging

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import OperationFailure

from app.database.mongodb import get_database

logger = logging.getLogger(__name__)

# MongoDB error code for IndexOptionsConflict (index exists with different name/options)
_INDEX_OPTIONS_CONFLICT = 85
_INDEX_KEY_SPECS_CONFLICT = 86


async def _safe_create_index(collection, keys, log_label: str, **kwargs) -> None:
    """
    Creates an index, tolerating conflicts when an equivalent index already exists
    under a different auto-generated name (e.g. created by an older migration).
    """
    try:
        await collection.create_index(keys, **kwargs)
        logger.info(f"✅ Índice creado: {log_label}")
    except OperationFailure as e:
        if e.code in (_INDEX_OPTIONS_CONFLICT, _INDEX_KEY_SPECS_CONFLICT):
            logger.warning(
                f"⚠️  Índice '{log_label}' ya existe con un nombre diferente "
                f"(probablemente de una migración anterior). Se omite. [{e.details.get('errmsg', e)}]"
            )
        else:
            logger.error(f"❌ Error creando índice '{log_label}': {e}")
    except Exception as e:
        logger.error(f"❌ Error inesperado creando índice '{log_label}': {e}")


async def create_indexes() -> None:
    """
    Crea todos los índices necesarios en las colecciones.
    Se ejecuta automáticamente al iniciar la aplicación.
    Los errores por índice existente se registran como advertencias y no
    interrumpen el arranque de la aplicación.
    """
    try:
        db = get_database()
        logger.info("Creando índices en MongoDB...")

        # ==========================================
        # ALERTS
        # ==========================================
        await _safe_create_index(
            db.alerts,
            [("signature", ASCENDING)],
            "alerts.signature (unique)",
            unique=True,
            name="idx_signature_unique",
        )

        await _safe_create_index(
            db.alerts,
            [("status", ASCENDING), ("severity", DESCENDING)],
            "alerts.status + severity",
            name="idx_status_severity",
        )

        await _safe_create_index(
            db.alerts,
            [("first_seen", DESCENDING)],
            "alerts.first_seen",
            name="idx_first_seen",
        )

        # ==========================================
        # REMEDIATIONS
        # ==========================================
        await _safe_create_index(
            db.remediations,
            [("alert_id", ASCENDING)],
            "remediations.alert_id",
            name="idx_alert_id",
        )

        await _safe_create_index(
            db.remediations,
            [("user_id", ASCENDING), ("created_at", DESCENDING)],
            "remediations.user_id + created_at",
            name="idx_user_created",
        )

        await _safe_create_index(
            db.remediations,
            [("status", ASCENDING)],
            "remediations.status",
            name="idx_status",
        )

        # ==========================================
        # POINT TRANSACTIONS (Ledger Inmutable)
        # ==========================================
        await _safe_create_index(
            db.point_transactions,
            [("user_id", ASCENDING), ("timestamp", DESCENDING)],
            "point_transactions.user_id + timestamp",
            name="idx_user_timestamp",
        )

        await _safe_create_index(
            db.point_transactions,
            [("rule_id", ASCENDING)],
            "point_transactions.rule_id",
            name="idx_rule_id",
        )

        # ==========================================
        # USERS
        # ==========================================
        await _safe_create_index(
            db.users,
            [("user_id", ASCENDING)],
            "users.user_id (unique)",
            unique=True,
            name="idx_user_id_unique",
        )

        await _safe_create_index(
            db.users,
            [("email", ASCENDING)],
            "users.email (unique, sparse)",
            unique=True,
            sparse=True,
            name="idx_email_unique",
        )

        # ==========================================
        # AWARDS (Badges)
        # ==========================================
        await _safe_create_index(
            db.awards,
            [("user_id", ASCENDING), ("badge_id", ASCENDING)],
            "awards.user_id + badge_id (unique)",
            unique=True,
            name="idx_user_badge_unique",
        )

        await _safe_create_index(
            db.awards,
            [("awarded_at", DESCENDING)],
            "awards.awarded_at",
            name="idx_awarded_at",
        )

        # ==========================================
        # RESCAN RESULTS
        # ==========================================
        await _safe_create_index(
            db.rescan_results,
            [("remediation_id", ASCENDING)],
            "rescan_results.remediation_id",
            name="idx_remediation_id",
        )

        await _safe_create_index(
            db.rescan_results,
            [("alert_id", ASCENDING), ("executed_at", DESCENDING)],
            "rescan_results.alert_id + executed_at",
            name="idx_alert_executed",
        )

        # ==========================================
        # DISCORD WEBHOOKS
        # ==========================================
        await _safe_create_index(
            db.discord_webhooks,
            [('guild_id', ASCENDING)],
            'discord_webhooks.guild_id (unique)',
            unique=True,
            name='idx_discord_guild_unique',
        )

        await _safe_create_index(
            db.discord_webhooks,
            [('active', ASCENDING), ('updated_at', DESCENDING)],
            'discord_webhooks.active + updated_at',
            name='idx_discord_active_updated',
        )

        logger.info("🎉 Inicialización de índices completada")

    except Exception as e:
        logger.error(f"❌ Error inesperado durante la creación de índices: {e}")
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
            "rescan_results",
            "discord_webhooks",
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
