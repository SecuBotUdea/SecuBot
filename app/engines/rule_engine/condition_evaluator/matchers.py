"""
matchers.py - Patrones regex y matchers para expresiones

Define los patrones regex para identificar tipos de condiciones.
"""

import re
from dataclasses import dataclass


@dataclass
class ComparisonMatch:
    """Resultado de match de comparación estándar"""

    left_expr: str
    operator: str
    right_expr: str


@dataclass
class TimeComparisonMatch:
    """Resultado de match de comparación temporal"""

    time_expr: str
    operator: str
    threshold: int
    unit: str


class PatternMatcher:
    """Matchers basados en regex para diferentes tipos de condiciones"""

    # Regex patterns
    COMPARISON_PATTERN = re.compile(
        r'([A-Za-z_][A-Za-z0-9_.]*)\s*(==|!=|<=|>=|<|>|IN|NOT IN)\s*(.+)'
    )

    TIME_COMPARISON_PATTERN = re.compile(
        r'\(([^)]+)\)\s*(==|!=|<=|>=|<|>)\s*(\d+)\s*(hours?|days?|minutes?|seconds?)'
    )

    NOT_EXISTS_PATTERN = re.compile(r'(\w+)\s+NOT\s+EXISTS', re.IGNORECASE)

    @classmethod
    def match_comparison(cls, condition: str) -> ComparisonMatch | None:
        """
        Intenta hacer match con una comparación estándar

        Args:
            condition: Condición a evaluar

        Returns:
            ComparisonMatch si hace match, None en caso contrario

        Examples:
            >>> match = PatternMatcher.match_comparison("Alert.severity == 'CRITICAL'")
            >>> match.left_expr
            'Alert.severity'
            >>> match.operator
            '=='
            >>> match.right_expr
            "'CRITICAL'"
        """
        match = cls.COMPARISON_PATTERN.match(condition)

        if not match:
            return None

        left_expr, operator, right_expr = match.groups()

        return ComparisonMatch(
            left_expr=left_expr.strip(),
            operator=operator.strip(),
            right_expr=right_expr.strip(),
        )

    @classmethod
    def match_time_comparison(cls, condition: str) -> TimeComparisonMatch | None:
        """
        Intenta hacer match con una comparación temporal

        Args:
            condition: Condición a evaluar

        Returns:
            TimeComparisonMatch si hace match, None en caso contrario

        Examples:
            >>> match = PatternMatcher.match_time_comparison(
            ...     "(Remediation.action_ts - Alert.first_seen) < 24 hours"
            ... )
            >>> match.time_expr
            'Remediation.action_ts - Alert.first_seen'
            >>> match.threshold
            24
            >>> match.unit
            'hours'
        """
        match = cls.TIME_COMPARISON_PATTERN.match(condition)

        if not match:
            return None

        time_expr, operator, threshold_str, unit = match.groups()

        return TimeComparisonMatch(
            time_expr=time_expr.strip(),
            operator=operator.strip(),
            threshold=int(threshold_str),
            unit=unit.strip(),
        )

    @classmethod
    def match_not_exists(cls, condition: str) -> str | None:
        """
        Intenta hacer match con una condición NOT EXISTS

        Args:
            condition: Condición a evaluar

        Returns:
            Nombre de la entidad si hace match, None en caso contrario

        Examples:
            >>> PatternMatcher.match_not_exists("RescanResult NOT EXISTS")
            'RescanResult'
        """
        match = cls.NOT_EXISTS_PATTERN.match(condition)

        if not match:
            return None

        return match.group(1)

    @classmethod
    def is_time_comparison(cls, condition: str) -> bool:
        """
        Verifica si una condición es una comparación temporal

        Args:
            condition: Condición a verificar

        Returns:
            True si es comparación temporal
        """
        return '(' in condition and any(
            unit in condition.lower() for unit in ['hours', 'days', 'minutes', 'seconds']
        )

    @classmethod
    def is_not_exists(cls, condition: str) -> bool:
        """
        Verifica si una condición es del tipo NOT EXISTS

        Args:
            condition: Condición a verificar

        Returns:
            True si es condición NOT EXISTS
        """
        return 'NOT EXISTS' in condition.upper()
