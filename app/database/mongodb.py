# app/database/connection.py

import logging
import os

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from config.settings import settings

# Carga el archivo .env desde la ubicación actual
load_dotenv()

def get_database():
    """Retorna la base de datos de SecuBot"""
    client = MongoClient(
        os.getenv("MONGODB_URI"),
        serverSelectionTimeoutMS=5000
    )
    db_name = os.getenv("DATABASE_NAME", "secubot_dev")
    return client[db_name]
def get_database() -> AsyncIOMotorDatabase:
    """
    Dependency para FastAPI
    Retorna la instancia de la base de datos
    Usage:
        @app.get("/items")
        async def get_items(db: AsyncIOMotorDatabase = Depends(get_database)):
            items = await db.items.find().to_list(100)
            return items
    """
    if db.database is None:
        raise RuntimeError("Database not initialized. Call connect_to_mongo() first.")
    return db.database

"""
MongoDB Connection Manager
Maneja la conexión async a MongoDB usando Motor
"""



logger = logging.getLogger(__name__)


class Database:
    """Singleton para mantener la conexión a MongoDB"""

    client: AsyncIOMotorClient | None = None
    database: AsyncIOMotorDatabase | None = None


# Instancia global
db = Database()


async def connect_to_mongo() -> None:
    """
    Conecta a MongoDB al iniciar la aplicación
    """
    try:
        logger.info(f"Conectando a MongoDB: {settings.database_name}")

        # Crear cliente Motor (async)
        db.client = AsyncIOMotorClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=5000,  # Timeout de 5 segundos
            maxPoolSize=10,  # Máximo 10 conexiones
        )

        # Seleccionar base de datos
        db.database = db.client[settings.database_name]

        # Verificar conexión
        await db.client.admin.command('ping')

        logger.info(f"✅ Conectado a MongoDB: {settings.database_name}")

        # Crear índices al iniciar
        from app.database.indexes import create_indexes
        await create_indexes()

    except ConnectionFailure as e:
        logger.error(f"❌ Error conectando a MongoDB: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}")
        raise


async def close_mongo_connection() -> None:
    """
    Cierra la conexión a MongoDB al apagar la aplicación
    """
    if db.client:
        logger.info("Cerrando conexión a MongoDB...")
        db.client.close()
        logger.info("✅ Conexión cerrada")





async def check_connection() -> bool:
    """
    Verifica si la conexión a MongoDB está activa
    """
    try:
        if db.client:
            await db.client.admin.command('ping')
            return True
        return False
    except Exception:
        return False
