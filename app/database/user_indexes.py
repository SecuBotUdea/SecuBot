from app.database.mongodb import get_database
import logging
logger = logging.getLogger(__name__)

def ensure_indexes(collection) -> None:
        """Crear índices estratégicos para optimizar queries"""
        try:
            # Índices únicos
            collection.create_index("username", unique=True)
            collection.create_index("email", unique=True)
            
            # Índices para búsquedas comunes
            collection.create_index("role")
            collection.create_index("team_id")
            collection.create_index("is_active")
            collection.create_index("email_verified")
            collection.create_index("created_at")
            
            # Índices compuestos
            collection.create_index([("role", 1), ("is_active", 1)])
            collection.create_index([("team_id", 1), ("is_active", 1)])
            
        except Exception as e:
            print(f"Advertencia al crear índices de usuarios: {e}")