from __future__ import annotations

import datetime
from typing import Any, Optional

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
    team_id: Optional[str] = Field(None, description='Referencia a equipo (si aplica).')
    metadata: dict[str, Any] = Field(
        default_factory=dict, description='Objeto libre para datos adicionales.'
    )
    # Campos comunes con defaults (evolución controlada)
    is_active: bool = Field(default=True)
    email_verified: bool = Field(default=False)
    last_login: Optional[datetime.datetime] = None

    class Config:
        # Configuración importante para MongoDB
        allow_population_by_field_name = True  # Permite cargar por _id
        json_encoders = {
            datetime: lambda v: v.isoformat()  # Serialización para MongoDB
        }
        # Para desarrollo: ignorar campos extra al crear desde MongoDB
        extra = 'ignore'