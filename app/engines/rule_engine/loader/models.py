"""
models.py - Modelos Pydantic para validación de rules.yaml

Define la estructura de datos para:
- Reglas de puntos (PTS-XXX)
- Reglas de penalización (PEN-XXX)
- Reglas de exclusión (EXC-XXX)
- Reglas de badges (BDG-XXX)
- Configuración global
"""

from typing import Any

from pydantic import BaseModel, Field

# ============================================================================
# MODELOS BASE Y COMUNES
# ============================================================================


class TriggerConditions(BaseModel):
    """Condiciones dentro de un trigger"""

    event: str
    conditions: list[str] = Field(default_factory=list)


class ActionConfig(BaseModel):
    """Configuración de acción a ejecutar"""

    points: int | None = None
    target: str = 'individual'  # individual | team | both
    recipient: str | None = None
    reason: str
    evidence: list[str] = Field(default_factory=list)
    penalty_reason: str | None = None
    original_alert_status: str | None = None

    # Side effects
    block_gamification: bool | None = None
    block_point_award: bool | None = None
    allow_badge_progress: bool | None = None
    log_exclusion: bool | None = None


# ============================================================================
# REGLAS DE PUNTOS Y PENALIZACIONES
# ============================================================================


class PointRule(BaseModel):
    """Regla de puntos (PTS-XXX)"""

    rule_id: str
    name: str
    type: str
    active: bool
    version: int
    trigger: TriggerConditions
    action: ActionConfig
    metadata: dict[str, Any] | None = Field(default_factory=dict)


class PenaltyRule(BaseModel):
    """Regla de penalización (PEN-XXX)"""

    rule_id: str
    name: str
    type: str
    active: bool
    version: int
    trigger: TriggerConditions
    action: ActionConfig
    side_effects: list[dict[str, Any]] | None = Field(default_factory=list)


class ExclusionRule(BaseModel):
    """Regla de exclusión (EXC-XXX)"""

    rule_id: str
    name: str
    type: str
    active: bool
    version: int
    conditions: list[str]
    action: ActionConfig


# ============================================================================
# MODELOS DE BADGES
# ============================================================================


class BadgeCriteriaCondition(BaseModel):
    """Condición para badge (count, streak, distinct_count, sum)"""

    entity: str
    filters: list[str] = Field(default_factory=list)
    operator: str | None = None
    threshold: int | None = None
    field: str | None = None  # Para sum y distinct_count
    consecutive_days: int | None = None  # Para streak
    min_per_day: int | None = None  # Para streak


class BadgeCriteria(BaseModel):
    """Criterios para otorgar badge"""

    type: str  # individual | team
    conditions: list[dict[str, BadgeCriteriaCondition]]


class BadgeAwardTrigger(BaseModel):
    """Configuración de cuándo evaluar badge"""

    event: str
    immediate: bool | None = None
    check_frequency: str | None = None


class BadgeRule(BaseModel):
    """Regla de badge (BDG-XXX)"""

    badge_id: str
    name: str
    description: str
    category: str
    icon_url: str
    active: bool
    version: int
    criteria: BadgeCriteria
    award_trigger: BadgeAwardTrigger


# ============================================================================
# CONFIGURACIÓN GLOBAL
# ============================================================================


class RulesConfig(BaseModel):
    """Configuración global del sistema"""

    version: str
    point_system: dict[str, Any]
    verification: dict[str, int]
    quality_filter: dict[str, Any]


# ============================================================================
# DOCUMENTO COMPLETO
# ============================================================================


class RulesDocument(BaseModel):
    """Documento completo de rules.yaml"""

    config: RulesConfig
    point_rules: list[PointRule] = Field(default_factory=list)
    penalty_rules: list[PenaltyRule] = Field(default_factory=list)
    exclusion_rules: list[ExclusionRule] = Field(default_factory=list)
    badge_rules: list[BadgeRule] = Field(default_factory=list)
    # team_missions: ignoramos por ahora
    # regression_rules: las manejaremos en el servicio
    # notification_rules: las manejaremos en el servicio
