from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .base import BaseModelDB

__all__ = ['PointTxn']


class PointTxn(BaseModelDB):
    """
    Contrato de datos para la entidad PointTxn (solo datos — sin lógica).

    Campos:
      - txn_id: PK
      - user_id: FK -> User
      - team_id: FK -> Team
      - rule_id: FK (identificador de la regla que generó la transacción)
      - alert_id: FK -> Alert (opcional)
      - points: puntos otorgados (positivos o negativos)
      - reason: razón humana o contextual
      - timestamp: momento del evento (puede ser distinto a created_at)
      - evidence_refs: links o IDs externos que respaldan la acción
      - penalty_reason: motivo si fue penalización
      - original_alert_status: estado previo del alerta cuando se evaluó la regla
    """

    txn_id: str = Field(..., description='Identificador único de la transacción de puntos (PK).')

    user_id: str = Field(..., description='Usuario afectado (FK).')
    team_id: str = Field(..., description='Equipo afectado (FK).')
    rule_id: str = Field(..., description='Regla que generó la transacción (FK).')

    alert_id: str | None = Field(None, description='ID de la alerta relacionada (FK), si aplica.')

    points: int = Field(..., description='Puntos otorgados (+) o penalización (-).')
    reason: str = Field(..., description='Razón o explicación del puntaje.')

    timestamp: datetime = Field(..., description='Momento en que ocurrió la transacción.')

    evidence_refs: list[str] = Field(
        default_factory=list, description='Referencias externas que respaldan la acción.'
    )

    penalty_reason: str | None = Field(None, description='Motivo de penalización, si aplica.')

    original_alert_status: str | None = Field(
        None, description='Estado de la alerta en el momento del cálculo.'
    )
