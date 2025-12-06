"""
parsers.py - Parsers para expresiones y valores literales

Responsabilidades:
- Parsear valores literales (strings, números, booleanos, listas)
- Convertir unidades de tiempo
- Parsear referencias a entidades
"""

from typing import Any


class LiteralParser:
    """Parser de valores literales"""

    @staticmethod
    def parse(value: str) -> Any:
        """
        Parsea un valor literal (string, number, bool, None)

        Args:
            value: String con el valor

        Returns:
            Valor parseado al tipo correcto

        Examples:
            >>> LiteralParser.parse("'hello'")
            'hello'
            >>> LiteralParser.parse("123")
            123
            >>> LiteralParser.parse("true")
            True
        """
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


class ListParser:
    """Parser de listas"""

    @staticmethod
    def parse(expr: str) -> list[Any]:
        """
        Parsea una expresión de lista

        Args:
            expr: String con la lista (ej: "['value1', 'value2']")

        Returns:
            Lista de valores parseados

        Examples:
            >>> ListParser.parse("['A', 'B', 'C']")
            ['A', 'B', 'C']
            >>> ListParser.parse("[1, 2, 3]")
            [1, 2, 3]
        """
        expr = expr.strip()

        if not (expr.startswith('[') and expr.endswith(']')):
            raise ValueError(f'Invalid list syntax: {expr}')

        # Remover corchetes
        content = expr[1:-1].strip()

        if not content:
            return []

        # Split por coma
        items = content.split(',')

        # Parsear cada item
        return [LiteralParser.parse(item.strip()) for item in items]


class TimeUnitConverter:
    """Conversor de unidades de tiempo"""

    # Conversión a segundos
    UNIT_TO_SECONDS = {
        'second': 1,
        'minute': 60,
        'hour': 3600,
        'day': 86400,
    }

    @staticmethod
    def to_seconds(value: int, unit: str) -> float:
        """
        Convierte tiempo a segundos

        Args:
            value: Cantidad de unidades
            unit: Unidad de tiempo (second, minute, hour, day)

        Returns:
            Valor en segundos

        Raises:
            ValueError: Si la unidad no es soportada

        Examples:
            >>> TimeUnitConverter.to_seconds(2, 'hours')
            7200
            >>> TimeUnitConverter.to_seconds(1, 'day')
            86400
        """
        # Normalizar unidad (remover 's' plural)
        unit = unit.lower().rstrip('s')

        if unit not in TimeUnitConverter.UNIT_TO_SECONDS:
            raise ValueError(f'Unsupported time unit: {unit}')

        return value * TimeUnitConverter.UNIT_TO_SECONDS[unit]


class ReferenceParser:
    """Parser de referencias a propiedades de entidades"""

    @staticmethod
    def parse(expr: str) -> tuple[str, list[str]]:
        """
        Parsea una referencia a entidad

        Args:
            expr: Expresión (ej: "Alert.severity")

        Returns:
            Tupla (entity_name, property_path)

        Raises:
            ValueError: Si la sintaxis es inválida

        Examples:
            >>> ReferenceParser.parse("Alert.severity")
            ('Alert', ['severity'])
            >>> ReferenceParser.parse("User.profile.email")
            ('User', ['profile', 'email'])
        """
        parts = expr.split('.')

        if len(parts) < 2:
            raise ValueError(f'Invalid reference syntax: {expr}')

        entity_name = parts[0]
        property_path = parts[1:]

        return entity_name, property_path
