"""
loader.py - Carga y parsea rules.yaml al inicio de la aplicación

Responsabilidades:
- Cargar rules.yaml desde el filesystem
- Validar estructura contra esquema esperado
- Cachear reglas en memoria para acceso rápido
- Proveer métodos de consulta por tipo de regla

Nota: La sincronización a MongoDB (modelo Rule) será manejada por los servicios.
      Este módulo es puro procesamiento de YAML → objetos Pydantic.
"""

from pathlib import Path
from typing import Any

import yaml

from .models import (
    BadgeRule,
    PenaltyRule,
    PointRule,
    RulesConfig,
    RulesDocument,
)


class RuleLoader:
    """
    Carga y cachea las reglas desde rules.yaml

    Usage:
        loader = RuleLoader("config/rules.yaml")
        loader.load()

        # Consultas
        point_rules = loader.get_rules_by_type("points")
        rule = loader.get_rule_by_id("PTS-001")
    """

    def __init__(self, rules_path: str | Path):
        self.rules_path = Path(rules_path)
        self._rules_doc: RulesDocument | None = None
        self._rules_cache: dict[str, Any] = {}
        self._loaded = False

    def load(self) -> None:
        """Carga y valida rules.yaml"""
        if not self.rules_path.exists():
            raise FileNotFoundError(f'Rules file not found: {self.rules_path}')

        # Leer YAML
        with open(self.rules_path, encoding='utf-8') as f:
            raw_data = yaml.safe_load(f)

        # Validar contra esquema Pydantic
        try:
            self._rules_doc = RulesDocument(**raw_data)
        except Exception as e:
            raise e

        # Construir caché indexado
        self._build_cache()
        self._loaded = True

        print(f'✅ Loaded {len(self._rules_cache)} rules from {self.rules_path}')

    def _build_cache(self) -> None:
        """Construye caché indexado por rule_id y tipo"""
        if not self._rules_doc:
            return

        # Indexar todas las reglas por ID
        all_rules = (
            self._rules_doc.point_rules
            + self._rules_doc.penalty_rules
            + self._rules_doc.exclusion_rules
        )

        for rule in all_rules:
            self._rules_cache[rule.rule_id] = rule

        # Indexar badges por badge_id
        for badge in self._rules_doc.badge_rules:
            self._rules_cache[badge.badge_id] = badge

    def get_rule_by_id(self, rule_id: str) -> Any | None:
        """Obtiene una regla por su ID"""
        self._ensure_loaded()
        return self._rules_cache.get(rule_id)

    def get_rules_by_type(self, rule_type: str) -> list[Any]:
        """
        Obtiene reglas por tipo

        Args:
            rule_type: "points", "penalty", "exclusion", "badge"
        """
        self._ensure_loaded()

        if rule_type == 'points':
            return [r for r in self._rules_doc.point_rules if r.active]
        elif rule_type == 'penalty':
            return [r for r in self._rules_doc.penalty_rules if r.active]
        elif rule_type == 'exclusion':
            return [r for r in self._rules_doc.exclusion_rules if r.active]
        elif rule_type == 'badge':
            return [r for r in self._rules_doc.badge_rules if r.active]
        else:
            return []

    def get_rules_by_event(self, event: str) -> list[PointRule | PenaltyRule]:
        """
        Obtiene reglas que se disparan con un evento específico

        Args:
            event: "rescan_completed", "grace_period_expired", etc.
        """
        self._ensure_loaded()

        matching_rules = []

        # Point rules
        for rule in self._rules_doc.point_rules:
            if rule.active and rule.trigger.event == event:
                matching_rules.append(rule)

        # Penalty rules
        for rule in self._rules_doc.penalty_rules:
            if rule.active and rule.trigger.event == event:
                matching_rules.append(rule)

        return matching_rules

    def get_config(self) -> RulesConfig:
        """Obtiene configuración global"""
        self._ensure_loaded()
        return self._rules_doc.config

    def get_all_active_badges(self) -> list[BadgeRule]:
        """Obtiene todos los badges activos"""
        self._ensure_loaded()
        return [b for b in self._rules_doc.badge_rules if b.active]

    def reload(self) -> None:
        """Recarga las reglas desde el archivo"""
        self._loaded = False
        self._rules_cache.clear()
        self.load()

    def _ensure_loaded(self) -> None:
        """Asegura que las reglas estén cargadas"""
        if not self._loaded:
            raise RuntimeError('Rules not loaded. Call load() first.')

    @property
    def is_loaded(self) -> bool:
        """Verifica si las reglas están cargadas"""
        return self._loaded
