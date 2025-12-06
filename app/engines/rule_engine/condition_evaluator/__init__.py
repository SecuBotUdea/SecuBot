"""
Condition Evaluator Module

Evalúa condiciones complejas definidas en rules.yaml

Usage básico:
    from rules.evaluator import ConditionEvaluator

    context = {
        "Alert": alert_obj,
        "Remediation": remediation_obj,
    }

    evaluator = ConditionEvaluator(context)

    # Evaluación simple
    result = evaluator.evaluate("Alert.severity == 'CRITICAL'")

    # Evaluación múltiple
    conditions = [
        "Alert.severity == 'CRITICAL'",
        "Alert.status == 'OPEN'"
    ]
    result = evaluator.evaluate_all(conditions, operator="AND")

Comparaciones temporales:
    result = evaluator.evaluate(
        "(Remediation.action_ts - Alert.first_seen) < 24 hours"
    )

Verificación de existencia:
    from rules.evaluator import check_entity_exists

    if check_entity_exists(context, "RescanResult"):
        # RescanResult está disponible
        pass

Operadores soportados:
    - Comparación: ==, !=, <, >, <=, >=, IN, NOT IN
    - Lógicos: AND, OR
    - Temporal: hours, days, minutes, seconds
"""

from .evaluator import (
    ConditionEvaluator,
    check_condition_not_exists,
    check_entity_exists,
)
from .matchers import ComparisonMatch, PatternMatcher, TimeComparisonMatch
from .operators import ComparisonOperator, LogicalOperator
from .parsers import (
    ListParser,
    LiteralParser,
    ReferenceParser,
    TimeUnitConverter,
)
from .resolvers import ContextChecker, ReferenceResolver, ValueResolver
from .time_evaluator import TimeEvaluator, TimeHelper

__all__ = [
    # Main evaluator
    'ConditionEvaluator',
    # Helper functions
    'check_entity_exists',
    'check_condition_not_exists',
    # Pattern matching
    'PatternMatcher',
    'ComparisonMatch',
    'TimeComparisonMatch',
    # Operators
    'ComparisonOperator',
    'LogicalOperator',
    # Parsers
    'LiteralParser',
    'ListParser',
    'ReferenceParser',
    'TimeUnitConverter',
    # Resolvers
    'ReferenceResolver',
    'ValueResolver',
    'ContextChecker',
    # Time evaluation
    'TimeEvaluator',
    'TimeHelper',
]
