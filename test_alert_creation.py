"""
Script de prueba para AlertService.create_alert()
Prueba la creación de alerta y notificación en vivo a Slack
"""

import asyncio
from datetime import datetime, timezone

from app.database.mongodb import connect_to_mongo, close_mongo_connection
from app.services.alert_service import get_alert_service


async def test_create_alert():
    """Prueba la creación de una alerta y su notificación"""

    print("=" * 60)
    print("[TEST] PRUEBA: AlertService.create_alert()")
    print("=" * 60)

    # 1. Conectar a MongoDB
    print("\n[1] Conectando a MongoDB...")
    await connect_to_mongo()
    print("[OK] Conectado a MongoDB")

    # 2. Obtener instancia del servicio
    print("\n[2] Obteniendo AlertService...")
    alert_service = get_alert_service()
    print("[OK] AlertService obtenido")

    # 3. Preparar datos de alerta de prueba
    print("\n[3] Preparando datos de alerta de prueba...")
    now = datetime.now(timezone.utc)

    alert_data = {
        "alert_id": f"test-alert-direct-{int(now.timestamp())}",
        "signature": f"sql-injection-test-{int(now.timestamp())}",
        "source_id": "test-scanner-semgrep",
        "severity": "CRITICAL",
        "component": "payment-service",
        "status": "open",
        "first_seen": now,
        "last_seen": now,
        "quality": "high",
        "normalized_payload": {
            "description": "[CRITICAL] SQL Injection critico detectado en modulo de pagos - PRUEBA DIRECTA DE ALERTSERVICE",
            "cvss_score": 9.8,
            "cwe": "CWE-89",
            "file_path": "src/payment/process.py",
            "line_number": 234,
            "vulnerable_code": "query = f'SELECT * FROM payments WHERE id={user_input}'",
            "recommendation": "Usar prepared statements o ORM"
        },
        "lifecycle_history": [
            {
                "timestamp": now,
                "old_status": None,
                "new_status": "open",
                "metadata": {"event": "alert_created", "test": True}
            }
        ],
        "reopen_count": 0,
        "version": 1
    }

    print("[OK] Datos preparados:")
    print(f"   - Alert ID: {alert_data['alert_id']}")
    print(f"   - Severidad: {alert_data['severity']}")
    print(f"   - Componente: {alert_data['component']}")

    # 4. Llamar a create_alert()
    print(f"\n[4] Llamando a AlertService.create_alert()...")
    print("   [WAIT] Creando alerta y enviando notificacion a Slack...")

    try:
        result = await alert_service.create_alert(alert_data)

        print("\n[OK] RESULTADO:")
        print(f"   - Status: {result['status']}")
        print(f"   - Message: {result['message']}")
        print(f"   - Alert ID: {result['alert_id']}")

        if result['status'] == 'created':
            print("\n[SUCCESS] Alerta creada exitosamente!")
            print("\n[INFO] Detalles de la alerta:")
            alert = result['alert']
            print(f"   - Severidad: {alert['severity']}")
            print(f"   - Componente: {alert['component']}")
            print(f"   - Estado: {alert['status']}")
            print(f"   - Calidad: {alert['quality']}")

            print("\n[NOTIFICATION] NOTIFICACION:")
            print("   -> La notificacion deberia haber sido enviada a Slack")
            print("   -> Revisa el canal de Slack configurado")
            print("   -> Busca logs de 'Notificacion enviada a Slack'")

    except Exception as e:
        print(f"\n[ERROR] ERROR al crear alerta: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    # 5. Cerrar conexión
    print("\n[5] Cerrando conexion...")
    await close_mongo_connection()
    print("[OK] Conexion cerrada")

    print("\n" + "=" * 60)
    print("[OK] PRUEBA COMPLETADA")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_create_alert())
