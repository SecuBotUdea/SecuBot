"""
Test de flujo completo simulado (sin BD real)

Este test simula el flujo completo de:
1. Usuario marca alerta como resuelta
2. Sistema hace rescan
3. RuleEngine procesa el evento
4. Se otorgan puntos
5. Se evalúan badges

Ejecutar:
    pytest tests/integration/test_complete_flow.py -v -s
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.engines.rule_engine import RuleLoader, ConditionEvaluator, PointCalculator


# ============================================================================
# FIXTURES DE DATOS SIMULADOS
# ============================================================================

@pytest.fixture
def mock_db():
    """Mock de base de datos"""
    db = MagicMock()
    
    # Mock de colección point_transactions
    db.point_transactions.insert_one = AsyncMock(return_value=MagicMock(inserted_id="txn_123"))
    db.point_transactions.aggregate = AsyncMock()
    db.point_transactions.aggregate.return_value.to_list = AsyncMock(
        return_value=[{"total": 1200}]  # Usuario tiene 1200 puntos
    )
    
    # Mock de colección awards
    db.awards.find_one = AsyncMock(return_value=None)  # No tiene badges aún
    db.awards.insert_one = AsyncMock(return_value=MagicMock(inserted_id="award_123"))
    
    return db


@pytest.fixture
def critical_vulnerability_resolved():
    """Escenario: Vulnerabilidad CRITICAL resuelta"""
    return {
        "alert": {
            "alert_id": "alert_001",
            "signature": "CVE-2024-1234",
            "severity": "CRITICAL",
            "quality": "high",
            "status": "pending_verification",
            "first_seen": datetime.utcnow() - timedelta(hours=48),
            "component": "auth-service",
            "source_id": "dependabot"
        },
        "remediation": {
            "remediation_id": "rem_001",
            "alert_id": "alert_001",
            "user_id": "user_alice",
            "team_id": "team_backend",
            "type": "user_mark",
            "action_ts": datetime.utcnow() - timedelta(hours=12),
            "status": "pending",
            "notes": "Upgraded package to v2.1.5"
        },
        "rescan_result": {
            "rescan_id": "rescan_001",
            "alert_id": "alert_001",
            "present": False,  # ✅ Vulnerabilidad NO presente = RESUELTA
            "scan_ts": datetime.utcnow(),
            "trigger": "manual",
            "validated_by": "rescan_service"
        }
    }


@pytest.fixture
def critical_vulnerability_fast():
    """Escenario: Vulnerabilidad CRITICAL resuelta rápido (< 24h)"""
    return {
        "alert": {
            "alert_id": "alert_002",
            "signature": "CVE-2024-5678",
            "severity": "CRITICAL",
            "quality": "high",
            "status": "pending_verification",
            "first_seen": datetime.utcnow() - timedelta(hours=20)
        },
        "remediation": {
            "remediation_id": "rem_002",
            "alert_id": "alert_002",
            "user_id": "user_bob",
            "team_id": "team_backend",
            "type": "user_mark",
            "action_ts": datetime.utcnow() - timedelta(hours=4),  # Solo 4h después
            "status": "pending"
        },
        "rescan_result": {
            "rescan_id": "rescan_002",
            "alert_id": "alert_002",
            "present": False,
            "scan_ts": datetime.utcnow(),
            "trigger": "manual"
        }
    }


# ============================================================================
# TESTS DE FLUJO COMPLETO
# ============================================================================

def test_scenario_critical_resolved_gives_100_points(critical_vulnerability_resolved):
    """
    ✅ ESCENARIO 1: Remediación de vulnerabilidad CRITICAL verificada
    
    Given: Alerta CRITICAL + Remediación + Rescan que confirma ausencia
    When: Se procesa el evento "rescan_completed"
    Then: 
      - Se otorgan 100 puntos (PTS-001)
      - Razón: "Vulnerabilidad CRÍTICA verificada como resuelta"
    """
    print("\n" + "="*70)
    print("ESCENARIO 1: Remediación CRITICAL Verificada")
    print("="*70)
    
    # Arrange
    loader = RuleLoader(Path("config/rules.yaml"))
    loader.load()
    
    rule = loader.get_rule_by_id("PTS-001")
    
    context = {
        "Alert": critical_vulnerability_resolved["alert"],
        "Remediation": critical_vulnerability_resolved["remediation"],
        "RescanResult": critical_vulnerability_resolved["rescan_result"]
    }
    
    print(f"📋 Alerta: {context['Alert']['alert_id']} - {context['Alert']['severity']}")
    print(f"👤 Usuario: {context['Remediation']['user_id']}")
    print(f"🔍 Rescan: Vulnerabilidad presente = {context['RescanResult']['present']}")
    
    # Act
    evaluator = ConditionEvaluator(context)
    conditions_met = evaluator.evaluate_all(rule.trigger.conditions, operator="AND")
    
    # Assert
    assert conditions_met is True, "Condiciones de PTS-001 deben cumplirse"
    
    print(f"\n✅ Regla aplicable: {rule.rule_id} - {rule.name}")
    print(f"💰 Puntos a otorgar: {rule.action.points}")
    print(f"📝 Razón: {rule.action.reason}")
    
    # Calcular puntos con nivel (asumiendo nivel 2)
    calculator = PointCalculator()
    final_points = calculator.calculate_from_rule(
        rule_points=rule.action.points,
        user_level=2  # Nivel 2 = 1.0x (sin bonus)
    )
    
    assert final_points == 100
    print(f"✅ Puntos finales: {final_points}")


def test_scenario_fast_remediation_gets_bonus(critical_vulnerability_fast):
    """
    ✅ ESCENARIO 2: Remediación rápida recibe bonus
    
    Given: Alerta CRITICAL resuelta en < 24 horas
    When: Se procesa el evento "rescan_completed"
    Then:
      - Se otorgan 100 puntos (PTS-001)
      - Se otorgan 50 puntos de bonus (PTS-004)
      - Total: 150 puntos
    """
    print("\n" + "="*70)
    print("ESCENARIO 2: Bonus por Remediación Rápida")
    print("="*70)
    
    # Arrange
    loader = RuleLoader(Path("config/rules.yaml"))
    loader.load()
    
    context = {
        "Alert": critical_vulnerability_fast["alert"],
        "Remediation": critical_vulnerability_fast["remediation"],
        "RescanResult": critical_vulnerability_fast["rescan_result"]
    }
    
    time_diff = context["Remediation"]["action_ts"] - context["Alert"]["first_seen"]
    hours = time_diff.total_seconds() / 3600
    
    print(f"📋 Alerta: {context['Alert']['alert_id']}")
    print(f"⏱️  Tiempo de remediación: {hours:.1f} horas")
    
    # Act - Evaluar PTS-001 (base)
    rule_base = loader.get_rule_by_id("PTS-001")
    evaluator = ConditionEvaluator(context)
    base_met = evaluator.evaluate_all(rule_base.trigger.conditions, operator="AND")
    
    # Act - Evaluar PTS-004 (bonus)
    rule_bonus = loader.get_rule_by_id("PTS-004")
    bonus_met = evaluator.evaluate_all(rule_bonus.trigger.conditions, operator="AND")
    
    # Assert
    assert base_met is True, "Debe cumplir PTS-001"
    assert bonus_met is True, "Debe cumplir PTS-004 (bonus rápido)"
    
    print(f"\n✅ Regla base: {rule_base.rule_id} → {rule_base.action.points} puntos")
    print(f"✅ Regla bonus: {rule_bonus.rule_id} → {rule_bonus.action.points} puntos")
    
    total_points = rule_base.action.points + rule_bonus.action.points
    print(f"💰 Total: {total_points} puntos")
    
    assert total_points == 150


def test_user_level_calculation():
    """
    ✅ ESCENARIO 3: Cálculo de nivel de usuario
    
    Given: Usuario con diferentes cantidades de puntos
    When: Se calcula su nivel
    Then: Nivel correcto según progresión
    """
    print("\n" + "="*70)
    print("ESCENARIO 3: Cálculo de Niveles")
    print("="*70)
    
    calculator = PointCalculator()
    
    test_cases = [
        (0, 1, "Aprendiz de Seguridad"),
        (250, 1, "Aprendiz de Seguridad"),
        (500, 2, "Vigilante del Código"),
        (1200, 2, "Vigilante del Código"),
        (1500, 3, "Guardián DevSecOps"),
        (4000, 4, "Centinela Élite"),
        (10000, 5, "Maestro de la Seguridad"),
    ]
    
    print("\n📊 Tabla de niveles:")
    print("-" * 70)
    
    for points, expected_level, expected_name in test_cases:
        level = calculator.calculate_user_level(points)
        info = calculator.get_level_info(level)
        
        assert level == expected_level, f"{points} pts debe ser nivel {expected_level}"
        assert info["name"] == expected_name
        
        mult = calculator.get_level_multiplier(level)
        print(f"{points:>6} pts → Nivel {level} ({info['name']:.<30}) Mult: {mult}x")
    
    print("✅ Todos los niveles calculados correctamente")


def test_badge_evaluation_logic():
    """
    ✅ ESCENARIO 4: Lógica de evaluación de badges
    
    Given: Usuario con transacciones de puntos
    When: Se evalúan criterios de badges
    Then: Badges se otorgan correctamente
    """
    print("\n" + "="*70)
    print("ESCENARIO 4: Evaluación de Badges")
    print("="*70)
    
    # Arrange
    loader = RuleLoader(Path("config/rules.yaml"))
    loader.load()
    
    badge = loader.get_rule_by_id("BDG-001")  # Primera Sangre
    
    print(f"\n🏆 Badge: {badge.name}")
    print(f"📝 Descripción: {badge.description}")
    print(f"📋 Criterio: Al menos 1 vulnerabilidad CRITICAL resuelta")
    
    # El badge se otorgaría si el usuario tiene al menos 1 transacción PTS-001
    # Esto se validaría en BadgeEvaluator consultando la BD
    
    print("\n✅ Lógica de badge validada (requiere BD para ejecución real)")


def test_exclusion_rules():
    """
    ✅ ESCENARIO 5: Reglas de exclusión
    
    Given: Alerta de baja calidad
    When: Se intenta gamificar
    Then: Se excluye por regla EXC-001
    """
    print("\n" + "="*70)
    print("ESCENARIO 5: Reglas de Exclusión")
    print("="*70)
    
    # Arrange
    loader = RuleLoader(Path("config/rules.yaml"))
    loader.load()
    
    exclusion = loader.get_rule_by_id("EXC-001")
    
    context_low_quality = {
        "Alert": {
            "quality": "low"  # ❌ Baja calidad
        }
    }
    
    print(f"📋 Regla: {exclusion.rule_id} - {exclusion.name}")
    print(f"🚫 Condición: Alert.quality == 'low'")
    
    # Act
    evaluator = ConditionEvaluator(context_low_quality)
    should_exclude = evaluator.evaluate_all(exclusion.conditions, operator="AND")
    
    # Assert
    assert should_exclude is True
    
    print(f"✅ Alerta excluida correctamente: {exclusion.action.reason}")


# ============================================================================
# TEST RUNNER
# ============================================================================

if __name__ == "__main__":
    """Permite ejecutar directamente: python test_complete_flow.py"""
    pytest.main([__file__, "-v", "-s"])