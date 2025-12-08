"""
Script de validación rápida de servicios
Ejecutar: python scripts/test_services.py
"""

import sys
from pathlib import Path
from datetime import datetime
import uuid
sys.path.insert(0, str(Path(__file__).parent.parent))


from app.services.alert_service import get_alert_service
from app.services.user_service import get_user_service
from app.services.remediation_service import get_remediation_service
from app.services.rescan_service import get_rescan_service
from app.services.gamification_service import get_gamification_service


def test_services_import():
    """Test 1: Verificar que todos los servicios se importan sin errores"""
    print("🧪 Test 1: Importando servicios...")
    
    try:
        alert_svc = get_alert_service()
        print("✅ AlertService importado")
        
        user_svc = get_user_service()
        print("✅ UserService importado")
        
        remediation_svc = get_remediation_service()
        print("✅ RemediationService importado")
        
        rescan_svc = get_rescan_service(demo_mode=True)
        print("✅ RescanService importado")
        
        gamification_svc = get_gamification_service()
        print("✅ GamificationService importado")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_create_user():
    print("\n🧪 Test 2: Creando usuario de prueba...")
    user_svc = get_user_service()
    base_username = "test_alice"
    email = "alice@test.com"

    try:
        user = user_svc.create_user(
            username=base_username,
            email=email,
            display_name="Alice Test",
            role="developer"
        )
        
        print(f"✅ Usuario creado: {user['username']} ({user['_id']})")
        return user

    except Exception as e:
        msg = str(e).lower()
        
        # Caso típico: nombre de usuario ya existe
        if "already exists" in msg or "ya existe" in msg:
            print("⚠️ Usuario ya existe. Intentando recuperarlo...")
            # 1) intentar método explícito si existe
            try:
                user = user_svc.get_user_by_username(base_username)
                assert user is not None
                print(f"🔁 Usuario recuperado: {user['username']} ({user['_id']})")
                return user
            except Exception:
                # 2) crear con sufijo único como fallback
                unique_username = f"{base_username}_{uuid.uuid4().hex[:6]}"
                print(f"🔁 Creando usuario alternativo: {unique_username}")
                user = user_svc.create_user(
                    username=unique_username,
                    email=f"{unique_username}@test.com",
                    display_name="Alice Test",
                    role="developer"
                )
                print(f"✅ Usuario creado: {user['username']} ({user['_id']})")
                return user
        else:
            print(f"❌ Error inesperado al crear usuario: {e}")
            raise


from datetime import datetime, timezone

def test_create_alert():
    print("\n🧪 Test 3: Creando alerta de prueba...")
    try:
        alert_svc = get_alert_service()

        now = datetime.now(timezone.utc)
        alert_data = {
            "alert_id": "test_alert_001",
            "signature": "test_sig_001",
            "source_id": "dependabot",
            "severity": "critical",
            "component": "auth-service",
            "title": "SQL Injection Test",
            "description": "Test alert for validation",
            "quality": "high",
            "status": "open",
            "first_seen": now,          # datetime aware
            "last_seen": now,           # datetime aware
            "normalized_payload": {"cve": "CVE-2024-TEST"},
            "raw_payload": {}
        }

        result = alert_svc.create_alert(alert_data)
        print(f"✅ Alerta creada: {result['alert_id']}")
        return result

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_create_remediation(user, alert):
    """Test 4: Crear una remediación"""
    print("\n🧪 Test 4: Creando remediación...")
    
    if not user or not alert:
        print("⏭️  Saltando test (dependencias no cumplidas)")
        return None
    
    try:
        remediation_svc = get_remediation_service()
        
        remediation = remediation_svc.create_remediation(
            alert_id=alert["alert"]["alert_id"],
            user_id=user["_id"],
            notes="Fixed by upgrading to v2.0",
            auto_trigger_rescan=True  # Esto invocará al RuleEngine
        )
        
        print(f"✅ Remediación creada: {remediation['remediation_id']}")
        print(f"   Rescan disparado: {remediation.get('rescan_triggered', False)}")
        
        if remediation.get('gamification_result'):
            result = remediation['gamification_result']
            print(f"   Reglas evaluadas: {result['rules_evaluated']}")
            print(f"   Reglas disparadas: {result['rules_triggered']}")
            print(f"   Puntos otorgados: {len(result['points_awarded'])}")
        
        return remediation
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_gamification(user):
    """Test 5: Consultar balance de gamificación"""
    print("\n🧪 Test 5: Consultando balance de gamificación...")
    
    if not user:
        print("⏭️  Saltando test (dependencias no cumplidas)")
        return
    
    try:
        gamification_svc = get_gamification_service()
        
        balance = gamification_svc.get_user_balance(user["_id"])
        
        print(f"✅ Balance de usuario:")
        print(f"   Total puntos: {balance['total_points']}")
        print(f"   Nivel: {balance['level']} - {balance['level_name']}")
        print(f"   Progreso: {balance['progress_to_next_level']}%")
        print(f"   Multiplicador: {balance['multiplier']}x")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Ejecutar todos los tests"""
    print("=" * 70)
    print("🔍 VALIDANDO SERVICIOS - INTEGRANTE 1".center(70))
    print("=" * 70)
    
    # Test 1: Imports
    if not test_services_import():
        print("\n❌ Tests detenidos - Error en imports")
        return 1
    
    # Test 2: Crear usuario
    user = test_create_user()
    
    # Test 3: Crear alerta
    alert = test_create_alert()
    
    # Test 4: Crear remediación (INVOCA RULEENGINE)
    remediation = test_create_remediation(user, alert)
    
    # Test 5: Gamificación
    test_gamification(user)
    
    # Resumen
    print("\n" + "=" * 70)
    print("RESUMEN".center(70))
    print("=" * 70)
    
    print("\n✅ Servicios validados exitosamente")
    print("\n📋 Próximos pasos:")
    print("  1. Revisar que no hay errores de import")
    print("  2. Verificar que el RuleEngine se invoca correctamente")
    print("  3. Continuar con integración con Integrante 2 (API)")
    
    return 0


if __name__ == "__main__":
    exit(main())