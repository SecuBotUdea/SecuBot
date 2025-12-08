# database/migrations/versions/001_initial_setup.py
from datetime import datetime, timezone


def upgrade(db):
    """
    Configuración inicial de la base de datos SecuBot.
    Compatible con el modelo User sin password.
    """

    # 1. Crear colección users si no existe (MongoDB la crea automáticamente)
    # pero definimos índices importantes

    # Índices únicos para username y email
    db.users.create_index("username", unique=True)
    db.users.create_index("email", unique=True)

    # Índices para búsquedas comunes
    db.users.create_index("role")
    db.users.create_index("team_id")
    db.users.create_index("created_at")
    db.users.create_index("is_active")
    db.users.create_index("email_verified")

    # Índice compuesto para consultas frecuentes
    db.users.create_index([("role", 1), ("is_active", 1)])

    print("Índices de usuarios creados")

    # 2. Crear usuario administrador inicial
    if db.users.count_documents({"email": "admin@secubot.com"}) == 0:
        admin_user = {
            "_id": "admin_001",  # id del modelo se mapea a _id
            "username": "admin",
            "display_name": "Administrador del Sistema",
            "email": "admin@secubot.com",
            "role": "super_admin",
            "team_id": None,
            "metadata": {
                "is_initial_admin": True,
                "password_reset_required": False,
                "notes": "Usuario administrador inicial"
            },
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            # schema_version viene de BaseModelDB (si lo incluyes)
        }

        db.users.insert_one(admin_user)
        print("Usuario administrador creado")
        print("Email: admin@secubot.com")
        print("Username: admin")
        print("Role: super_admin")

    # 3. Crear colección de logs de acceso
    if "access_logs" not in db.list_collection_names():
        db.create_collection("access_logs")

    # Índices para logs
    db.access_logs.create_index("user_id")  # Referencia al _id del usuario
    db.access_logs.create_index("timestamp")
    db.access_logs.create_index([("user_id", 1), ("timestamp", -1)])
    db.access_logs.create_index("action")

    print("Colección de logs configurada")

    # 4. Crear colección de configuraciones del sistema
    if "system_configs" not in db.list_collection_names():
        db.create_collection("system_configs")

        # Configuración inicial del sistema
        db.system_configs.insert_one({
            "_id": "security_settings",
            "name": "Configuración de Seguridad",
            "max_login_attempts": 5,
            "session_timeout_minutes": 30,
            "require_2fa": False,
            "password_min_length": 8,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        })

        db.system_configs.insert_one({
            "_id": "audit_settings",
            "name": "Configuración de Auditoría",
            "log_retention_days": 90,
            "log_sensitive_data": False,
            "created_at": datetime.now(timezone.utc)
        })

        print("Configuraciones del sistema creadas")

    # 5. Crear colección de equipos (teams) si tu app los usa
    if "teams" not in db.list_collection_names():
        db.create_collection("teams")

        db.teams.create_index("name", unique=True)
        db.teams.create_index("created_at")

        # Equipo por defecto
        db.teams.insert_one({
            "_id": "default_team",
            "name": "Equipo Principal",
            "description": "Equipo por defecto del sistema",
            "created_at": datetime.now(timezone.utc)
        })

        print("Colección de equipos creada")

def downgrade(db):
    """Rollback para desarrollo (opcional)"""
    print("Rollback de migración inicial")

    # Eliminar índices pero NO colecciones (para no perder datos)
    try:
        db.users.drop_indexes()
        print("   Índices de usuarios eliminados")
    except:  # noqa: E722
        pass

    try:
        db.access_logs.drop_indexes()
        print("   Índices de logs eliminados")
    except:  # noqa: E722
        pass

    try:
        db.system_configs.drop_indexes()
        print("   Índices de configuraciones eliminados")
    except:  # noqa: E722
        pass

    try:
        db.teams.drop_indexes()
        print("   Índices de equipos eliminados")
    except:  # noqa: E722
        pass
