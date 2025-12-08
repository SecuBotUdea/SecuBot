"""
Tests simples para PointCalculator

Ejecutar:
    pytest tests/unit/engines/test_point_calculator.py -v
"""

import pytest
from app.engines.rule_engine.point_calculator import PointCalculator


def test_can_calculate_basic_points():
    """✅ Test: Cálculo básico de puntos sin multiplicador"""
    calculator = PointCalculator()
    
    points = calculator.calculate(base_points=100)
    
    assert points == 100
    print("✅ 100 puntos base → 100 puntos finales")


def test_can_calculate_with_level_multiplier():
    """✅ Test: Multiplicador de nivel funciona"""
    calculator = PointCalculator()
    
    # Nivel 3 tiene multiplicador 1.1x
    points = calculator.calculate(
        base_points=100,
        user_level_multiplier=1.1
    )
    
    assert points == 110
    print("✅ 100 puntos × 1.1 → 110 puntos")


def test_can_calculate_with_bonus():
    """✅ Test: Bonus se suma correctamente"""
    calculator = PointCalculator()
    
    points = calculator.calculate(
        base_points=100,
        bonus_points=50
    )
    
    assert points == 150
    print("✅ 100 base + 50 bonus → 150 puntos")


def test_can_calculate_negative_penalty():
    """✅ Test: Penalizaciones (puntos negativos)"""
    calculator = PointCalculator(allow_negative=True)
    
    points = calculator.calculate(base_points=-50)
    
    assert points == -50
    print("✅ Penalización: -50 puntos")


def test_can_get_level_from_points():
    """✅ Test: Calcular nivel desde puntos totales"""
    calculator = PointCalculator()
    
    # Según rules.yaml
    level_1 = calculator.calculate_user_level(0)      # 0-499
    level_2 = calculator.calculate_user_level(500)    # 500-1499
    level_3 = calculator.calculate_user_level(1500)   # 1500-3999
    level_4 = calculator.calculate_user_level(4000)   # 4000-9999
    level_5 = calculator.calculate_user_level(10000)  # 10000+
    
    assert level_1 == 1
    assert level_2 == 2
    assert level_3 == 3
    assert level_4 == 4
    assert level_5 == 5
    
    print("✅ Niveles calculados correctamente:")
    print(f"   0 puntos → Nivel {level_1}")
    print(f"   500 puntos → Nivel {level_2}")
    print(f"   1500 puntos → Nivel {level_3}")
    print(f"   4000 puntos → Nivel {level_4}")
    print(f"   10000 puntos → Nivel {level_5}")


def test_can_get_level_multiplier():
    """✅ Test: Multiplicador correcto por nivel"""
    calculator = PointCalculator()
    
    mult_1 = calculator.get_level_multiplier(1)
    mult_3 = calculator.get_level_multiplier(3)
    mult_5 = calculator.get_level_multiplier(5)
    
    assert mult_1 == 1.0
    assert mult_3 == 1.1
    assert mult_5 == 1.5
    
    print("✅ Multiplicadores por nivel:")
    print(f"   Nivel 1 → {mult_1}x")
    print(f"   Nivel 3 → {mult_3}x")
    print(f"   Nivel 5 → {mult_5}x")


def test_can_get_level_info():
    """✅ Test: Información completa de nivel"""
    calculator = PointCalculator()
    
    info = calculator.get_level_info(3)
    
    assert info["name"] == "Guardián DevSecOps"
    assert info["min_points"] == 1500
    assert info["max_points"] == 3999
    assert "Multiplicador de puntos x1.1" in info["perks"]
    
    print(f"✅ Nivel 3: {info['name']}")
    print(f"   Rango: {info['min_points']}-{info['max_points']} puntos")
    print(f"   Perks: {len(info['perks'])} beneficios")


def test_can_calculate_progress_to_next_level():
    """✅ Test: Progreso hacia siguiente nivel"""
    calculator = PointCalculator()
    
    # Usuario con 1000 puntos (nivel 2)
    progress = calculator.calculate_progress_to_next_level(1000)
    
    assert progress["current_level"] == 2
    assert progress["next_level"] == 3
    assert progress["points_needed"] == 500  # Necesita llegar a 1500
    assert 0 <= progress["progress_percentage"] <= 100
    
    print("✅ Usuario con 1000 puntos:")
    print(f"   Nivel actual: {progress['current_level']}")
    print(f"   Siguiente nivel: {progress['next_level']}")
    print(f"   Puntos necesarios: {progress['points_needed']}")
    print(f"   Progreso: {progress['progress_percentage']:.1f}%")


def test_can_calculate_from_rule():
    """✅ Test: Calcular puntos desde regla aplicando nivel"""
    calculator = PointCalculator()
    
    # Regla otorga 100 puntos, usuario nivel 3 (mult 1.1x)
    points = calculator.calculate_from_rule(
        rule_points=100,
        user_level=3
    )
    
    assert points == 110
    print("✅ 100 puntos de regla × nivel 3 (1.1x) → 110 puntos")