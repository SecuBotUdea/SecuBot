# models/log.py
from __future__ import annotations

from pydantic import Field

from .base import BaseModelDB

__all__ = ['AccessLog']

class AccessLog(BaseModelDB):
    """
    Modelo para logs de acceso.
    """
    user_id: str = Field(..., description="ID del usuario")
    action: str = Field(..., description="Acción realizada")
    ip_address: str = Field(..., description="Dirección IP")
    user_agent: str | None = Field(None, description="Agente de usuario")
    status: str = Field("success", description="Estado de la acción")
    details: dict = Field(default_factory=dict, description="Detalles adicionales")

    # timestamp puede usar created_at de BaseModelDB

    class Config:
        allow_population_by_field_name = True
        extra = 'ignore'
