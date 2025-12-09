"""
Servicio de re-escaneo de vulnerabilidades.
Responsabilidad única: Consultar el normalizador y determinar si una alerta aún existe.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
import aiohttp

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
    """
    
    NORMALIZER_URL = "https://parser-dependabot.vercel.app"
    
    async def check_alert_exists(
        self,
        alert_id: str,
        local_reopen_count: int
    ) -> RescanResult:
        """
        Verifica si una alerta aún existe consultando el normalizador.
        
        Args:
            alert_id: ID de la alerta a verificar
            local_reopen_count: Contador local de reaperturas
            
        Returns:
            RescanResult indicando si la vulnerabilidad aún existe
            
        Raises:
            Exception: Si hay error en la consulta al normalizador
        """
        now = datetime.now(timezone.utc)
        url = f"{self.NORMALIZER_URL}/alerts/{alert_id}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    
                    # Alerta no existe en el normalizador
                    if response.status == 404:
                        logger.warning(f"Alert {alert_id} not found in normalizer")
                        raise Exception(f"Alert {alert_id} not found in normalizer")
                    
                    # Error del servidor
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Normalizer error {response.status}: {error_text}")
                    
                    # Parsear respuesta
                    data = await response.json()
                    normalizer_reopen_count = data.get("reopen_count", 0)
                    
                    # LÓGICA CRÍTICA: Comparar reopen_count
                    reopen_count_changed = normalizer_reopen_count > local_reopen_count
                    still_exists = reopen_count_changed
                    
                    if still_exists:
                        logger.info(
                            f"Alert {alert_id} REAPARECE: "
                            f"local={local_reopen_count}, normalizer={normalizer_reopen_count}"
                        )
                    else:
                        logger.info(
                            f"Alert {alert_id} REMEDIADA: "
                            f"reopen_count={local_reopen_count} (sin cambios)"
                        )
                    
                    return RescanResult(
                        alert_id=alert_id,
                        still_exists=still_exists,
                        reopen_count_changed=reopen_count_changed,
                        local_reopen_count=local_reopen_count,
                        normalizer_reopen_count=normalizer_reopen_count,
                        scan_timestamp=now,
                        metadata={
                            "http_status": 200,
                            "reopen_count_delta": normalizer_reopen_count - local_reopen_count,
                            "normalizer_data": data
                        }
                    )
        
        except aiohttp.ClientError as e:
            logger.error(f"Network error checking alert {alert_id}: {e}")
            raise Exception(f"Failed to connect to normalizer: {e}")
        
        except Exception as e:
            logger.error(f"Error checking alert {alert_id}: {e}")
            raise


# Singleton
_rescan_service = None

def get_rescan_service() -> RescanService:
    """Obtener instancia única del servicio"""
    global _rescan_service
    if _rescan_service is None:
        _rescan_service = RescanService()
    return _rescan_service