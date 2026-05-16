from __future__ import annotations

from pydantic import Field

from .base import BaseModelDB

__all__ = ['Server']


class Server(BaseModelDB):
    """
    Contrato de datos para la entidad Server.

    Campos:
      - server_id: PK de negocio (string)
      - guild_id: ID del servidor en Discord
      - guild_name: nombre del servidor
      - webhook_url: webhook activo asociado
      - active: indica si el webhook/servidor está activo
    """

    server_id: str = Field(..., description='Primary business identifier (PK) del servidor.')
    guild_id: str = Field(..., description='Discord guild id asociado.')
    guild_name: str | None = Field(default=None, description='Nombre del servidor Discord.')
    webhook_url: str | None = Field(
        default=None, description='Webhook incoming asociado al servidor.'
    )
    active: bool = Field(default=True, description='Estado activo del webhook del servidor.')
