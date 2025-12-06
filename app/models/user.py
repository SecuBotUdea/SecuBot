from __future__ import annotations

from typing import Any

from pydantic import EmailStr, Field

from .base import BaseModelDB

__all__ = ['User']


class User(BaseModelDB):
    """
    Contrato de datos para la entidad User.

    Campos:
      - user_id: PK (identificador de negocio, string)
      - username
      - display_name
      - email (validado)
      - role
      - team_id: FK (opcional)
      - metadata: objeto libre (dict)
      - created_at / updated_at (heredados de BaseModelDB)
    """

    user_id: str = Field(..., description='Primary business identifier (PK).')
    username: str = Field(
        ..., min_length=3, description='Nombre de usuario único dentro del sistema.'
    )
    display_name: str = Field(..., description='Nombre visible / para mostrar.')
    email: EmailStr = Field(..., description='Correo electrónico validado.')
    role: str = Field(..., description="Rol del usuario (ej. 'admin', 'member').")
    team_id: str | None = Field(None, description='ID del equipo (FK), si aplica.')
    metadata: dict[str, Any] = Field(
        default_factory=dict, description='Objeto libre para datos adicionales.'
    )
