"""
operators.py - Operadores de comparación para evaluación de condiciones

Define los operadores soportados y la lógica de comparación.
"""

from typing import Any


class ComparisonOperator:
    """Clase base para operadores de comparación"""

    @staticmethod
    def compare(left: Any, operator: str, right: Any) -> bool:
        """
        Ejecuta la comparación según el operador

        Args:
            left: Valor izquierdo
            operator: Operador (==, !=, <, >, <=, >=, IN, NOT IN)
            right: Valor derecho

        Returns:
            Resultado de la comparación

        Raises:
            ValueError: Si el operador no es soportado
        """
        operator = operator.strip().upper()

        # Manejo de None
        if left is None or right is None:
            return ComparisonOperator._compare_with_none(left, operator, right)

        # Operadores de comparación
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

    @staticmethod
    def _compare_with_none(left: Any, operator: str, right: Any) -> bool:
        """Maneja comparaciones cuando algún valor es None"""
        if operator == '==':
            return left == right
        elif operator == '!=':
            return left != right
        else:
            # Otros operadores retornan False con None
            return False


class LogicalOperator:
    """Operadores lógicos para combinar múltiples condiciones"""

    @staticmethod
    def combine(results: list[bool], operator: str) -> bool:
        """
        Combina resultados con operador lógico

        Args:
            results: Lista de resultados booleanos
            operator: "AND" | "OR"

        Returns:
            Resultado de la combinación

        Raises:
            ValueError: Si el operador no es soportado
        """
        operator = operator.strip().upper()

        if operator == 'AND':
            return all(results)
        elif operator == 'OR':
            return any(results)
        else:
            raise ValueError(f'Unsupported logical operator: {operator}')


# ============================================================================
# CONSTANTES DE OPERADORES
# ============================================================================

COMPARISON_OPERATORS = ['==', '!=', '<=', '>=', '<', '>', 'IN', 'NOT IN']
LOGICAL_OPERATORS = ['AND', 'OR']
TIME_UNITS = ['second', 'minute', 'hour', 'day']
