"""
Servicio de re-escaneo de vulnerabilidades.
Responsabilidad única: Consultar el normalizador, determinar si una alerta aún existe,
y guardar el resultado del rescan en MongoDB.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from uuid import uuid4
import aiohttp

from app.database.mongodb import get_database
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RescanResult:
    """Resultado de un re-escaneo"""
    
    def __init__(
        self,
        alert_id: str,
        still_exists: bool,
        reopen_count_changed: bool,
        local_reopen_count: int,
        normalizer_reopen_count: int,
        scan_timestamp: datetime,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.alert_id = alert_id
        self.still_exists = still_exists  # ¿La vulnerabilidad aún existe?
        self.reopen_count_changed = reopen_count_changed
        self.local_reopen_count = local_reopen_count
        self.normalizer_reopen_count = normalizer_reopen_count
        self.scan_timestamp = scan_timestamp
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "still_exists": self.still_exists,
            "reopen_count_changed": self.reopen_count_changed,
            "local_reopen_count": self.local_reopen_count,
            "normalizer_reopen_count": self.normalizer_reopen_count,
            "scan_timestamp": self.scan_timestamp.isoformat(),
            "metadata": self.metadata
        }


class RescanService:
    """
    Servicio para verificar si una vulnerabilidad aún existe.
    
    Lógica:
    - GET a https://parser-dependabot.vercel.app/alerts/{alert_id}
    - Compara reopen_count local vs normalizer
    - Si normalizer.reopen_count > local.reopen_count → Vulnerabilidad REAPARECE
    - Si normalizer.reopen_count == local.reopen_count → Vulnerabilidad REMEDIADA
    - Guarda el resultado en la colección 'rescans'
    """
    
    NORMALIZER_URL = "https://parser-dependabot.vercel.app"
    
    def __init__(self):
        self.db = get_database()
        self.collection = self.db.rescans
    
    async def check_alert_exists(
        self,
        alert_id: str,
        local_reopen_count: int,
        remediation_id: Optional[str] = None
    ) -> RescanResult:
        """
        Verifica si una alerta aún existe consultando el normalizador
        y guarda el resultado en MongoDB.
        
        Args:
            alert_id: ID de la alerta a verificar
            local_reopen_count: Contador local de reaperturas
            remediation_id: ID de la remediación asociada (opcional)
            
        Returns:
            RescanResult indicando si la vulnerabilidad aún existe
            
        Raises:
            Exception: Si hay error en la consulta al normalizador
        """
        now = datetime.now(timezone.utc)
        rescan_id = self._generate_rescan_id()
        url = f"{self.NORMALIZER_URL}/alerts/{alert_id}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    
                    # Alerta no existe en el normalizador
                    if response.status == 404:
                        logger.warning(f"Alert {alert_id} not found in normalizer")
                        
                        # Guardar rescan con status "alert_not_found"
                        await self._save_rescan(
                            rescan_id=rescan_id,
                            alert_id=alert_id,
                            remediation_id=remediation_id,
                            present=False,
                            status="alert_not_found",
                            scan_output="Alert not found in normalizer (404)",
                            executed_at=now
                        )
                        
                        raise Exception(f"Alert {alert_id} not found in normalizer")
                    
                    # Error del servidor
                    if response.status != 200:
                        error_text = await response.text()
                        
                        # Guardar rescan con status "error"
                        await self._save_rescan(
                            rescan_id=rescan_id,
                            alert_id=alert_id,
                            remediation_id=remediation_id,
                            present=False,
                            status="error",
                            scan_output=f"Normalizer error {response.status}: {error_text}",
                            executed_at=now
                        )
                        
                        raise Exception(f"Normalizer error {response.status}: {error_text}")
                    
                    # Parsear respuesta
                    data = await response.json()
                    normalizer_reopen_count = data.get("reopen_count", 0)
                    
                    # LÓGICA CRÍTICA: Comparar reopen_count
                    reopen_count_changed = normalizer_reopen_count > local_reopen_count
                    still_exists = reopen_count_changed
                    
                    # Determinar status del rescan
                    if still_exists:
                        status = "vulnerability_persists"
                        logger.info(
                            f"Alert {alert_id} REAPARECE: "
                            f"local={local_reopen_count}, normalizer={normalizer_reopen_count}"
                        )
                    else:
                        status = "vulnerability_resolved"
                        logger.info(
                            f"Alert {alert_id} REMEDIADA: "
                            f"reopen_count={local_reopen_count} (sin cambios)"
                        )
                    
                    # Guardar rescan exitoso
                    await self._save_rescan(
                        rescan_id=rescan_id,
                        alert_id=alert_id,
                        remediation_id=remediation_id,
                        present=still_exists,
                        status=status,
                        scan_output=f"Rescan completed. Reopen count: local={local_reopen_count}, normalizer={normalizer_reopen_count}",
                        executed_at=now
                    )
                    
                    return RescanResult(
                        alert_id=alert_id,
                        still_exists=still_exists,
                        reopen_count_changed=reopen_count_changed,
                        local_reopen_count=local_reopen_count,
                        normalizer_reopen_count=normalizer_reopen_count,
                        scan_timestamp=now,
                        metadata={
                            "rescan_id": rescan_id,
                            "http_status": 200,
                            "reopen_count_delta": normalizer_reopen_count - local_reopen_count,
                            "normalizer_data": data
                        }
                    )
        
        except aiohttp.ClientError as e:
            logger.error(f"Network error checking alert {alert_id}: {e}")
            
            # Guardar rescan con error de red
            await self._save_rescan(
                rescan_id=rescan_id,
                alert_id=alert_id,
                remediation_id=remediation_id,
                present=False,
                status="network_error",
                scan_output=f"Failed to connect to normalizer: {str(e)}",
                executed_at=now
            )
            
            raise Exception(f"Failed to connect to normalizer: {e}")
        
        except Exception as e:
            logger.error(f"Error checking alert {alert_id}: {e}")
            raise
    
    async def _save_rescan(
        self,
        rescan_id: str,
        alert_id: str,
        remediation_id: Optional[str],
        present: bool,
        status: str,
        scan_output: str,
        executed_at: datetime
    ) -> Dict[str, Any]:
        """
        Guardar resultado del rescan en MongoDB.
        
        Args:
            rescan_id: ID único del rescan
            alert_id: ID de la alerta escaneada
            remediation_id: ID de la remediación (si aplica)
            present: ¿La vulnerabilidad está presente?
            status: Estado del rescan
            scan_output: Salida del escaneo
            executed_at: Timestamp de ejecución
            
        Returns:
            Dict con el rescan guardado
        """
        rescan_doc = {
            "rescan_id": rescan_id,
            "alert_id": alert_id,
            "remediation_id": remediation_id or "",
            "present": present,
            "status": status,
            "scan_output": scan_output,
            "executed_at": executed_at
        }
        
        result = await self.collection.insert_one(rescan_doc)
        rescan_doc["_id"] = str(result.inserted_id)
        
        logger.info(f"Rescan guardado: {rescan_id} - status={status}")
        
        return rescan_doc
    
    async def get_rescan(self, rescan_id: str) -> Optional[Dict[str, Any]]:
        """Obtener un rescan por ID"""
        rescan = await self.collection.find_one({"rescan_id": rescan_id})
        if rescan:
            rescan["_id"] = str(rescan["_id"])
        return rescan
    
    async def get_rescans_by_alert(self, alert_id: str, limit: int = 50) -> list:
        """Obtener todos los rescans de una alerta"""
        rescans = await self.collection.find(
            {"alert_id": alert_id}
        ).sort("executed_at", -1).limit(limit).to_list(length=limit)
        
        for rescan in rescans:
            rescan["_id"] = str(rescan["_id"])
        
        return rescans
    
    async def get_rescans_by_remediation(self, remediation_id: str) -> list:
        """Obtener todos los rescans asociados a una remediación"""
        rescans = await self.collection.find(
            {"remediation_id": remediation_id}
        ).sort("executed_at", -1).to_list(length=None)
        
        for rescan in rescans:
            rescan["_id"] = str(rescan["_id"])
        
        return rescans
    
    def _generate_rescan_id(self) -> str:
        """Generar ID único para rescan"""
        return f"rescan_{uuid4().hex[:12]}"


# Singleton
_rescan_service = None

def get_rescan_service() -> RescanService:
    """Obtener instancia única del servicio"""
    global _rescan_service
    if _rescan_service is None:
        _rescan_service = RescanService()
    return _rescan_service