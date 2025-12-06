"""
Rule Loader Module

Carga y gestiona las reglas desde rules.yaml

Usage básico:
    from rules.loader import get_rule_loader

    loader = get_rule_loader()
    rule = loader.get_rule_by_id("PTS-001")
    point_rules = loader.get_rules_by_type("points")

Usage con inicialización custom:
    from rules.loader import init_rule_loader

    init_rule_loader("path/to/custom/rules.yaml")

Usage de sincronización a MongoDB:
    from rules.loader import get_rule_loader, get_all_rules_for_sync

    loader = get_rule_loader()
    rules_dict = get_all_rules_for_sync(loader)
    # Ahora puedes sincronizar rules_dict a MongoDB
"""

from .loader import RuleLoader
from .models import (
    ActionConfig,
    BadgeAwardTrigger,
    BadgeCriteria,
    BadgeCriteriaCondition,
    BadgeRule,
    ExclusionRule,
    PenaltyRule,
    PointRule,
    RulesConfig,
    RulesDocument,
    TriggerConditions,
)
from .singleton import (
    get_rule_loader,
    init_rule_loader,
    is_loader_initialized,
    reset_rule_loader,
)
from .sync import RuleSyncHelper, get_all_rules_for_sync

__all__ = [
    # Main loader
    'RuleLoader',
    'get_rule_loader',
    'init_rule_loader',
    'reset_rule_loader',
    'is_loader_initialized',
    # Sync helpers
    'RuleSyncHelper',
    'get_all_rules_for_sync',
    # Models
    'ActionConfig',
    'BadgeCriteria',
    'BadgeCriteriaCondition',
    'BadgeRule',
    'BadgeAwardTrigger',
    'ExclusionRule',
    'PenaltyRule',
    'PointRule',
    'RulesConfig',
    'RulesDocument',
    'TriggerConditions',
]
