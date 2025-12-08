"""
Reset Database Script
⚠️ CUIDADO: Elimina TODAS las colecciones de la base de datos
Solo usar en desarrollo
"""

import asyncio
import os
import sys

from motor.motor_asyncio import AsyncIOMotorClient

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.settings import settings


async def reset_database():
    """
    Elimina todas las colecciones de la base de datos
    """
    # Verificar que no estamos en producción
    if settings.environment.lower() == "production":
        print("❌ ERROR: No puedes resetear la base de datos en producción!")
        print("   Cambia ENVIRONMENT en .env a 'development' o 'testing'")
        return

    print("⚠️  WARNING: Esto eliminará TODOS los datos de la base de datos")
    print(f"   Database: {settings.database_name}")
    print(f"   Environment: {settings.environment}")

    # Pedir confirmación
    response = input("\n¿Estás seguro? Escribe 'DELETE' para confirmar: ")

    if response != "DELETE":
        print("❌ Operación cancelada")
        return

    print("\n🗑️  Reseteando database...")

    # Conectar a MongoDB
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.database_name]

    try:
        # Obtener todas las colecciones
        collections = await db.list_collection_names()

        if not collections:
            print("No hay colecciones para eliminar")
            return

        print(f"\nColecciones a eliminar: {', '.join(collections)}")

        # Eliminar cada colección
        for collection_name in collections:
            await db[collection_name].drop()
            print(f"  ✅ Eliminada: {collection_name}")

        print("\n" + "="*50)
        print("Database reseteada exitosamente!")
        print("="*50)
        print("\nPróximos pasos:")
        print("  1. Ejecuta: python scripts/seed_db.py")
        print("  2. O inicia la API: make dev")

    except Exception as e:
        print(f"\nError reseteando database: {e}")
        raise
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(reset_database())
