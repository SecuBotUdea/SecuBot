from __future__ import annotations

from typing import Any

from pydantic import Field

from .base import BaseModelDB

__all__ = ['Source']


class Source(BaseModelDB):
    """
    Contrato de datos para la entidad Source.

    Campos:
      - source_id: PK (string)
      - name: nombre legible de la fuente
      - type: tipo de fuente (ej. 'sast', 'sca', 'dast', 'manual', etc.)
      - metadata: objeto libre
      - created_at / updated_at heredados
    """

    source_id: str = Field(..., description='Identificador principal de la fuente (PK).')
    name: str = Field(..., description='Nombre de la fuente.')
    type: str = Field(..., description='Tipo o categoría de la fuente.')
    metadata: dict[str, Any] = Field(default_factory=dict, description='Metadatos adicionales.')
