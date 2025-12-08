# database/migrations/migrate.py
import importlib
import sys
from datetime import datetime
from pathlib import Path

# AÑADIR ESTO AL INICIO para que Python encuentre los módulos
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def run_migrations():
    """Ejecuta todas las migraciones pendientes"""
    from app.database.connection import get_database  # ← ajustado

    db = get_database()

    # Crear colección para trackear migraciones
    if "migration_history" not in db.list_collection_names():
        db.create_collection("migration_history")

    # Obtener migraciones en orden numérico
    versions_dir = Path(__file__).parent / "versions"
    migration_files = sorted([
        f for f in versions_dir.glob("*.py")
        if f.name != "__init__.py" and f.name[0].isdigit()
    ])

    print(f"Encontradas {len(migration_files)} migraciones")

    applied = 0
    for migration_file in migration_files:
        migration_name = migration_file.stem  # ej: "001_initial_setup"

        # Verificar si ya se aplicó
        if db.migration_history.find_one({"name": migration_name}):
            print(f"⏭Saltando: {migration_name} (ya aplicada)")
            continue

        print(f"Aplicando: {migration_name}")

        try:
            # Importar dinámicamente
            module = importlib.import_module(f"database.migrations.versions.{migration_name}")

            # Ejecutar upgrade
            module.upgrade(db)

            # Registrar como aplicada
            db.migration_history.insert_one({
                "name": migration_name,
                "applied_at": datetime.utcnow(),
                "file": migration_file.name
            })

            print(f"{migration_name} completada")
            applied += 1

        except Exception as e:
            print(f"Error en {migration_name}: {type(e).__name__}: {e}")
            raise

    print(rf"\{applied} migraciones aplicadas exitosamente")
    return applied

if __name__ == "__main__":
    run_migrations()
