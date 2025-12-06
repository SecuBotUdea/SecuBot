from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from .base import BaseModelDB

__all__ = ['Award']


class Award(BaseModelDB):
    """
    Contrato de datos para la entidad Award (solo datos — sin lógica).

    Campos:
      - award_id: PK
      - badge_id: FK → Badge
      - user_id: FK → User
      - team_id: FK → Team
      - timestamp: momento en el que se otorgó el badge
      - evidence_refs: lista de referencias que justifican el award
      - metadata: metadatos adicionales
    """

    award_id: str = Field(..., description='Identificador único del award (PK).')

    badge_id: str = Field(..., description='ID del badge otorgado (FK).')
    user_id: str = Field(..., description='Usuario que recibió el badge (FK).')
    team_id: str = Field(..., description='Equipo asociado al award (FK).')

    timestamp: datetime = Field(..., description='Momento en el que se otorgó el badge.')

    evidence_refs: list[str] = Field(
        default_factory=list, description='Referencias externas que justifican el otorgamiento.'
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict, description='Metadatos adicionales del award.'
    )
