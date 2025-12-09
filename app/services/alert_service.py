from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from app.models.alert import Alert
from app.database.mongodb import get_database


class AlertService:
    """
    Servicio principal para gestión de alertas de seguridad.
    
    Responsable de:
    - Recibir alertas ya normalizadas vía webhook
    - Validar contra el modelo Pydantic
    - Persistir en MongoDB
    - Gestionar ciclo de vida (status, reopen, etc.)
    - Proveer queries para el RuleEngine
    """

    def __init__(self):
        self.db = get_database()
        self.collection = self.db.alerts

    async def create_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crear una nueva alerta en el sistema.
        
        Args:
            alert_data: Payload ya normalizado desde el normalizador externo
            
        Returns:
            Dict con la alerta creada y metadata
            
        Raises:
            ValueError: Si los datos no cumplen el contrato Pydantic
        """
        # 1. Validar contra el modelo Pydantic
        try:
            alert = Alert(**alert_data)
        except Exception as e:
            raise ValueError(f"Datos inválidos para Alert: {str(e)}")
        
        # 2. Convertir a dict para MongoDB
        alert_dict = alert.model_dump()
        
        # 3. Verificar si ya existe (por alert_id)
        existing = await self.collection.find_one({"alert_id": alert_dict["alert_id"]})
        if existing:
            return {
                "status": "duplicate",
                "alert_id": alert_dict["alert_id"],
                "message": f"Alerta {alert_dict['alert_id']} ya existe"
            }
        
        # 4. Insertar en MongoDB
        result = await self.collection.insert_one(alert_dict)
        alert_dict["_id"] = str(result.inserted_id)

        
        return {
            "status": "created",
            "alert_id": alert_dict["alert_id"],
            "alert": alert_dict,
            "message": f"Alerta {alert_dict['alert_id']} creada exitosamente"
        }

    async def get_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtener una alerta por su alert_id (PK).
        
        Args:
            alert_id: Identificador único de la alerta
            
        Returns:
            Dict con la alerta o None si no existe
        """
        alert = await self.collection.find_one({"alert_id": alert_id})
        if alert:
            alert["_id"] = str(alert["_id"])
        return alert

    async def get_alert_by_signature(self, signature: str) -> Optional[Dict[str, Any]]:
        """
        Obtener una alerta por su firma técnica.
        Útil para detectar recurrencias del mismo hallazgo.
        """
        alert = await self.collection.find_one({"signature": signature})
        if alert:
            alert["_id"] = str(alert["_id"])
        return alert

    async def list_alerts(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        source_id: Optional[str] = None,
        quality: Optional[str] = None,
        component: Optional[str] = None,
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Listar alertas con filtros opcionales.
        
        Returns:
            Lista de alertas ordenadas por first_seen descendente
        """
        query = {}
        
        if status:
            query["status"] = status
        if severity:
            query["severity"] = severity
        if source_id:
            query["source_id"] = source_id
        if quality:
            query["quality"] = quality
        if component:
            query["component"] = component
        
        cursor = self.collection.find(query).sort("first_seen", -1).skip(skip).limit(limit)
        
        alerts = []
        async for alert in cursor:
            alert["_id"] = str(alert["_id"])
            alerts.append(alert)
        
        return alerts

    async def update_status(
        self,
        alert_id: str,
        new_status: str,
        event_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Actualizar el estado de una alerta y registrar en lifecycle_history.
        
        Args:
            alert_id: ID de la alerta
            new_status: Nuevo estado (open, closed, reopened, etc.)
            event_metadata: Metadata adicional del evento
            
        Returns:
            Alerta actualizada
        """
        alert = await self.get_alert(alert_id)
        
        if not alert:
            raise ValueError(f"Alerta {alert_id} no encontrada")
        
        now = datetime.now(timezone.utc)
        
        # Crear evento del lifecycle
        lifecycle_event = {
            "timestamp": now,
            "old_status": alert["status"],
            "new_status": new_status,
            "metadata": event_metadata or {}
        }
        
        update_data = {
            "status": new_status,
            "last_seen": now,
            "updated_at": now,
            "version": alert.get("version", 1) + 1
        }
        
        # Tracking especial para reaperturas
        if new_status == "reopened":
            update_data["reopen_count"] = alert.get("reopen_count", 0) + 1
            update_data["last_reopened_at"] = now
        
        # Actualizar en MongoDB
        await self.collection.update_one(
            {"alert_id": alert_id},
            {
                "$set": update_data,
                "$push": {"lifecycle_history": lifecycle_event}
            }
        )
        
        # TODO: Disparar evento al RuleEngine
        # await process_event(f"alert_status_changed", {
        #     "alert_id": alert_id,
        #     "old_status": alert["status"],
        #     "new_status": new_status
        # })
        
        getAlertResult = await self.get_alert(alert_id)
        assert getAlertResult is not None
        
        return getAlertResult

    async def reopen_alert(self, alert_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Reabrir una alerta cerrada.
        Incrementa reopen_count y registra en lifecycle_history.
        """
        return await self.update_status(
            alert_id,
            "reopened",
            event_metadata={"reason": reason or "Vulnerability detected again"}
        )

    async def close_alert(self, alert_id: str, closed_by: Optional[str] = None) -> Dict[str, Any]:
        """
        Cerrar una alerta.
        """
        return await self.update_status(
            alert_id,
            "closed",
            event_metadata={"closed_by": closed_by}
        )

    async def update_last_seen(self, alert_id: str) -> Dict[str, Any]:
        """
        Actualizar el timestamp last_seen cuando la alerta se detecta nuevamente.
        NO cambia el status, solo actualiza la fecha.
        """
        now = datetime.now(timezone.utc)
        
        await self.collection.update_one(
            {"alert_id": alert_id},
            {
                "$set": {
                    "last_seen": now,
                    "updated_at": now
                }
            }
        )
        
        getAlertResult = await self.get_alert(alert_id)
        assert getAlertResult is not None
        
        return getAlertResult

    async def get_alerts_by_component(self, component: str) -> List[Dict[str, Any]]:
        """
        Obtener todas las alertas de un componente específico.
        Útil para análisis de vulnerabilidades por módulo.
        """
        return await self.list_alerts(component=component, limit=1000)

    async def get_open_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Obtener alertas abiertas (status: open o reopened).
        """
        query = {"status": {"$in": ["open", "reopened"]}}
        cursor = self.collection.find(query).sort("severity", 1).limit(limit)
        
        alerts = []
        async for alert in cursor:
            alert["_id"] = str(alert["_id"])
            alerts.append(alert)
        
        return alerts

    async def get_high_quality_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Obtener alertas de alta calidad.
        Útil para priorización de remediación.
        """
        return await self.list_alerts(quality="high", limit=limit)

    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtener estadísticas generales de alertas.
        """
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "total": {"$sum": 1},
                    "open": {
                        "$sum": {"$cond": [{"$eq": ["$status", "open"]}, 1, 0]}
                    },
                    "closed": {
                        "$sum": {"$cond": [{"$eq": ["$status", "closed"]}, 1, 0]}
                    },
                    "reopened": {
                        "$sum": {"$cond": [{"$eq": ["$status", "reopened"]}, 1, 0]}
                    },
                    "critical": {
                        "$sum": {"$cond": [{"$eq": ["$severity", "critical"]}, 1, 0]}
                    },
                    "high": {
                        "$sum": {"$cond": [{"$eq": ["$severity", "high"]}, 1, 0]}
                    },
                    "medium": {
                        "$sum": {"$cond": [{"$eq": ["$severity", "medium"]}, 1, 0]}
                    },
                    "low": {
                        "$sum": {"$cond": [{"$eq": ["$severity", "low"]}, 1, 0]}
                    },
                    "high_quality": {
                        "$sum": {"$cond": [{"$eq": ["$quality", "high"]}, 1, 0]}
                    },
                    "medium_quality": {
                        "$sum": {"$cond": [{"$eq": ["$quality", "medium"]}, 1, 0]}
                    },
                    "low_quality": {
                        "$sum": {"$cond": [{"$eq": ["$quality", "low"]}, 1, 0]}
                    },
                    "total_reopens": {"$sum": "$reopen_count"}
                }
            }
        ]
        
        cursor = self.collection.aggregate(pipeline)
        result = await cursor.to_list(length=None)
        
        if result:
            stats = result[0]
            stats.pop("_id", None)
            return stats
        
        return {
            "total": 0,
            "open": 0,
            "closed": 0,
            "reopened": 0,
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "high_quality": 0,
            "medium_quality": 0,
            "low_quality": 0,
            "total_reopens": 0
        }

    async def get_alerts_with_multiple_reopens(self, min_reopens: int = 2) -> List[Dict[str, Any]]:
        """
        Obtener alertas que han sido reabiertas múltiples veces.
        Útil para identificar vulnerabilidades recurrentes o problemas de calidad.
        """
        query = {"reopen_count": {"$gte": min_reopens}}
        cursor = self.collection.find(query).sort("reopen_count", -1).limit(50)
        
        alerts = []
        async for alert in cursor:
            alert["_id"] = str(alert["_id"])
            alerts.append(alert)
        
        return alerts

    async def delete_alert(self, alert_id: str) -> bool:
        """Eliminar una alerta permanentemente"""
        result = await self.collection.delete_one({"alert_id": alert_id})
        return result.deleted_count > 0

# Singleton global para uso en toda la aplicación
_alert_service_instance = None


def get_alert_service() -> AlertService:
    """Factory function para obtener instancia única del servicio"""
    global _alert_service_instance
    if _alert_service_instance is None:
        _alert_service_instance = AlertService()
    return _alert_service_instance