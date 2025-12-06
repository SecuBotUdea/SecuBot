"""
resolvers.py - Resolvedores de valores y referencias a entidades

Responsabilidades:
- Resolver referencias a propiedades de entidades desde el contexto
- Resolver valores del lado derecho de comparaciones
- Navegar propiedades anidadas
"""

from typing import Any

from .parsers import ListParser, LiteralParser, ReferenceParser


class ReferenceResolver:
    """Resuelve referencias a propiedades de entidades desde el contexto"""

    def __init__(self, context: dict[str, Any]):
        """
        Args:
            context: Diccionario con entidades disponibles
        """
        self.context = context

    def resolve(self, expr: str) -> Any:
        """
        Resuelve una referencia a propiedad de entidad

        Args:
            expr: Expresión (ej: "Alert.severity")

        Returns:
            Valor de la propiedad

        Raises:
            ValueError: Si la sintaxis es inválida
            KeyError: Si la entidad no existe en el contexto

        Examples:
            >>> resolver = ReferenceResolver({"Alert": alert_obj})
            >>> resolver.resolve("Alert.severity")
            'CRITICAL'
        """
        entity_name, property_path = ReferenceParser.parse(expr)

        # Verificar que la entidad existe
        if entity_name not in self.context:
            raise KeyError(f"Entity '{entity_name}' not found in context")

        obj = self.context[entity_name]

        # Navegar propiedades anidadas
        return self._navigate_properties(obj, property_path)

    def _navigate_properties(self, obj: Any, path: list[str]) -> Any:
        """
        Navega por propiedades anidadas

        Args:
            obj: Objeto inicial
            path: Lista de propiedades a navegar

        Returns:
            Valor final de la navegación
        """
        current = obj

        for prop in path:
            if current is None:
                return None

            # Soportar tanto diccionarios como objetos
            if isinstance(current, dict):
                current = current.get(prop)
            else:
                current = getattr(current, prop, None)

        return current


class ValueResolver:
    """Resuelve valores del lado derecho de comparaciones"""

    def __init__(self, context: dict[str, Any]):
        """
        Args:
            context: Diccionario con entidades disponibles
        """
        self.context = context

    def resolve(self, expr: str) -> Any:
        """
        Resuelve el valor del lado derecho de la comparación

        Puede ser:
        - Lista: ['value1', 'value2']
        - Variable del contexto: current_user
        - Literal: 'string', 123, true

        Args:
            expr: Expresión a resolver

        Returns:
            Valor resuelto

        Examples:
            >>> resolver = ValueResolver({"max_value": 100})
            >>> resolver.resolve("max_value")
            100
            >>> resolver.resolve("'CRITICAL'")
            'CRITICAL'
            >>> resolver.resolve("['A', 'B', 'C']")
            ['A', 'B', 'C']
        """
        expr = expr.strip()

        # Lista: ['value1', 'value2']
        if expr.startswith('[') and expr.endswith(']'):
            return ListParser.parse(expr)

        # Variable del contexto (ej: "current_user")
        if expr in self.context:
            return self.context[expr]

        # Literal
        return LiteralParser.parse(expr)


class ContextChecker:
    """Verifica existencia de entidades en el contexto"""

    def __init__(self, context: dict[str, Any]):
        """
        Args:
            context: Diccionario con entidades disponibles
        """
        self.context = context

    def entity_exists(self, entity_name: str) -> bool:
        """
        Verifica si una entidad existe en el contexto

        Args:
            entity_name: Nombre de la entidad

        Returns:
            True si la entidad existe y no es None

        Examples:
            >>> checker = ContextChecker({"Alert": alert_obj})
            >>> checker.entity_exists("Alert")
            True
            >>> checker.entity_exists("RescanResult")
            False
        """
        return entity_name in self.context and self.context[entity_name] is not None

    def has_property(self, entity_name: str, property_path: str) -> bool:
        """
        Verifica si una entidad tiene una propiedad específica

        Args:
            entity_name: Nombre de la entidad
            property_path: Path de la propiedad (ej: "profile.email")

        Returns:
            True si la propiedad existe
        """
        if not self.entity_exists(entity_name):
            return False

        obj = self.context[entity_name]
        parts = property_path.split('.')

        resolver = ReferenceResolver(self.context)
        try:
            value = resolver._navigate_properties(obj, parts)
            return value is not None
        except (AttributeError, KeyError):
            return False
