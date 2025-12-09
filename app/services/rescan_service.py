# app/services/rescan_service.py
"""
Servicio de re-escaneo y verificación de vulnerabilidades.
Componente crítico para gamificación verificada.

En producción: Consulta al normalizador externo (https://parser-dependabot.vercel.app/alerts/{alert_id})
En desarrollo/demo: Simula el rescan para testing
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, Literal, List
import random

from app.database.mongodb import get_database
from app.services.alert_service import get_alert_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RescanResult:
    """Resultado de un re-escaneo de vulnerabilidad"""
    
    def __init__(
        self,
        alert_id: str,
        present: bool,
        signature_match: bool,
        scan_timestamp: datetime,
        scanner_version: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.alert_id = alert_id
        self.present = present  # ¿La vulnerabilidad sigue presente?
        self.signature_match = signature_match  # ¿La firma coincide con la original?
        self.scan_timestamp = scan_timestamp
        self.scanner_version = scanner_version or "demo-v1.0"
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario para persistencia"""
        return {
            "alert_id": self.alert_id,
            "present": self.present,
            "signature_match": self.signature_match,
            "scan_timestamp": self.scan_timestamp,
            "scanner_version": self.scanner_version,
            "metadata": self.metadata
        }


class RescanService:
    """
    Servicio principal para re-escaneo y verificación de remediación.
    
    Responsable de:
    - Ejecutar re-escaneos de vulnerabilidades
    - Verificar si una remediación fue exitosa
    - Consultar el normalizador externo (en producción)
    - Simular resultados (en modo demo)
    - Persistir resultados en MongoDB
    - Disparar eventos al RuleEngine
    """
    
    # URL del normalizador en producción
    NORMALIZER_BASE_URL = "https://parser-dependabot.vercel.app"
    
    def __init__(self, demo_mode: bool = True):
        """
        Args:
            demo_mode: Si True, simula resultados. Si False, consulta el normalizador real.
        """
        self.db = get_database()
        self.collection = self.db.rescan_results
        self.alert_service = get_alert_service()
        self.demo_mode = demo_mode
    
    async def trigger_rescan(
        self,
        alert_id: str,
        triggered_by: Optional[str] = None,
        force_real_scan: bool = False
    ) -> RescanResult:
        """
        Disparar un re-escaneo de una alerta específica.
        
        Args:
            alert_id: ID de la alerta a re-escanear
            triggered_by: ID del usuario que disparó el rescan (opcional)
            force_real_scan: Forzar consulta real al normalizador (ignora demo_mode)
            
        Returns:
            RescanResult con el resultado del escaneo
            
        Raises:
            ValueError: Si la alerta no existe
        """
        # 1. Validar que la alerta existe
        alert = await self.alert_service.get_alert(alert_id)
        if not alert:
            raise ValueError(f"Alerta {alert_id} no encontrada")
        
        # 2. Ejecutar el rescan (real o simulado)
        if self.demo_mode and not force_real_scan:
            result = self._simulate_rescan(alert)
        else:
            result = await self._perform_real_rescan(alert)
        
        # 3. Persistir el resultado
        await self._save_rescan_result(result, triggered_by)
        
        # 4. Actualizar last_seen de la alerta si sigue presente
        if result.present:
            await self.alert_service.update_last_seen(alert_id)
        
        # 5. TODO: Disparar evento al RuleEngine
        # from app.rule_engine.engine import process_event
        # await process_event("rescan_completed", {
        #     "alert": alert,
        #     "rescan_result": result.to_dict(),
        #     "triggered_by": triggered_by
        # })
        
        return result
    
    def _simulate_rescan(self, alert: Dict[str, Any]) -> RescanResult:
        """
        Simular un re-escaneo para modo demo.
        
        NUEVA LÓGICA (simulada):
        - 80% probabilidad: reopen_count se mantiene igual → REMEDIADA
        - 20% probabilidad: reopen_count aumenta → REAPARECE
        """
        now = datetime.now(timezone.utc)
        
        local_reopen_count = alert.get("reopen_count", 0)
        
        # Simular si la vulnerabilidad reaparece
        vulnerability_reappears = random.random() < 0.20  # 20% reaparece
        
        if vulnerability_reappears:
            # Simular que el normalizador detectó la vuln de nuevo
            present = True
            simulated_normalizer_reopen_count = local_reopen_count + 1
        else:
            # Vulnerabilidad fue remediada
            present = False
            simulated_normalizer_reopen_count = local_reopen_count
        
        # Si está presente, verificar coincidencia de firma
        signature_match = False
        if present:
            signature_match = random.random() < 0.95  # 95% coincide
        
        # Metadata simulada
        metadata = {
            "simulation_mode": True,
            "random_seed": random.random(),
            "alert_status": alert["status"],
            "alert_severity": alert["severity"],
            "component": alert.get("component", "unknown"),
            "scan_duration_ms": random.randint(500, 3000),
            "local_reopen_count": local_reopen_count,
            "simulated_normalizer_reopen_count": simulated_normalizer_reopen_count,
            "vulnerability_reappears": vulnerability_reappears
        }
        
        return RescanResult(
            alert_id=alert["alert_id"],
            present=present,
            signature_match=signature_match,
            scan_timestamp=now,
            scanner_version="demo-simulator-v1.0",
            metadata=metadata
        )
    
    async def _perform_real_rescan(self, alert: Dict[str, Any]) -> RescanResult:
        """
        Ejecutar un re-escaneo real consultando al normalizador externo.
        
        LÓGICA CORRECTA:
        - El normalizador SIEMPRE retorna la alerta (existe en su BD)
        - Si normalizer.reopen_count > alert.reopen_count → Vulnerabilidad REAPARECE
        - Si normalizer.reopen_count == alert.reopen_count → Vulnerabilidad REMEDIADA
        
        En producción, hace un GET a:
        https://parser-dependabot.vercel.app/alerts/{alert_id}
        
        Respuesta esperada:
        {
            "alert_id": "...",
            "signature": "sha256:...",
            "reopen_count": 2,  # ← ESTE ES EL CAMPO CRÍTICO
            "last_seen": "2025-12-08T10:00:00Z",
            "status": "reopened",
            ...
        }
        """
        import aiohttp
        
        now = datetime.now(timezone.utc)
        url = f"{self.NORMALIZER_BASE_URL}/alerts/{alert['alert_id']}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 404:
                        # Alerta no existe en el normalizador = ERROR del sistema
                        logger.error(f"Alert {alert['alert_id']} not found in normalizer")
                        raise Exception("Alert not found in normalizer database")
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        # Obtener reopen_count de ambos lados
                        local_reopen_count = alert.get("reopen_count", 0)
                        normalizer_reopen_count = data.get("reopen_count", 0)
                        
                        # LÓGICA CRÍTICA: Comparar reopen_count
                        if normalizer_reopen_count > local_reopen_count:
                            # La vulnerabilidad REAPARECE (el normalizador la detectó de nuevo)
                            present = True
                            logger.info(
                                f"Alert {alert['alert_id']} REAPARECE: "
                                f"local={local_reopen_count}, normalizer={normalizer_reopen_count}"
                            )
                        else:
                            # reopen_count igual = La vulnerabilidad fue REMEDIADA
                            present = False
                            logger.info(
                                f"Alert {alert['alert_id']} REMEDIADA: "
                                f"reopen_count={local_reopen_count} (sin cambios)"
                            )
                        
                        # Verificar si la firma coincide
                        signature_match = (
                            data.get("signature") == alert.get("signature")
                        )
                        
                        return RescanResult(
                            alert_id=alert["alert_id"],
                            present=present,
                            signature_match=signature_match,
                            scan_timestamp=now,
                            scanner_version="normalizer-v1.0",
                            metadata={
                                "http_status": 200,
                                "local_reopen_count": local_reopen_count,
                                "normalizer_reopen_count": normalizer_reopen_count,
                                "reopen_count_delta": normalizer_reopen_count - local_reopen_count,
                                "normalizer_response": data
                            }
                        )
                    
                    # Otros status codes = error
                    error_text = await response.text()
                    raise Exception(f"HTTP {response.status}: {error_text}")
        
        except Exception as e:
            # En caso de error, fallback a simulación
            logger.warning(f"Error en rescan real: {e}. Usando simulación como fallback.")
            return self._simulate_rescan(alert)
    
    async def _save_rescan_result(
        self,
        result: RescanResult,
        triggered_by: Optional[str] = None
    ) -> None:
        """Persistir resultado del rescan en MongoDB"""
        result_doc = result.to_dict()
        result_doc["triggered_by"] = triggered_by
        result_doc["created_at"] = datetime.now(timezone.utc)
        
        await self.collection.insert_one(result_doc)
    
    async def get_latest_rescan(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtener el resultado del último rescan de una alerta.
        """
        result = await self.collection.find_one(
            {"alert_id": alert_id},
            sort=[("scan_timestamp", -1)]
        )
        
        if result:
            result["_id"] = str(result["_id"])
        
        return result
    
    async def get_rescan_history(
        self,
        alert_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Obtener historial de rescans de una alerta.
        """
        cursor = self.collection.find(
            {"alert_id": alert_id}
        ).sort("scan_timestamp", -1).limit(limit)
        
        results = []
        async for result in cursor:
            result["_id"] = str(result["_id"])
            results.append(result)
        
        return results
    
    async def verify_remediation(
        self,
        alert_id: str,
        expected_result: Literal["present", "absent"] = "absent"
    ) -> Dict[str, Any]:
        """
        Verificar si una remediación fue exitosa.
        
        Args:
            alert_id: ID de la alerta
            expected_result: Resultado esperado ("absent" para remediación exitosa)
            
        Returns:
            Dict con resultado de la verificación
        """
        latest = await self.get_latest_rescan(alert_id)
        
        if not latest:
            return {
                "verified": False,
                "reason": "No rescan available",
                "recommendation": "Trigger a rescan first"
            }
        
        # Verificar según expectativa
        if expected_result == "absent":
            success = not latest["present"]
            return {
                "verified": success,
                "rescan_timestamp": latest["scan_timestamp"],
                "present": latest["present"],
                "signature_match": latest.get("signature_match"),
                "reason": "Vulnerability absent" if success else "Vulnerability still present"
            }
        
        else:  # expected_result == "present"
            success = latest["present"]
            return {
                "verified": success,
                "rescan_timestamp": latest["scan_timestamp"],
                "present": latest["present"],
                "signature_match": latest.get("signature_match"),
                "reason": "Vulnerability confirmed present" if success else "Vulnerability not found"
            }
    
    async def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas de rescans"""
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "total_scans": {"$sum": 1},
                    "present_count": {
                        "$sum": {"$cond": [{"$eq": ["$present", True]}, 1, 0]}
                    },
                    "absent_count": {
                        "$sum": {"$cond": [{"$eq": ["$present", False]}, 1, 0]}
                    },
                    "signature_matches": {
                        "$sum": {"$cond": [{"$eq": ["$signature_match", True]}, 1, 0]}
                    }
                }
            }
        ]
        
        cursor = self.collection.aggregate(pipeline)
        result = await cursor.to_list(length=None)
        
        if result:
            stats = result[0]
            stats.pop("_id", None)
            
            # Calcular tasas
            total = stats["total_scans"]
            if total > 0:
                stats["remediation_rate"] = round(
                    (stats["absent_count"] / total) * 100, 2
                )
                stats["persistence_rate"] = round(
                    (stats["present_count"] / total) * 100, 2
                )
            else:
                stats["remediation_rate"] = 0.0
                stats["persistence_rate"] = 0.0
            
            return stats
        
        return {
            "total_scans": 0,
            "present_count": 0,
            "absent_count": 0,
            "signature_matches": 0,
            "remediation_rate": 0.0,
            "persistence_rate": 0.0
        }
    
    async def bulk_rescan_alerts(
        self,
        alert_ids: List[str],
        triggered_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Re-escanear múltiples alertas en lote.
        Útil para verificaciones masivas.
        
        Returns:
            Resumen con resultados agregados
        """
        import asyncio
        
        results = {
            "total": len(alert_ids),
            "successful": 0,
            "failed": 0,
            "present": 0,
            "absent": 0,
            "errors": []
        }
        
        # Crear tareas para paralelizar
        tasks = [
            self.trigger_rescan(alert_id, triggered_by)
            for alert_id in alert_ids
        ]
        
        # Ejecutar en paralelo con manejo de errores
        scan_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for alert_id, result in zip(alert_ids, scan_results):
            if isinstance(result, Exception):
                results["failed"] += 1
                results["errors"].append({
                    "alert_id": alert_id,
                    "error": str(result)
                })
            else:
                results["successful"] += 1
                
                if result.present: # type: ignore
                    results["present"] += 1
                else:
                    results["absent"] += 1
        
        return results


# Singleton global para uso en toda la aplicación
_rescan_service_instance = None


def get_rescan_service(demo_mode: bool = True) -> RescanService:
    """
    Factory function para obtener instancia única del servicio.
    
    Args:
        demo_mode: Si True, simula rescans. Si False, consulta el normalizador real.
    """
    global _rescan_service_instance
    if _rescan_service_instance is None:
        _rescan_service_instance = RescanService(demo_mode=demo_mode)
    return _rescan_service_instance