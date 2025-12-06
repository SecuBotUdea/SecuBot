"""
evaluator.py - Evaluador principal de condiciones

Responsabilidades:
- Evalúa condiciones complejas definidas en rules.yaml
- Coordina evaluadores especializados
- Soporta operadores lógicos AND, OR
"""

from typing import Any

from .matchers import PatternMatcher
from .operators import ComparisonOperator, LogicalOperator
from .resolvers import ContextChecker, ReferenceResolver, ValueResolver
from .time_evaluator import TimeEvaluator


class ConditionEvaluator:
    """
    Evalúa condiciones definidas en reglas

    Usage:
        context = {
            "Alert": alert_obj,
            "Remediation": remediation_obj,
            "RescanResult": rescan_obj,
            "current_time": datetime.now()
        }

        evaluator = ConditionEvaluator(context)
        result = evaluator.evaluate("Alert.severity == 'CRITICAL'")
    """

    def __init__(self, context: dict[str, Any]):
        """
        Args:
            context: Diccionario con entidades disponibles para evaluar
                     Ejemplo: {"Alert": alert_obj, "Remediation": rem_obj}
        """
        self.context = context
        self.reference_resolver = ReferenceResolver(context)
        self.value_resolver = ValueResolver(context)
        self.time_evaluator = TimeEvaluator(context)
        self.context_checker = ContextChecker(context)

    def evaluate(self, condition: str) -> bool:
        """
        Evalúa una condición individual

        Args:
            condition: String con la condición (ej: "Alert.severity == 'CRITICAL'")

        Returns:
            True si la condición se cumple, False caso contrario

        Raises:
            ValueError: Si la sintaxis de la condición es inválida
            KeyError: Si se referencia una entidad que no existe
        """
        condition = condition.strip()

        # Verificar condiciones NOT EXISTS
        if PatternMatcher.is_not_exists(condition):
            return self._evaluate_not_exists(condition)

        # Intentar evaluación de comparación temporal
        if PatternMatcher.is_time_comparison(condition):
            time_match = PatternMatcher.match_time_comparison(condition)
            if time_match:
                return self.time_evaluator.evaluate(
                    time_match.time_expr,
                    time_match.operator,
                    time_match.threshold,
                    time_match.unit,
                )

        # Evaluación de comparación estándar
        return self._evaluate_standard_comparison(condition)

    def evaluate_all(self, conditions: list[str], operator: str = 'AND') -> bool:
        """
        Evalúa múltiples condiciones con operador lógico

        Args:
            conditions: Lista de condiciones
            operator: "AND" | "OR"

        Returns:
            True si todas/alguna condición se cumple según el operador

        Raises:
            ValueError: Si el operador no es soportado
        """
        if not conditions:
            return True

        results = [self.evaluate(cond) for cond in conditions]
        return LogicalOperator.combine(results, operator)

    def _evaluate_standard_comparison(self, condition: str) -> bool:
        """
        Evalúa comparaciones estándar

        Args:
            condition: Condición a evaluar

        Returns:
            Resultado de la evaluación

        Raises:
            ValueError: Si la sintaxis es inválida
        """
        match = PatternMatcher.match_comparison(condition)

        if not match:
            raise ValueError(f'Invalid condition syntax: {condition}')

        # Resolver lado izquierdo (variable del contexto)
        left_value = self.reference_resolver.resolve(match.left_expr)

        # Resolver lado derecho (puede ser literal o variable)
        right_value = self.value_resolver.resolve(match.right_expr)

        # Ejecutar comparación
        return ComparisonOperator.compare(left_value, match.operator, right_value)

    def _evaluate_not_exists(self, condition: str) -> bool:
        """
        Evalúa condiciones NOT EXISTS

        Args:
            condition: Condición (ej: "RescanResult NOT EXISTS")

        Returns:
            True si la entidad NO existe
        """
        entity_name = PatternMatcher.match_not_exists(condition)

        if not entity_name:
            raise ValueError(f'Invalid NOT EXISTS condition: {condition}')

        # Retorna True si la entidad NO existe
        return not self.context_checker.entity_exists(entity_name)


# ============================================================================
# HELPERS PÚBLICOS
# ============================================================================


def check_entity_exists(context: dict[str, Any], entity_name: str) -> bool:
    """
    Verifica si una entidad existe en el contexto

    Args:
        context: Contexto de evaluación
        entity_name: Nombre de la entidad

    Returns:
        True si la entidad existe y no es None

    Usage:
        if check_entity_exists(context, "RescanResult"):
            # RescanResult está disponible
    """
    checker = ContextChecker(context)
    return checker.entity_exists(entity_name)


def check_condition_not_exists(condition: str) -> bool:
    """
    Verifica si una condición es del tipo "NOT EXISTS"

    Args:
        condition: Condición a verificar

    Returns:
        True si es una condición NOT EXISTS

    Usage:
        if check_condition_not_exists("RescanResult NOT EXISTS"):
            # Esta es una condición de no existencia
    """
    return PatternMatcher.is_not_exists(condition)
