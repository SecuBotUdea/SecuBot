"""
Script de validación rápida del RuleEngine (sin conexión a BD)

Este script valida que todos los componentes del RuleEngine funcionan
correctamente sin necesidad de MongoDB.

Ejecutar:
    python scripts/validate_rule_engine.py
"""

from pathlib import Path
from datetime import datetime, timedelta
import sys

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.engines.rule_engine.loader import RuleLoader
from app.engines.rule_engine.condition_evaluator import ConditionEvaluator
from app.engines.rule_engine.point_calculator import PointCalculator


def print_section(title: str):
    """Helper para imprimir secciones"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def validate_rule_loader():
    """Valida que RuleLoader funciona"""
    print_section("1. VALIDANDO RULE LOADER")
    
    try:
        # Cargar rules.yaml
        rules_path = Path("config/rules.yaml")
        loader = RuleLoader(rules_path)
        loader.load()
        
        print("✅ rules.yaml cargado correctamente")
        
        # Verificar configuración
        config = loader.get_config()
        print(f"✅ Configuración global: {config.point_system['currency_name']}")
        
        # Verificar reglas de puntos
        point_rules = loader.get_rules_by_type("points")
        print(f"✅ Reglas de puntos encontradas: {len(point_rules)}")
        
        # Verificar regla específica
        rule = loader.get_rule_by_id("PTS-001")
        if rule:
            print(f"✅ Regla PTS-001: {rule.name} ({rule.action.points} puntos)")
        
        # Verificar badges
        badges = loader.get_all_active_badges()
        print(f"✅ Badges encontrados: {len(badges)}")
        
        return True
    
    except Exception as e:
        print(f"❌ Error en RuleLoader: {e}")
        return False


def validate_condition_evaluator():
    """Valida que ConditionEvaluator funciona"""
    print_section("2. VALIDANDO CONDITION EVALUATOR")
    
    try:
        # Contexto de prueba
        context = {
            "Alert": {
                "alert_id": "test_001",
                "severity": "CRITICAL",
                "quality": "high",
                "status": "pending_verification",
                "first_seen": datetime.utcnow() - timedelta(hours=12)
            },
            "Remediation": {
                "user_id": "user_123",
                "type": "user_mark",
                "action_ts": datetime.utcnow() - timedelta(hours=6)
            },
            "RescanResult": {
                "present": False
            }
        }
        
        evaluator = ConditionEvaluator(context)
        
        # Test 1: Igualdad
        result1 = evaluator.evaluate("Alert.severity == 'CRITICAL'")
        print(f"✅ Igualdad: Alert.severity == 'CRITICAL' → {result1}")
        assert result1 is True
        
        # Test 2: Operador IN
        result2 = evaluator.evaluate("Alert.quality IN ['high', 'medium']")
        print(f"✅ Operador IN: Alert.quality IN ['high', 'medium'] → {result2}")
        assert result2 is True
        
        # Test 3: Boolean
        result3 = evaluator.evaluate("RescanResult.present == false")
        print(f"✅ Boolean: RescanResult.present == false → {result3}")
        assert result3 is True
        
        # Test 4: Múltiples condiciones
        conditions = [
            "Alert.severity == 'CRITICAL'",
            "Alert.quality == 'high'",
            "RescanResult.present == false"
        ]
        result4 = evaluator.evaluate_all(conditions, operator="AND")
        print(f"✅ Múltiples condiciones (AND): → {result4}")
        assert result4 is True
        
        # Test 5: Tiempo
        result5 = evaluator.evaluate("(Remediation.action_ts - Alert.first_seen) < 24 hours")
        print(f"✅ Comparación temporal: diferencia < 24h → {result5}")
        assert result5 is True
        
        return True
    
    except Exception as e:
        print(f"❌ Error en ConditionEvaluator: {e}")
        import traceback
        traceback.print_exc()
        return False


def validate_point_calculator():
    """Valida que PointCalculator funciona"""
    print_section("3. VALIDANDO POINT CALCULATOR")
    
    try:
        calculator = PointCalculator()
        
        # Test 1: Cálculo básico
        points1 = calculator.calculate(base_points=100)
        print(f"✅ Cálculo básico: 100 base → {points1} puntos")
        assert points1 == 100
        
        # Test 2: Con multiplicador
        points2 = calculator.calculate(base_points=100, user_level_multiplier=1.5)
        print(f"✅ Con multiplicador: 100 × 1.5 → {points2} puntos")
        assert points2 == 150
        
        # Test 3: Con bonus
        points3 = calculator.calculate(base_points=100, bonus_points=50)
        print(f"✅ Con bonus: 100 + 50 → {points3} puntos")
        assert points3 == 150
        
        # Test 4: Niveles
        level1 = calculator.calculate_user_level(0)
        level2 = calculator.calculate_user_level(1000)
        level5 = calculator.calculate_user_level(10000)
        print(f"✅ Niveles: 0pts→L{level1}, 1000pts→L{level2}, 10000pts→L{level5}")
        
        # Test 5: Multiplicadores
        mult3 = calculator.get_level_multiplier(3)
        mult5 = calculator.get_level_multiplier(5)
        print(f"✅ Multiplicadores: Nivel 3→{mult3}x, Nivel 5→{mult5}x")
        
        # Test 6: Progreso
        progress = calculator.calculate_progress_to_next_level(1000)
        print(f"✅ Progreso: 1000 pts → Nivel {progress['current_level']}, " +
              f"{progress['points_needed']} pts para siguiente")
        
        return True
    
    except Exception as e:
        print(f"❌ Error en PointCalculator: {e}")
        import traceback
        traceback.print_exc()
        return False


def validate_integration():
    """Valida integración entre componentes"""
    print_section("4. VALIDANDO INTEGRACIÓN")
    
    try:
        # Cargar reglas
        rules_path = Path("config/rules.yaml")
        loader = RuleLoader(rules_path)
        loader.load()
        
        # Obtener regla PTS-001
        rule = loader.get_rule_by_id("PTS-001")
        assert rule is not None
        print(f"✅ Regla obtenida: {rule.rule_id}")
        
        # Crear contexto que cumple condiciones
        context = {
            "Alert": {
                "severity": "CRITICAL",
                "quality": "high",
                "status": "pending_verification"
            },
            "Remediation": {
                "user_id": "user_123",
                "type": "user_mark"
            },
            "RescanResult": {
                "present": False
            }
        }
        
        # Evaluar condiciones
        evaluator = ConditionEvaluator(context)
        result = evaluator.evaluate_all(rule.trigger.conditions, operator="AND")
        print(f"✅ Condiciones evaluadas: {result}")
        
        if result:
            # Calcular puntos
            calculator = PointCalculator()
            points = calculator.calculate_from_rule(
                rule_points=rule.action.points,
                user_level=3  # Nivel 3
            )
            print(f"✅ Puntos calculados: {rule.action.points} × 1.1 = {points} puntos")
            print(f"✅ Razón: {rule.action.reason}")
        
        return True
    
    except Exception as e:
        print(f"❌ Error en integración: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Ejecuta todas las validaciones"""
    print("\n" + "🔍 VALIDANDO RULE ENGINE - FASE 2".center(70))
    print("=" * 70)
    
    results = {
        "RuleLoader": validate_rule_loader(),
        "ConditionEvaluator": validate_condition_evaluator(),
        "PointCalculator": validate_point_calculator(),
        "Integración": validate_integration()
    }
    
    # Resumen
    print_section("RESUMEN DE VALIDACIÓN")
    
    all_passed = True
    for component, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{component:.<50} {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 70)
    
    if all_passed:
        print("🎉 TODOS LOS COMPONENTES FUNCIONAN CORRECTAMENTE".center(70))
        print("\n✅ El RuleEngine está listo para usar!")
        print("\nPróximos pasos:")
        print("  1. Ejecutar tests unitarios: pytest tests/unit/engines/ -v")
        print("  2. Conectar con MongoDB y probar el engine completo")
        print("  3. Continuar con Fase 3: Servicios de negocio")
        return 0
    else:
        print("❌ ALGUNOS COMPONENTES TIENEN ERRORES".center(70))
        print("\nRevisa los errores arriba y corrige antes de continuar.")
        return 1


if __name__ == "__main__":
    exit(main())