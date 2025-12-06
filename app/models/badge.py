from __future__ import annotations

from typing import Any

from pydantic import Field

from .base import BaseModelDB

__all__ = ['Badge']


class Badge(BaseModelDB):
    """
    Contrato de datos para la entidad Badge (solo datos — sin lógica).

    Campos:
      - badge_id: PK
      - name: nombre del badge
      - description: descripción corta
      - criteria_ref: referencia a la lógica/criterios (objeto)
      - icon_url: URL del ícono del badge
      - category: agrupación (ej. mastery, progression, teamwork)
      - active: si se puede otorgar actualmente
    """

    badge_id: str = Field(..., description='Identificador único del badge (PK).')
    name: str = Field(..., description='Nombre del badge.')
    description: str = Field(..., description='Descripción del badge.')

    criteria_ref: dict[str, Any] = Field(
        default_factory=dict, description='Referencia o definición de los criterios para otorgarlo.'
    )

    icon_url: str = Field(..., description='URL del ícono representativo del badge.')
    category: str = Field(..., description="Categoría del badge (ej. 'team', 'skill', etc.).")

    active: bool = Field(True, description='Indica si el badge está disponible para ser otorgado.')
