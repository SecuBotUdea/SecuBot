"""
Rule Engine Package

Exports principales del motor de reglas de gamificación.
"""

from app.engines.rule_engine.engine import RuleEngine, process_remediation_verified
from app.engines.rule_engine.rule_loader import RuleLoader, get_rule_loader, init_rule_loader
from app.engines.rule_engine.condition_evaluator import ConditionEvaluator
from app.engines.rule_engine.action_executor import ActionExecutor
from app.engines.rule_engine.point_calculator import PointCalculator
from app.engines.rule_engine.badge_evaluator import BadgeEvaluator

__all__ = [
    # Core engine
    "RuleEngine",
    "process_remediation_verified",
    
    # Rule loader
    "RuleLoader",
    "get_rule_loader",
    "init_rule_loader",
    
    # Components
    "ConditionEvaluator",
    "ActionExecutor",
    "PointCalculator",
    "BadgeEvaluator",
]