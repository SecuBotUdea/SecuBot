"""
sync.py - Preparación de reglas para sincronización a MongoDB

Este módulo proporciona funcionalidad para convertir las reglas
cargadas desde rules.yaml al formato necesario para el modelo Rule de MongoDB.
"""

from typing import Any

from .loader import RuleLoader


class RuleSyncHelper:
    """
    Helper para preparar reglas para sincronización a MongoDB

    Este helper convierte las reglas Pydantic al formato dict
    que espera el modelo Rule (app.models.rule.Rule)
    """

    def __init__(self, loader: RuleLoader):
        self.loader = loader

    def get_all_rules_for_sync(self) -> list[dict[str, Any]]:
        """
        Retorna todas las reglas en formato dict para sincronización a MongoDB

        Este método será usado por el servicio de sincronización.
        Retorna las reglas con el formato del modelo Rule (app.models.rule.Rule)

        Returns:
            Lista de dicts con estructura:
            {
                "rule_id": str,
                "name": str,
                "type": str,
                "definition": dict,  # Definición completa de la regla
                "version": int,
                "active": bool,
                "created_by": str
            }
        """
        if not self.loader.is_loaded:
            raise RuntimeError('RuleLoader must be loaded before syncing')

        rules_for_sync = []

        # Point rules
        for rule in self.loader._rules_doc.point_rules:
            rules_for_sync.append(self._convert_point_rule_to_sync_format(rule))

        # Penalty rules
        for rule in self.loader._rules_doc.penalty_rules:
            rules_for_sync.append(self._convert_penalty_rule_to_sync_format(rule))

        # Exclusion rules
        for rule in self.loader._rules_doc.exclusion_rules:
            rules_for_sync.append(self._convert_exclusion_rule_to_sync_format(rule))

        # Badge rules
        for badge in self.loader._rules_doc.badge_rules:
            rules_for_sync.append(self._convert_badge_rule_to_sync_format(badge))

        return rules_for_sync

    def _convert_point_rule_to_sync_format(self, rule) -> dict[str, Any]:
        """Convierte PointRule a formato de sincronización"""
        return {
            'rule_id': rule.rule_id,
            'name': rule.name,
            'type': rule.type,
            'definition': rule.dict(exclude={'rule_id', 'name', 'type', 'active', 'version'}),
            'version': rule.version,
            'active': rule.active,
            'created_by': 'rules.yaml',
        }

    def _convert_penalty_rule_to_sync_format(self, rule) -> dict[str, Any]:
        """Convierte PenaltyRule a formato de sincronización"""
        return {
            'rule_id': rule.rule_id,
            'name': rule.name,
            'type': rule.type,
            'definition': rule.dict(exclude={'rule_id', 'name', 'type', 'active', 'version'}),
            'version': rule.version,
            'active': rule.active,
            'created_by': 'rules.yaml',
        }

    def _convert_exclusion_rule_to_sync_format(self, rule) -> dict[str, Any]:
        """Convierte ExclusionRule a formato de sincronización"""
        return {
            'rule_id': rule.rule_id,
            'name': rule.name,
            'type': rule.type,
            'definition': rule.dict(exclude={'rule_id', 'name', 'type', 'active', 'version'}),
            'version': rule.version,
            'active': rule.active,
            'created_by': 'rules.yaml',
        }

    def _convert_badge_rule_to_sync_format(self, badge) -> dict[str, Any]:
        """Convierte BadgeRule a formato de sincronización"""
        return {
            'rule_id': badge.badge_id,
            'name': badge.name,
            'type': 'badge',
            'definition': badge.dict(exclude={'badge_id', 'name', 'active', 'version'}),
            'version': badge.version,
            'active': badge.active,
            'created_by': 'rules.yaml',
        }

    def get_rules_for_sync_by_type(self, rule_type: str) -> list[dict[str, Any]]:
        """
        Retorna reglas de un tipo específico en formato de sincronización

        Args:
            rule_type: "points", "penalty", "exclusion", "badge"

        Returns:
            Lista de dicts en formato de sincronización
        """
        all_rules = self.get_all_rules_for_sync()
        return [r for r in all_rules if r['type'] == rule_type]

    def get_rules_for_sync_by_ids(self, rule_ids: list[str]) -> list[dict[str, Any]]:
        """
        Retorna reglas específicas por sus IDs en formato de sincronización

        Args:
            rule_ids: Lista de IDs de reglas a obtener

        Returns:
            Lista de dicts en formato de sincronización
        """
        all_rules = self.get_all_rules_for_sync()
        return [r for r in all_rules if r['rule_id'] in rule_ids]


# ============================================================================
# FUNCIÓN HELPER PARA BACKWARD COMPATIBILITY
# ============================================================================


def get_all_rules_for_sync(loader: RuleLoader) -> list[dict[str, Any]]:
    """
    Helper function para mantener compatibilidad con código existente

    Esta función permite usar:
        from rules.loader import get_all_rules_for_sync
        rules = get_all_rules_for_sync(loader)

    En lugar de:
        helper = RuleSyncHelper(loader)
        rules = helper.get_all_rules_for_sync()

    Args:
        loader: Instancia de RuleLoader cargada

    Returns:
        Lista de reglas en formato de sincronización
    """
    helper = RuleSyncHelper(loader)
    return helper.get_all_rules_for_sync()
