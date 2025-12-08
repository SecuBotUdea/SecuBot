"""
Tests simples para ConditionEvaluator

Ejecutar:
    pytest tests/unit/engines/test_condition_evaluator.py -v
"""

import pytest
from datetime import datetime, timedelta
from app.engines.rule_engine.condition_evaluator import ConditionEvaluator


@pytest.fixture
def simple_alert():
    """Alerta simple para testing"""
    return {
        "alert_id": "alert_123",
        "severity": "CRITICAL",
        "quality": "high",
        "status": "pending_verification"
    }


def test_can_evaluate_simple_equality(simple_alert):
    """✅ Test: Puedo evaluar igualdad simple"""
    context = {"Alert": simple_alert}
    evaluator = ConditionEvaluator(context)
    
    result = evaluator.evaluate("Alert.severity == 'CRITICAL'")
    
    assert result is True
    print("✅ Evaluación: Alert.severity == 'CRITICAL' → True")


def test_can_evaluate_false_condition(simple_alert):
    """✅ Test: Detecta cuando una condición es falsa"""
    context = {"Alert": simple_alert}
    evaluator = ConditionEvaluator(context)
    
    result = evaluator.evaluate("Alert.severity == 'LOW'")
    
    assert result is False
    print("✅ Evaluación: Alert.severity == 'LOW' → False")


def test_can_evaluate_in_operator(simple_alert):
    """✅ Test: Operador IN funciona"""
    context = {"Alert": simple_alert}
    evaluator = ConditionEvaluator(context)
    
    result = evaluator.evaluate("Alert.quality IN ['high', 'medium']")
    
    assert result is True
    print("✅ Evaluación: Alert.quality IN ['high', 'medium'] → True")


def test_can_evaluate_boolean():
    """✅ Test: Puedo evaluar booleanos"""
    context = {
        "RescanResult": {
            "present": False
        }
    }
    evaluator = ConditionEvaluator(context)
    
    result = evaluator.evaluate("RescanResult.present == false")
    
    assert result is True
    print("✅ Evaluación: RescanResult.present == false → True")


def test_can_evaluate_multiple_conditions(simple_alert):
    """✅ Test: Puedo evaluar múltiples condiciones con AND"""
    context = {
        "Alert": simple_alert,
        "RescanResult": {"present": False}
    }
    evaluator = ConditionEvaluator(context)
    
    conditions = [
        "Alert.severity == 'CRITICAL'",
        "Alert.quality == 'high'",
        "RescanResult.present == false"
    ]
    
    result = evaluator.evaluate_all(conditions, operator="AND")
    
    assert result is True
    print("✅ Evaluación: 3 condiciones con AND → True")


def test_can_evaluate_time_difference():
    """✅ Test: Puedo calcular diferencias de tiempo"""
    now = datetime.utcnow()
    
    context = {
        "Alert": {
            "first_seen": now - timedelta(hours=12)
        },
        "Remediation": {
            "action_ts": now - timedelta(hours=6)
        }
    }
    evaluator = ConditionEvaluator(context)
    
    # La diferencia es ~6 horas, debe ser < 24
    result = evaluator.evaluate("(Remediation.action_ts - Alert.first_seen) < 24 hours")
    
    assert result is True
    print("✅ Evaluación temporal: diferencia < 24 horas → True")


def test_can_detect_missing_field():
    """✅ Test: Maneja campos faltantes correctamente"""
    context = {
        "Alert": {
            "severity": "CRITICAL"
            # quality no existe
        }
    }
    evaluator = ConditionEvaluator(context)
    
    result = evaluator.evaluate("Alert.quality == 'high'")
    
    # Debería ser False porque quality no existe (es None)
    assert result is False
    print("✅ Campo faltante manejado: Alert.quality == None → False")