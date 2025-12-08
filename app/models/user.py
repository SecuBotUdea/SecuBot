from __future__ import annotations

import datetime
from typing import Any

from pydantic import EmailStr, Field, field_validator

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

    username: str = Field(
        ..., min_length=3, max_length=50, description='Nombre de usuario único dentro del sistema.'
    )
    display_name: str = Field(..., max_length=100, description='Nombre visible / para mostrar.')
    email: EmailStr = Field(...,  description='Correo electrónico validado.')
    role: str = Field(default="member", description="Rol del usuario (ej. 'admin', 'member').")
    team_id: str | None = Field(None,description='Referencia a equipo (si aplica).')
    metadata: dict[str, Any] = Field(
        default_factory=dict, description='Objeto libre para datos adicionales.'
    )
    # Campos comunes con defaults (evolución controlada)
    is_active: bool = Field(default=True)

    # Validador de roles
    @field_validator('role')
    def validate_role(cls, v):
        valid_roles = ['super_admin', 'admin', 'member', 'viewer', 'auditor']
        if v not in valid_roles:
            raise ValueError(f'Rol debe ser uno de: {valid_roles}')
        return v

    class Config:
        # Configuración importante para MongoDB
        allow_population_by_field_name = True  # Permite cargar por _id
        json_encoders = {
            datetime: lambda v: v.isoformat()  # Serialización para MongoDB
        }
        # Para desarrollo: ignorar campos extra al crear desde MongoDB
        extra = 'ignore'
