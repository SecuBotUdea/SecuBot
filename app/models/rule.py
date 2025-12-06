from __future__ import annotations

from typing import Any

from pydantic import Field

from .base import BaseModelDB

__all__ = ['Rule']


class Rule(BaseModelDB):
    """
    Contrato de datos para la entidad Rule (solo datos — sin lógica).

    Campos:
      - rule_id: PK
      - name: nombre descriptivo de la regla
      - type: categoría (ej. scoring, mission_trigger, quality_gate, etc.)
      - definition: objeto con la definición completa (condiciones, acciones, etc.)
      - version: versión incremental de la regla
      - active: indicador de si está habilitada
      - created_by: usuario/servicio que creó la regla
      - created_at: heredado o sobrescrito (del BaseModelDB)
    """

    rule_id: str = Field(..., description='Identificador único de la regla (PK).')
    name: str = Field(..., description='Nombre de la regla.')
    type: str = Field(..., description='Categoría o tipo de la regla.')

    definition: dict[str, Any] = Field(
        default_factory=dict,
        description='Definición completa de la regla (condiciones, acciones, contexto).',
    )

    version: int = Field(1, description='Versión incremental de la regla.')

    active: bool = Field(True, description='Indica si la regla está activa.')

    created_by: str = Field(..., description='Entidad o usuario que creó la regla.')
