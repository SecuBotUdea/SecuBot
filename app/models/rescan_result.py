from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from .base import BaseModelDB

__all__ = ['RescanResult']


class RescanResult(BaseModelDB):
    """
    Contrato de datos para la entidad RescanResult (solo datos — sin lógica).

    Campos:
      - rescan_id: PK
      - alert_id: FK -> Alert
      - alert_signature: firma usada para correlación
      - trigger: origen del rescan (manual, scheduled, rule, etc.)
      - scan_ts: timestamp del re-scan
      - present: indica si la alerta sigue presente
      - validated_by: usuario, sistema o regla que validó el resultado
      - raw_payload: datos crudos del motor de escaneo
      - metadata: metadatos adicionales
    """

    rescan_id: str = Field(..., description='Identificador del rescan (PK).')

    alert_id: str = Field(..., description='ID de la alerta asociada (FK).')
    alert_signature: str = Field(..., description='Firma del hallazgo usada para correlación.')
    trigger: str = Field(..., description='Qué disparó el rescan (manual, scheduler, rule, etc.).')

    scan_ts: datetime = Field(..., description='Momento en que se ejecutó el rescan.')

    present: bool = Field(..., description='Indica si la alerta sigue presente tras el rescan.')
    validated_by: str = Field(..., description='Entidad (usuario/sistema) que validó el resultado.')

    raw_payload: dict[str, Any] = Field(
        default_factory=dict, description='Datos crudos proporcionados por el motor de escaneo.'
    )

    metadata: dict[str, Any] = Field(default_factory=dict, description='Metadatos adicionales.')
