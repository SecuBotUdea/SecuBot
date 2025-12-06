from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from .base import BaseModelDB

__all__ = ['Remediation']


class Remediation(BaseModelDB):
    """
    Contrato de datos para la entidad Remediation (solo datos — sin lógica).

    Campos:
      - remediation_id: PK
      - alert_id: FK -> Alert
      - user_id: FK -> User
      - team_id: FK -> Team
      - type: tipo de acción de remediación
      - action_ts: timestamp de la acción
      - status: estado (ej. 'pending', 'in_progress', 'done', 'failed')
      - notes: notas o comentarios
      - metadata: objeto libre
      - created_at / updated_at heredados
    """

    remediation_id: str = Field(..., description='Identificador único de la remediación (PK).')

    alert_id: str = Field(..., description='ID de la alerta asociada (FK).')
    user_id: str = Field(..., description='ID del usuario que realizó la acción (FK).')
    team_id: str = Field(..., description='ID del equipo responsable (FK).')

    type: str = Field(..., description='Tipo de remediación realizada.')
    action_ts: datetime = Field(..., description='Fecha y hora de la acción.')
    status: str = Field(..., description='Estado actual de la remediación.')
    notes: str | None = Field(None, description='Comentarios adicionales.')

    metadata: dict[str, Any] = Field(default_factory=dict, description='Metadatos adicionales.')
