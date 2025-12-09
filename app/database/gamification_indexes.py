from app.database.mongodb import get_database
import logging
logger = logging.getLogger(__name__)

def _ensure_indexes(point_txns, awards):
        """Crear índices para queries optimizadas"""
        try:
            point_txns.create_index("user_id")
            point_txns.create_index("timestamp")
            point_txns.create_index([("user_id", 1), ("timestamp", -1)])
            awards.create_index("user_id")
            awards.create_index([("user_id", 1), ("awarded_at", -1)])
        except Exception as e:
            logger.warning(f"Error creando índices: {e}")