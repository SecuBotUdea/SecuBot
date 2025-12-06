"""
time_evaluator.py - Evaluación de comparaciones temporales

Responsabilidades:
- Calcular diferencias de tiempo entre timestamps
- Evaluar comparaciones con umbrales temporales
- Soportar diferentes unidades de tiempo
"""

from datetime import datetime, timedelta
from typing import Any

from dateutil import parser as date_parser

from .operators import ComparisonOperator
from .parsers import TimeUnitConverter
from .resolvers import ReferenceResolver


class TimeEvaluator:
    """Evaluador de comparaciones temporales"""

    def __init__(self, context: dict[str, Any]):
        """
        Args:
            context: Diccionario con entidades disponibles
        """
        self.context = context
        self.resolver = ReferenceResolver(context)

    def evaluate(self, time_expr: str, operator: str, threshold: int, unit: str) -> bool:
        """
        Evalúa una comparación temporal

        Args:
            time_expr: Expresión temporal (ej: "Remediation.action_ts - Alert.first_seen")
            operator: Operador de comparación
            threshold: Valor umbral
            unit: Unidad de tiempo

        Returns:
            True si la condición se cumple

        Examples:
            >>> evaluator = TimeEvaluator(context)
            >>> evaluator.evaluate(
            ...     "Remediation.action_ts - Alert.first_seen",
            ...     "<",
            ...     24,
            ...     "hours"
            ... )
            True
        """
        # Calcular diferencia temporal
        delta = self._calculate_time_delta(time_expr)

        # Convertir threshold a segundos
        threshold_seconds = TimeUnitConverter.to_seconds(threshold, unit)

        # Comparar
        delta_seconds = delta.total_seconds()
        return ComparisonOperator.compare(delta_seconds, operator, threshold_seconds)

    def _calculate_time_delta(self, expr: str) -> timedelta:
        """
        Calcula diferencia temporal entre dos timestamps

        Args:
            expr: Expresión (ej: "timestamp1 - timestamp2")

        Returns:
            Diferencia como timedelta

        Raises:
            ValueError: Si la expresión es inválida
        """
        # Parsear expresión "timestamp1 - timestamp2"
        parts = expr.split('-')

        if len(parts) != 2:
            raise ValueError(f'Invalid time delta expression: {expr}')

        ts1_expr = parts[0].strip()
        ts2_expr = parts[1].strip()

        # Resolver timestamps
        ts1 = self.resolver.resolve(ts1_expr)
        ts2 = self.resolver.resolve(ts2_expr)

        # Convertir a datetime si son necesarios
        ts1 = self._ensure_datetime(ts1)
        ts2 = self._ensure_datetime(ts2)

        # Calcular diferencia
        return ts1 - ts2

    def _ensure_datetime(self, value: Any) -> datetime:
        """
        Asegura que el valor sea un datetime

        Args:
            value: Valor a convertir

        Returns:
            Objeto datetime

        Raises:
            ValueError: Si no se puede convertir
        """
        if isinstance(value, datetime):
            return value

        if isinstance(value, str):
            return date_parser.parse(value)

        raise ValueError(f'Cannot convert {type(value)} to datetime')


class TimeHelper:
    """Helper functions para operaciones con tiempo"""

    @staticmethod
    def parse_timestamp(value: Any) -> datetime:
        """
        Parsea un timestamp a datetime

        Args:
            value: String, datetime, o timestamp

        Returns:
            Objeto datetime
        """
        if isinstance(value, datetime):
            return value

        if isinstance(value, str):
            return date_parser.parse(value)

        raise ValueError(f'Cannot parse timestamp from {type(value)}')

    @staticmethod
    def time_difference(ts1: datetime, ts2: datetime, unit: str = 'seconds') -> float:
        """
        Calcula diferencia entre dos timestamps

        Args:
            ts1: Primer timestamp
            ts2: Segundo timestamp
            unit: Unidad de retorno (seconds, minutes, hours, days)

        Returns:
            Diferencia en la unidad especificada
        """
        delta = ts1 - ts2
        seconds = delta.total_seconds()

        # Normalizar unidad
        unit = unit.lower().rstrip('s')

        if unit == 'second':
            return seconds
        elif unit == 'minute':
            return seconds / 60
        elif unit == 'hour':
            return seconds / 3600
        elif unit == 'day':
            return seconds / 86400
        else:
            raise ValueError(f'Unsupported unit: {unit}')
