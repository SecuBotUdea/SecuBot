from datetime import datetime, timezone
from typing import Any

from app.database.mongodb import get_database
from app.models.alert import Alert
from app.services.notification_service import notification_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AlertService:
    """
    Servicio principal para gestión de alertas de seguridad.

    Responsable de:
    - Recibir alertas ya normalizadas vía webhook
    - Validar contra el modelo Pydantic
    - Persistir en MongoDB
    - Gestionar ciclo de vida (status, reopen, etc.)
    - Enviar notificaciones a Discord
    - Proveer queries para el RuleEngine
    """

    def __init__(self):
        self.db = get_database()
        self.collection = self.db.alerts
        self.notification_service = notification_service

    async def create_alert(self, alert_data: dict[str, Any]) -> dict[str, Any]:
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
            raise ValueError(f'Datos inválidos para Alert: {str(e)}') from e

        # 2. Convertir a dict para MongoDB
        alert_dict = alert.model_dump()

        # 3. Verificar si ya existe (por alert_id)
        existing = await self.collection.find_one({'alert_id': alert_dict['alert_id']})
        if existing:
            return {
                'status': 'duplicate',
                'alert_id': alert_dict['alert_id'],
                'message': f'Alerta {alert_dict["alert_id"]} ya existe',
            }

        # 4. Insertar en MongoDB
        result = await self.collection.insert_one(alert_dict)
        alert_dict['_id'] = str(result.inserted_id)

        # 5. ENVIAR NOTIFICACIÓN A DISCORD
        try:
            notification_sent = await self.notification_service.notify_new_alert(alert)
            if notification_sent:
                logger.info(f'Notificación enviada a Discord para alerta {alert.alert_id}')
            else:
                logger.warning(f'No se pudo enviar notificación para alerta {alert.alert_id}')
        except Exception as e:
            # No fallar la creación de alerta si falla la notificación
            logger.error(f'Error enviando notificación para {alert.alert_id}: {e}')

        return {
            'status': 'created',
            'alert_id': alert_dict['alert_id'],
            'alert': alert_dict,
            'message': f'Alerta {alert_dict["alert_id"]} creada exitosamente',
        }

    async def get_alert(self, alert_id: str) -> dict[str, Any] | None:
        """
        Obtener una alerta por su alert_id (PK).

        Args:
            alert_id: Identificador único de la alerta

        Returns:
            Dict con la alerta o None si no existe
        """
        alert = await self.collection.find_one({'alert_id': alert_id})
        if alert:
            alert['_id'] = str(alert['_id'])
        return alert

    async def get_alert_by_signature(self, signature: str) -> dict[str, Any] | None:
        """
        Obtener una alerta por su firma técnica.
        Útil para detectar recurrencias del mismo hallazgo.
        """
        alert = await self.collection.find_one({'signature': signature})
        if alert:
            alert['_id'] = str(alert['_id'])
        return alert

    async def list_alerts(
        self,
        status: str | None = None,
        severity: str | None = None,
        source_id: str | None = None,
        quality: str | None = None,
        component: str | None = None,
        limit: int = 50,
        skip: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Listar alertas con filtros opcionales.

        Returns:
            Lista de alertas ordenadas por first_seen descendente
        """
        query = {}

        if status:
            query['status'] = status
        if severity:
            query['severity'] = severity
        if source_id:
            query['source_id'] = source_id
        if quality:
            query['quality'] = quality
        if component:
            query['component'] = component

        cursor = self.collection.find(query).sort('first_seen', -1).skip(skip).limit(limit)

        alerts = []
        async for alert in cursor:
            alert['_id'] = str(alert['_id'])
            alerts.append(alert)

        return alerts

    async def update_status(
        self, alert_id: str, new_status: str, event_metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
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
            raise ValueError(f'Alerta {alert_id} no encontrada')

        now = datetime.now(timezone.utc)

        # Crear evento del lifecycle
        lifecycle_event = {
            'timestamp': now,
            'old_status': alert['status'],
            'new_status': new_status,
            'metadata': event_metadata or {},
        }

        update_data = {
            'status': new_status,
            'last_seen': now,
            'updated_at': now,
            'version': alert.get('version', 1) + 1,
        }

        # Tracking especial para reaperturas
        if new_status == 'reopened':
            update_data['reopen_count'] = alert.get('reopen_count', 0) + 1
            update_data['last_reopened_at'] = now

        # Actualizar en MongoDB
        await self.collection.update_one(
            {'alert_id': alert_id},
            {'$set': update_data, '$push': {'lifecycle_history': lifecycle_event}},
        )

        # Obtener alerta actualizada
        updated_alert = await self.get_alert(alert_id)
        assert updated_alert is not None

        # 🆕 ENVIAR NOTIFICACIÓN SI ES REAPERTURA
        if new_status == 'reopened':
            try:
                alert_obj = Alert(**updated_alert)
                await self.notification_service.notify_alert_reopened(alert_obj)
                logger.info(f'Notificación de reapertura enviada para {alert_id}')
            except Exception as e:
                logger.error(f'Error notificando reapertura de {alert_id}: {e}')

        return updated_alert

    async def reopen_alert(self, alert_id: str, reason: str | None = None) -> dict[str, Any]:
        """
        Reabrir una alerta cerrada.
        Incrementa reopen_count y registra en lifecycle_history.
        """
        return await self.update_status(
            alert_id,
            'reopened',
            event_metadata={'reason': reason or 'Vulnerability detected again'},
        )

    async def close_alert(self, alert_id: str, closed_by: str | None = None) -> dict[str, Any]:
        """
        Cerrar una alerta.
        """
        return await self.update_status(alert_id, 'closed', event_metadata={'closed_by': closed_by})

    async def update_last_seen(self, alert_id: str) -> dict[str, Any]:
        """
        Actualizar el timestamp last_seen cuando la alerta se detecta nuevamente.
        NO cambia el status, solo actualiza la fecha.
        """
        now = datetime.now(timezone.utc)

        await self.collection.update_one(
            {'alert_id': alert_id}, {'$set': {'last_seen': now, 'updated_at': now}}
        )

        updated_alert = await self.get_alert(alert_id)
        assert updated_alert is not None

        return updated_alert

    async def get_alerts_by_component(self, component: str) -> list[dict[str, Any]]:
        """
        Obtener todas las alertas de un componente específico.
        Útil para análisis de vulnerabilidades por módulo.
        """
        return await self.list_alerts(component=component, limit=1000)

    async def get_open_alerts(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        Obtener alertas abiertas (status: open o reopened).
        """
        query = {'status': {'$in': ['open', 'reopened']}}
        cursor = self.collection.find(query).sort('severity', 1).limit(limit)

        alerts = []
        async for alert in cursor:
            alert['_id'] = str(alert['_id'])
            alerts.append(alert)

        return alerts

    async def get_high_quality_alerts(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        Obtener alertas de alta calidad.
        Útil para priorización de remediación.
        """
        return await self.list_alerts(quality='high', limit=limit)

    async def get_stats(self) -> dict[str, Any]:
        """
        Obtener estadísticas generales de alertas.
        """
        pipeline = [
            {
                '$group': {
                    '_id': None,
                    'total': {'$sum': 1},
                    'open': {'$sum': {'$cond': [{'$eq': ['$status', 'open']}, 1, 0]}},
                    'closed': {'$sum': {'$cond': [{'$eq': ['$status', 'closed']}, 1, 0]}},
                    'reopened': {'$sum': {'$cond': [{'$eq': ['$status', 'reopened']}, 1, 0]}},
                    'critical': {'$sum': {'$cond': [{'$eq': ['$severity', 'critical']}, 1, 0]}},
                    'high': {'$sum': {'$cond': [{'$eq': ['$severity', 'high']}, 1, 0]}},
                    'medium': {'$sum': {'$cond': [{'$eq': ['$severity', 'medium']}, 1, 0]}},
                    'low': {'$sum': {'$cond': [{'$eq': ['$severity', 'low']}, 1, 0]}},
                    'high_quality': {'$sum': {'$cond': [{'$eq': ['$quality', 'high']}, 1, 0]}},
                    'medium_quality': {'$sum': {'$cond': [{'$eq': ['$quality', 'medium']}, 1, 0]}},
                    'low_quality': {'$sum': {'$cond': [{'$eq': ['$quality', 'low']}, 1, 0]}},
                    'total_reopens': {'$sum': '$reopen_count'},
                }
            }
        ]

        cursor = self.collection.aggregate(pipeline)
        result = await cursor.to_list(length=None)

        if result:
            stats = result[0]
            stats.pop('_id', None)
            return stats

        return {
            'total': 0,
            'open': 0,
            'closed': 0,
            'reopened': 0,
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'high_quality': 0,
            'medium_quality': 0,
            'low_quality': 0,
            'total_reopens': 0,
        }

    async def get_alerts_with_multiple_reopens(self, min_reopens: int = 2) -> list[dict[str, Any]]:
        """
        Obtener alertas que han sido reabiertas múltiples veces.
        Útil para identificar vulnerabilidades recurrentes o problemas de calidad.
        """
        query = {'reopen_count': {'$gte': min_reopens}}
        cursor = self.collection.find(query).sort('reopen_count', -1).limit(50)

        alerts = []
        async for alert in cursor:
            alert['_id'] = str(alert['_id'])
            alerts.append(alert)

        return alerts

    async def acquire_rescan_lock(
        self, alert_id: str, locked_by: str, timeout_minutes: int = 5
    ) -> bool:
        """
        Intenta adquirir un lock atómico para el rescan de una alerta.

        Usa findOneAndUpdate para garantizar atomicidad — solo un proceso
        puede adquirir el lock si no existe o si expiró.

        Returns:
            True si el lock fue adquirido, False si ya está tomado.
        """
        from datetime import timedelta

        now = datetime.now(timezone.utc)
        lock_expiry = now - timedelta(minutes=timeout_minutes)

        result = await self.collection.find_one_and_update(
            {
                'alert_id': alert_id,
                '$or': [
                    {'rescan_lock': {'$exists': False}},
                    {'rescan_lock.locked_at': {'$lt': lock_expiry}},
                ],
            },
            {'$set': {'rescan_lock': {'locked_at': now, 'locked_by': locked_by}}},
        )
        return result is not None

    async def release_rescan_lock(self, alert_id: str) -> None:
        """Libera el lock de rescan de una alerta."""
        await self.collection.update_one(
            {'alert_id': alert_id},
            {'$unset': {'rescan_lock': ''}},
        )

    async def delete_alert(self, alert_id: str) -> bool:
        """Eliminar una alerta permanentemente"""
        result = await self.collection.delete_one({'alert_id': alert_id})
        return result.deleted_count > 0


# Singleton global para uso en toda la aplicación
_alert_service_instance = None


def get_alert_service() -> AlertService:
    """Factory function para obtener instancia única del servicio"""
    global _alert_service_instance
    if _alert_service_instance is None:
        _alert_service_instance = AlertService()
    return _alert_service_instance
