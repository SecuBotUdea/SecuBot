"""
ConditionEvaluator - Evalúa condiciones complejas definidas en rules.yaml

Responsabilidades:
- Parsear expresiones tipo "Alert.severity == 'CRITICAL'"
- Resolver referencias a propiedades de entidades
- Soportar operadores: ==, !=, <, >, <=, >=, IN, NOT IN
- Comparaciones temporales (diferencias de tiempo)
- Operadores lógicos AND, OR
"""

import re
from datetime import timedelta
from typing import Any

from dateutil import parser as date_parser


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

    # Regex patterns
    COMPARISON_PATTERN = re.compile(
        r'([A-Za-z_][A-Za-z0-9_.]*)\s*(==|!=|<=|>=|<|>|IN|NOT IN)\s*(.+)'
    )
    TIME_COMPARISON_PATTERN = re.compile(
        r'\(([^)]+)\)\s*(==|!=|<=|>=|<|>)\s*(\d+)\s*(hours?|days?|minutes?)'
    )

    def __init__(self, context: dict[str, Any]):
        """
        Args:
            context: Diccionario con entidades disponibles para evaluar
                     Ejemplo: {"Alert": alert_obj, "Remediation": rem_obj}
        """
        self.context = context

    def evaluate(self, condition: str) -> bool:
        """
        Evalúa una condición individual

        Args:
            condition: String con la condición (ej: "Alert.severity == 'CRITICAL'")

        Returns:
            True si la condición se cumple, False caso contrario
        """
        condition = condition.strip()

        # Intentar evaluación de comparación temporal primero
        if '(' in condition and (
            'hours' in condition or 'days' in condition or 'minutes' in condition
        ):
            return self._evaluate_time_comparison(condition)

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
        """
        if not conditions:
            return True

        results = [self.evaluate(cond) for cond in conditions]

        if operator == 'AND':
            return all(results)
        elif operator == 'OR':
            return any(results)
        else:
            raise ValueError(f'Unsupported operator: {operator}')

    def _evaluate_standard_comparison(self, condition: str) -> bool:
        """Evalúa comparaciones estándar"""
        match = self.COMPARISON_PATTERN.match(condition)

        if not match:
            raise ValueError(f'Invalid condition syntax: {condition}')

        left_expr, operator, right_expr = match.groups()

        # Resolver lado izquierdo (variable del contexto)
        left_value = self._resolve_reference(left_expr)

        # Resolver lado derecho (puede ser literal o variable)
        right_value = self._resolve_value(right_expr)

        # Ejecutar comparación
        return self._compare(left_value, operator, right_value)

    def _evaluate_time_comparison(self, condition: str) -> bool:
        """
        Evalúa comparaciones temporales
        Ejemplo: "(Remediation.action_ts - Alert.first_seen) < 24 hours"
        """
        match = self.TIME_COMPARISON_PATTERN.match(condition)

        if not match:
            # Fallback a evaluación estándar
            return self._evaluate_standard_comparison(condition)

        time_expr, operator, threshold_num, time_unit = match.groups()

        # Calcular diferencia temporal
        delta = self._calculate_time_delta(time_expr)

        # Convertir threshold a segundos
        threshold_seconds = self._convert_to_seconds(int(threshold_num), time_unit)

        # Comparar
        delta_seconds = delta.total_seconds()
        return self._compare(delta_seconds, operator, threshold_seconds)

    def _resolve_reference(self, expr: str) -> Any:
        """
        Resuelve referencias a propiedades de entidades
        Ejemplo: "Alert.severity" -> context["Alert"].severity
        """
        parts = expr.split('.')

        if len(parts) < 2:
            raise ValueError(f'Invalid reference: {expr}')

        entity_name = parts[0]

        if entity_name not in self.context:
            raise KeyError(f"Entity '{entity_name}' not found in context")

        obj = self.context[entity_name]

        # Navegar propiedades anidadas
        for part in parts[1:]:
            if obj is None:
                return None

            # Soportar tanto diccionarios como objetos
            if isinstance(obj, dict):
                obj = obj.get(part)
            else:
                obj = getattr(obj, part, None)

        return obj

    def _resolve_value(self, expr: str) -> Any:
        """
        Resuelve el valor del lado derecho de la comparación
        Puede ser: literal, variable, lista
        """
        expr = expr.strip()

        # Lista: ['value1', 'value2']
        if expr.startswith('[') and expr.endswith(']'):
            items = expr[1:-1].split(',')
            return [self._parse_literal(item.strip()) for item in items]

        # Variable del contexto (ej: "current_user")
        if expr in self.context:
            return self.context[expr]

        # Literal
        return self._parse_literal(expr)

    def _parse_literal(self, value: str) -> Any:
        """Parsea un valor literal (string, number, bool)"""
        value = value.strip()

        # String con comillas
        if (value.startswith("'") and value.endswith("'")) or (
            value.startswith('"') and value.endswith('"')
        ):
            return value[1:-1]

        # Boolean
        if value.lower() == 'true':
            return True
        if value.lower() == 'false':
            return False

        # Null/None
        if value.lower() in ('null', 'none'):
            return None

        # Number
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # Default: string sin comillas
        return value

    def _compare(self, left: Any, operator: str, right: Any) -> bool:
        """Ejecuta la comparación según el operador"""
        operator = operator.strip().upper()

        # Manejo de None
        if left is None or right is None:
            if operator == '==':
                return left == right
            elif operator == '!=':
                return left != right
            else:
                return False

        # Operadores estándar
        if operator == '==':
            return left == right
        elif operator == '!=':
            return left != right
        elif operator == '<':
            return left < right
        elif operator == '>':
            return left > right
        elif operator == '<=':
            return left <= right
        elif operator == '>=':
            return left >= right
        elif operator == 'IN':
            return left in right
        elif operator == 'NOT IN':
            return left not in right
        else:
            raise ValueError(f'Unsupported operator: {operator}')

    def _calculate_time_delta(self, expr: str) -> timedelta:
        """
        Calcula diferencia temporal entre dos timestamps
        Ejemplo: "Remediation.action_ts - Alert.first_seen"
        """
        # Parsear expresión "timestamp1 - timestamp2"
        parts = expr.split('-')

        if len(parts) != 2:
            raise ValueError(f'Invalid time delta expression: {expr}')

        ts1_expr = parts[0].strip()
        ts2_expr = parts[1].strip()

        # Resolver timestamps
        ts1 = self._resolve_reference(ts1_expr)
        ts2 = self._resolve_reference(ts2_expr)

        # Convertir a datetime si son strings
        if isinstance(ts1, str):
            ts1 = date_parser.parse(ts1)
        if isinstance(ts2, str):
            ts2 = date_parser.parse(ts2)

        # Calcular diferencia
        return ts1 - ts2

    def _convert_to_seconds(self, value: int, unit: str) -> float:
        """Convierte tiempo a segundos"""
        unit = unit.lower().rstrip('s')  # Remove trailing 's'

        if unit == 'second':
            return value
        elif unit == 'minute':
            return value * 60
        elif unit == 'hour':
            return value * 3600
        elif unit == 'day':
            return value * 86400
        else:
            raise ValueError(f'Unsupported time unit: {unit}')


# ============================================================================
# HELPERS PARA VALIDACIÓN DE EXISTENCIA
# ============================================================================


def check_entity_exists(context: dict[str, Any], entity_name: str) -> bool:
    """
    Verifica si una entidad existe en el contexto

    Usage:
        if check_entity_exists(context, "RescanResult"):
            # RescanResult está disponible
    """
    return entity_name in context and context[entity_name] is not None


def check_condition_not_exists(condition: str) -> bool:
    """
    Verifica si una condición es del tipo "NOT EXISTS"

    Usage:
        if check_condition_not_exists("RescanResult NOT EXISTS"):
            # Esta es una condición de no existencia
    """
    return 'NOT EXISTS' in condition.upper()
