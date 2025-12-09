from app.database.mongodb import get_database
import logging
logger = logging.getLogger(__name__)

def ensure_indexes_alert(collection) -> None:
    try:

        logger.info("Creando índices de alerts...")
        # Índice único para PK
        collection.create_index("alert_id", unique=True)
        
        # Índices para búsquedas comunes del RuleEngine
        collection.create_index("signature")
        collection.create_index("source_id")
        collection.create_index("status")
        collection.create_index("severity")
        collection.create_index("quality")
        collection.create_index("component")
        collection.create_index("first_seen")
        collection.create_index("last_seen")
        collection.create_index("reopen_count")
            
        # Índices compuestos para queries frecuentes
        collection.create_index([("status", 1), ("severity", 1)])
        collection.create_index([("source_id", 1), ("status", 1)])
        collection.create_index([("quality", 1), ("first_seen", -1)])
        collection.create_index([("signature", 1), ("status", 1)])
            
    except Exception as e:
        print(f"Advertencia al crear índices: {e}")