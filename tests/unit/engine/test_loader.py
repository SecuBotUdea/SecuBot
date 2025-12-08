"""
Tests simples para RuleLoader

Ejecutar:
    pytest tests/unit/engines/test_rule_loader.py -v
"""

import pytest
from pathlib import Path
from app.engines.rule_engine.loader import RuleLoader


@pytest.fixture
def rules_path():
    """Path al archivo rules.yaml"""
    return Path("config/rules.yaml")


def test_rule_loader_can_load_file(rules_path):
    """✅ Test: El archivo rules.yaml existe y se puede cargar"""
    loader = RuleLoader(rules_path)
    loader.load()
    
    assert loader.is_loaded
    print("✅ rules.yaml cargado correctamente")


def test_can_get_config(rules_path):
    """✅ Test: Puedo obtener la configuración global"""
    loader = RuleLoader(rules_path)
    loader.load()
    
    config = loader.get_config()
    
    assert config.version == "1.0.0"
    assert config.point_system["currency_name"] == "SecuPoints"
    print(f"✅ Configuración: {config.point_system['currency_name']}")


def test_can_find_critical_rule(rules_path):
    """✅ Test: Puedo encontrar la regla PTS-001 (Critical)"""
    loader = RuleLoader(rules_path)
    loader.load()
    
    rule = loader.get_rule_by_id("PTS-001")
    
    assert rule is not None
    assert rule.rule_id == "PTS-001"
    assert rule.action.points == 100
    print(f"✅ Regla PTS-001 encontrada: {rule.action.points} puntos")


def test_can_find_high_rule(rules_path):
    """✅ Test: Puedo encontrar la regla PTS-002 (High)"""
    loader = RuleLoader(rules_path)
    loader.load()
    
    rule = loader.get_rule_by_id("PTS-002")
    
    assert rule is not None
    assert rule.action.points == 50
    print(f"✅ Regla PTS-002 encontrada: {rule.action.points} puntos")


def test_can_list_point_rules(rules_path):
    """✅ Test: Puedo listar todas las reglas de puntos"""
    loader = RuleLoader(rules_path)
    loader.load()
    
    point_rules = loader.get_rules_by_type("points")
    
    assert len(point_rules) >= 4  # Mínimo PTS-001 a PTS-004
    print(f"✅ Encontradas {len(point_rules)} reglas de puntos")
    
    for rule in point_rules[:3]:
        print(f"   - {rule.rule_id}: {rule.name}")


def test_can_list_badges(rules_path):
    """✅ Test: Puedo listar todos los badges"""
    loader = RuleLoader(rules_path)
    loader.load()
    
    badges = loader.get_all_active_badges()
    
    assert len(badges) >= 5  # Mínimo algunos badges
    print(f"✅ Encontrados {len(badges)} badges")
    
    for badge in badges[:3]:
        print(f"   - {badge.badge_id}: {badge.name}")


def test_can_find_rules_by_event(rules_path):
    """✅ Test: Puedo encontrar reglas por evento"""
    loader = RuleLoader(rules_path)
    loader.load()
    
    rescan_rules = loader.get_rules_by_event("rescan_completed")
    
    assert len(rescan_rules) > 0
    print(f"✅ Encontradas {len(rescan_rules)} reglas para 'rescan_completed'")