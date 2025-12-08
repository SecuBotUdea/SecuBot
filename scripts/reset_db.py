"""
Reset Database Script
⚠️ CUIDADO: Elimina TODAS las colecciones de la base de datos
Solo usar en desarrollo
"""

import asyncio
import os
import sys

# Agregar el directorio raíz al path para importar módulos de la app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.mongodb import close_db_connection, get_database, init_db_connection
from app.utils.logger import get_logger
from config.settings import settings

logger = get_logger(__name__)


async def reset_database():
    """
    Elimina todas las colecciones de la base de datos de forma dinámica.
    """
    # Verificar que no estamos en producción
    if settings.environment.lower() == "production":
        logger.error("❌ ERROR: No puedes resetear la base de datos en producción!")
        logger.error("   Cambia ENVIRONMENT en .env a 'development' o 'testing'")
        return

    logger.warning("⚠️  WARNING: Esto eliminará TODOS los datos de la base de datos")
    logger.warning(f"   Database: {settings.database_name}")
    logger.warning(f"   Environment: {settings.environment}")

    # Pedir confirmación robusta
    response = input("\n¿Estás seguro? Escribe 'DELETE' para confirmar: ")

    if response != "DELETE":
        logger.error("❌ Operación cancelada")
        return

    logger.info("\n🗑️  Reseteando database...")

    client = None  # Inicializar client para que exista en el bloque finally
    try:
        # Inicializar conexión usando la lógica de la aplicación
        await init_db_connection()
        db = get_database()

        # Obtener todas las colecciones de forma dinámica
        collections = await db.list_collection_names()

        if not collections:
            logger.info("No hay colecciones para eliminar.")
            return

        logger.warning(f"\nColecciones a eliminar: {', '.join(collections)}")

        # Eliminar cada colección
        for collection_name in collections:
            await db[collection_name].drop()
            logger.info(f"  ✅ Eliminada: {collection_name}")

        logger.info("\n" + "="*50)
        logger.info("🎉 Database reseteada exitosamente!")
        logger.info("="*50)
        logger.info("\nPróximos pasos:")
        logger.info("  1. Ejecuta: python scripts/seed_db.py")
        logger.info("  2. O inicia la API: make dev o uvicorn app.main:app --reload")

    except Exception as e:
        logger.error(f"\n❌ Error reseteando database: {e}")
        raise
    finally:
        # Asegurarse de cerrar la conexión
        if client:
            await close_db_connection()


if __name__ == "__main__":
    asyncio.run(reset_database())
