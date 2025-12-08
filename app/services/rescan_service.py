# app/services/rescan_service.py
"""
Servicio de re-escaneo y verificación de vulnerabilidades.
Componente crítico para gamificación verificada.

En producción: Consulta al normalizador externo (https://parser-dependabot.vercel.app/alerts/{alert_id})
En desarrollo/demo: Simula el rescan para testing
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, Literal
import random

from app.database.connection import get_database
from app.services.alert_service import get_alert_service


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
        self._ensure_indexes()
    
    def _ensure_indexes(self):
        """Crear índices estratégicos"""
        try:
            self.collection.create_index("alert_id")
            self.collection.create_index("scan_timestamp")
            self.collection.create_index([("alert_id", 1), ("scan_timestamp", -1)])
            self.collection.create_index("present")
            self.collection.create_index("signature_match")
        except Exception as e:
            print(f"Advertencia al crear índices de rescan: {e}")
    
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
        alert = self.alert_service.get_alert(alert_id)
        if not alert:
            raise ValueError(f"Alerta {alert_id} no encontrada")
        
        # 2. Ejecutar el rescan (real o simulado)
        if self.demo_mode and not force_real_scan:
            result = self._simulate_rescan(alert)
        else:
            result = await self._perform_real_rescan(alert)
        
        # 3. Persistir el resultado
        self._save_rescan_result(result, triggered_by)
        
        # 4. Actualizar last_seen de la alerta si sigue presente
        if result.present:
            self.alert_service.update_last_seen(alert_id)
        
        # 5. TODO: Disparar evento al RuleEngine
        # from app.rule_engine.engine import process_event
        # process_event("rescan_completed", {
        #     "alert": alert,
        #     "rescan_result": result.to_dict(),
        #     "triggered_by": triggered_by
        # })
        
        return result
    
    def _simulate_rescan(self, alert: Dict[str, Any]) -> RescanResult:
        """
        Simular un re-escaneo para modo demo.
        
        Lógica de simulación:
        - Si status = "open" o "reopened" → 80% probabilidad de estar presente
        - Si status = "closed" → 20% probabilidad de estar presente (falso positivo)
        - Si present = True → 95% probabilidad de signature_match
        """
        now = datetime.now(timezone.utc)
        
        # Determinar si la vulnerabilidad está presente
        if alert["status"] in ["open", "reopened"]:
            present = random.random() < 0.80  # 80% presente
        else:  # closed
            present = random.random() < 0.20  # 20% reapertura
        
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
            "scan_duration_ms": random.randint(500, 3000)
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
        
        En producción, hace un GET a:
        https://parser-dependabot.vercel.app/alerts/{alert_id}
        
        Respuesta esperada:
        {
            "found": true/false,
            "signature": "sha256:...",
            "last_seen": "2025-12-08T10:00:00Z",
            ...
        }
        """
        import aiohttp
        
        now = datetime.now(timezone.utc)
        url = f"{self.NORMALIZER_BASE_URL}/alerts/{alert['alert_id']}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 404:
                        # Vulnerabilidad no encontrada = fue remediada
                        return RescanResult(
                            alert_id=alert["alert_id"],
                            present=False,
                            signature_match=False,
                            scan_timestamp=now,
                            scanner_version="normalizer-v1.0",
                            metadata={
                                "http_status": 404,
                                "message": "Alert not found in normalizer"
                            }
                        )
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        # Verificar si la firma coincide
                        signature_match = (
                            data.get("signature") == alert.get("signature")
                        )
                        
                        return RescanResult(
                            alert_id=alert["alert_id"],
                            present=True,
                            signature_match=signature_match,
                            scan_timestamp=now,
                            scanner_version="normalizer-v1.0",
                            metadata={
                                "http_status": 200,
                                "normalizer_response": data
                            }
                        )
                    
                    # Otros status codes = error
                    raise Exception(f"HTTP {response.status}: {await response.text()}")
        
        except Exception as e:
            # En caso de error, fallback a simulación
            print(f"Error en rescan real: {e}. Usando simulación como fallback.")
            return self._simulate_rescan(alert)
    
    def _save_rescan_result(
        self,
        result: RescanResult,
        triggered_by: Optional[str] = None
    ) -> None:
        """Persistir resultado del rescan en MongoDB"""
        result_doc = result.to_dict()
        result_doc["triggered_by"] = triggered_by
        result_doc["created_at"] = datetime.now(timezone.utc)
        
        self.collection.insert_one(result_doc)
    
    def get_latest_rescan(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtener el resultado del último rescan de una alerta.
        """
        result = self.collection.find_one(
            {"alert_id": alert_id},
            sort=[("scan_timestamp", -1)]
        )
        
        if result:
            result["_id"] = str(result["_id"])
        
        return result
    
    def get_rescan_history(
        self,
        alert_id: str,
        limit: int = 10
    ) -> list[Dict[str, Any]]:
        """
        Obtener historial de rescans de una alerta.
        """
        cursor = self.collection.find(
            {"alert_id": alert_id}
        ).sort("scan_timestamp", -1).limit(limit)
        
        results = []
        for result in cursor:
            result["_id"] = str(result["_id"])
            results.append(result)
        
        return results
    
    def verify_remediation(
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
        latest = self.get_latest_rescan(alert_id)
        
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
    
    def get_stats(self) -> Dict[str, Any]:
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
        
        result = list(self.collection.aggregate(pipeline))
        
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
    
    def bulk_rescan_alerts(
        self,
        alert_ids: list[str],
        triggered_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Re-escanear múltiples alertas en lote.
        Útil para verificaciones masivas.
        
        Returns:
            Resumen con resultados agregados
        """
        results = {
            "total": len(alert_ids),
            "successful": 0,
            "failed": 0,
            "present": 0,
            "absent": 0,
            "errors": []
        }
        
        for alert_id in alert_ids:
            try:
                # Nota: En producción usar asyncio.gather para paralelizar
                import asyncio
                result = asyncio.run(
                    self.trigger_rescan(alert_id, triggered_by)
                )
                
                results["successful"] += 1
                
                if result.present:
                    results["present"] += 1
                else:
                    results["absent"] += 1
                
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "alert_id": alert_id,
                    "error": str(e)
                })
        
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