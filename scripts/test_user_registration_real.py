"""
Integration smoke-test: user registration against a real MongoDB instance.

Usage:
    .venv/bin/python scripts/test_user_registration_real.py

Exit codes:
    0 — all checks passed
    1 — one or more checks failed
"""

import asyncio
import sys
import traceback
from datetime import datetime, timezone

TEST_USERNAME = f'smoketest_{datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")}'
TEST_EMAIL = f'{TEST_USERNAME}@smoketest.invalid'

PASS = '✅'
FAIL = '❌'
INFO = '  '


def _log(icon: str, msg: str) -> None:
    print(f'{icon} {msg}')


async def run() -> bool:
    from app.database.mongodb import close_mongo_connection, connect_to_mongo, get_database
    from app.services.user_service import UserService

    failures: list[str] = []

    # ── Connect ───────────────────────────────────────────────────────────────
    _log(INFO, 'Conectando a MongoDB...')
    try:
        await connect_to_mongo()
        _log(PASS, 'Conexión establecida')
    except Exception as e:
        _log(FAIL, f'No se pudo conectar: {e}')
        return False

    db = get_database()
    svc = UserService()

    # ── 1. Create user ────────────────────────────────────────────────────────
    _log(INFO, f'Creando usuario: {TEST_USERNAME}')
    created_user = None
    try:
        created_user = await svc.create_user(
            username=TEST_USERNAME,
            email=TEST_EMAIL,
            display_name='Smoke Test User',
            role='developer',
        )
        _log(PASS, f'Usuario creado con _id={created_user["_id"]}')
    except Exception:
        failures.append('create_user falló')
        _log(FAIL, traceback.format_exc())

    # ── 2. Verify document exists in MongoDB ──────────────────────────────────
    if created_user:
        _log(INFO, 'Verificando que el documento existe en Mongo...')
        try:
            doc = await db.users.find_one({'username': TEST_USERNAME})
            if doc is None:
                failures.append('Documento no encontrado en MongoDB después de insertar')
                _log(FAIL, 'find_one devolvió None — el documento NO se guardó')
            else:
                _log(PASS, f'Documento encontrado en colección "users"')
                _log(INFO, f'  user_id      : {doc.get("user_id")}')
                _log(INFO, f'  role         : {doc.get("role")}')
                _log(INFO, f'  is_active    : {doc.get("is_active")}')
                _log(INFO, f'  email_verified: {doc.get("email_verified")}')
                _log(INFO, f'  created_at   : {doc.get("created_at")}')
        except Exception:
            failures.append('Verificación en Mongo falló')
            _log(FAIL, traceback.format_exc())

    # ── 3. Duplicate username is rejected ─────────────────────────────────────
    _log(INFO, 'Verificando que username duplicado es rechazado...')
    try:
        await svc.create_user(username=TEST_USERNAME, email='other@smoketest.invalid')
        failures.append('Debería haber lanzado ValueError para username duplicado')
        _log(FAIL, 'No se lanzó ValueError para username duplicado')
    except ValueError as e:
        _log(PASS, f'Username duplicado rechazado correctamente: {e}')
    except Exception:
        failures.append('Error inesperado en validación de duplicado')
        _log(FAIL, traceback.format_exc())

    # ── 4. Default role 'developer' passes ────────────────────────────────────
    _log(INFO, 'Verificando que role default "developer" es válido...')
    default_username = f'{TEST_USERNAME}_2'
    default_doc = None
    try:
        default_doc = await svc.create_user(
            username=default_username,
            email=f'{default_username}@smoketest.invalid',
        )
        if default_doc['role'] != 'developer':
            failures.append(f'Role esperado "developer", obtenido "{default_doc["role"]}"')
            _log(FAIL, f'Role incorrecto: {default_doc["role"]}')
        else:
            _log(PASS, 'Role default "developer" guardado correctamente')
    except Exception:
        failures.append('create_user con role default falló')
        _log(FAIL, traceback.format_exc())

    # ── 5. Invalid role is rejected ───────────────────────────────────────────
    _log(INFO, 'Verificando que role inválido "member" es rechazado...')
    try:
        await svc.create_user(
            username=f'{TEST_USERNAME}_bad',
            email=f'{TEST_USERNAME}_bad@smoketest.invalid',
            role='member',
        )
        failures.append('Debería haber lanzado ValueError para role "member"')
        _log(FAIL, 'No se lanzó ValueError para role "member"')
    except ValueError as e:
        _log(PASS, f'Role inválido rechazado correctamente: {e}')
    except Exception:
        failures.append('Error inesperado en validación de role')
        _log(FAIL, traceback.format_exc())

    # ── 6. Simulate auto-registration (discord:{id} pattern) ─────────────────
    _log(INFO, 'Verificando auto-registro con user_id estilo Discord...')
    discord_user_id = 'discord:123456789'
    discord_username = 'discord_123456789'
    try:
        auto_doc = await svc.create_user(
            username=discord_username,
            email=f'{discord_username}@discord.invalid',
            display_name='Test Discord User',
            role='developer',
            user_id=discord_user_id,
        )
        found = await db.users.find_one({'user_id': discord_user_id})
        if found:
            _log(PASS, f'Auto-registro Discord guardado: user_id={found["user_id"]}, display_name={found["display_name"]}')
        else:
            failures.append('Auto-registro Discord no encontrado en Mongo')
            _log(FAIL, 'Documento Discord no encontrado en MongoDB')
    except Exception:
        failures.append('Auto-registro Discord falló')
        _log(FAIL, traceback.format_exc())

    # ── Cleanup ───────────────────────────────────────────────────────────────
    _log(INFO, 'Limpiando documentos de prueba...')
    try:
        result = await db.users.delete_many(
            {'username': {'$in': [TEST_USERNAME, default_username, discord_username]}}
        )
        _log(PASS, f'{result.deleted_count} documento(s) de prueba eliminado(s)')
    except Exception:
        _log(FAIL, f'Limpieza falló (documentos de prueba pueden quedar en DB): {traceback.format_exc()}')

    await close_mongo_connection()

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    if failures:
        print(f'RESULTADO: {FAIL} {len(failures)} falla(s):')
        for f in failures:
            print(f'  - {f}')
        return False
    else:
        print(f'RESULTADO: {PASS} Todos los checks pasaron')
        return True


if __name__ == '__main__':
    ok = asyncio.run(run())
    sys.exit(0 if ok else 1)
