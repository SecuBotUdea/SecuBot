from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from .base import BaseModelDB

__all__ = ['Alert']


class Alert(BaseModelDB):
    """
    Contrato de datos para la entidad Alert.

    Campos:
      - alert_id: PK
      - signature: firma o identificador técnico del hallazgo
      - source_id: referencia al origen (FK)
      - severity: severidad (critical/high/medium/low/info)
      - component: módulo/componente afectado
      - status: estado del ciclo de vida (open, closed, reopened, etc.)
      - first_seen: cuándo apareció por primera vez
      - last_seen: última vez registrado
      - quality: métrica cualitativa (ej. signal/noise)
      - normalized_payload: datos normalizados comunes entre SAST/SCA/DAST
      - lifecycle_history: eventos del ciclo de vida (array)
      - reopen_count: número de re-aperturas
      - last_reopened_at: última vez que se reabrió
      - version: versión incremental del hallazgo
      - created_at / updated_at heredados
    """

    alert_id: str = Field(..., description='Identificador principal del hallazgo (PK).')
    signature: str = Field(..., description='Firma o hash del hallazgo.')
    source_id: str = Field(..., description='ID de la fuente que generó la alerta (FK).')

    severity: str = Field(..., description='Severidad de la alerta.')
    component: str = Field(..., description='Componente afectado.')
    status: str = Field(..., description='Estado del ciclo de vida de la alerta.')

    first_seen: datetime = Field(..., description='Primera detección del hallazgo.')
    last_seen: datetime = Field(..., description='Última vez visto.')

    quality: str = Field(..., description='Calidad o confianza del hallazgo.')

    normalized_payload: dict[str, Any] = Field(
        default_factory=dict, description='Payload normalizado independiente de la fuente.'
    )

    lifecycle_history: list[dict[str, Any]] = Field(
        default_factory=list, description='Historial de eventos del ciclo de vida.'
    )

    reopen_count: int = Field(0, description='Veces que la alerta ha sido reabierta.')
    last_reopened_at: datetime | None = Field(None, description='Última fecha de reapertura.')

    version: int = Field(1, description='Versión incremental del hallazgo.')
