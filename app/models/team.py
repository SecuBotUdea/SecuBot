from __future__ import annotations

from typing import Any

from pydantic import Field

from .base import BaseModelDB

__all__ = ['Team']


class Team(BaseModelDB):
    """
    Contrato de datos para la entidad Team.

    Campos:
      - team_id: PK (string)
      - name: nombre del equipo
      - members: lista de user_id (strings)
      - metadata: objeto libre
      - created_at / updated_at heredados
    """

    team_id: str = Field(..., description='Primary business identifier (PK) del equipo.')
    name: str = Field(..., description='Nombre del equipo.')
    members: list[str] = Field(
        default_factory=list, description='Lista de IDs de usuarios pertenecientes.'
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description='Datos adicionales.')
