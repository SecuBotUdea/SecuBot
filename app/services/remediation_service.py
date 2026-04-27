"""
RemediationService - Gestión de remediaciones y orquestación con RuleEngine

⭐ SERVICIO CRÍTICO ⭐
Este es el corazón del sistema de gamificación verificada.

Responsabilidades:
- Registrar cuando un usuario marca una alerta como resuelta
- Coordinar con RescanService para verificar la remediación
- INVOCAR AL RULEENGINE después del rescan (AQUÍ PASA LA MAGIA 🎯)
- Actualizar estados de alert y remediation según resultado
- Enviar notificaciones Discord con el resultado de la gamificación

Flujo completo:
1. Usuario dice "Resolví esta vulnerabilidad"
2. create_remediation() → guarda en BD con status="pending"
3. Dispara rescan automático (RescanService.check_alert_exists)
4. process_rescan_result() → INVOCA GAMIFICATIONSERVICE.process_event() 🔥
5. RuleEngine otorga puntos o penaliza
6. Actualiza estados de alert y remediation
7. Envía notificación Discord con resultado
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from uuid import uuid4

from app.database.mongodb import get_database
from app.models.alert import Alert
from app.models.remediation import Remediation
from app.services.alert_service import get_alert_service
from app.services.notification_service import notification_service
from app.services.rescan_service import get_rescan_service
from app.services.gamification_service import get_gamification_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RemediationService:
    """
    Servicio principal para gestión de remediaciones.
    
    Este servicio es el PUENTE entre:
    - Las acciones del usuario (marcar como resuelta)
    - El rescan de verificación (RescanService)
    - La gamificación (GamificationService → RuleEngine)
    """
    
    def __init__(self):
        self.db = get_database()
        self.collection = self.db.remediations
        self.alert_service = get_alert_service()
        self.rescan_service = get_rescan_service()
        self.gamification_service = get_gamification_service()
    
    async def create_remediation(
        self,
        alert_id: str,
        user_id: str,
        remediation_type: str = "user_mark",
        notes: Optional[str] = None,
        team_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        auto_trigger_rescan: bool = True
    ) -> Dict[str, Any]:
        """
        Registrar una remediación (usuario marca alerta como resuelta).
        
        Args:
            alert_id: ID de la alerta que se remedió
            user_id: ID del usuario que hizo la remediación
            remediation_type: Tipo (user_mark | automated | manual_verification)
            notes: Notas del usuario sobre la remediación
            team_id: ID del equipo (opcional)
            metadata: Metadata adicional
            auto_trigger_rescan: Si True, dispara rescan automáticamente
            
        Returns:
            Dict con la remediación creada
            
        Raises:
            ValueError: Si la alerta no existe o no está abierta
        """
        # 1. Validar que la alerta existe
        alert = await self.alert_service.get_alert(alert_id)
        if not alert:
            raise ValueError(f"Alerta {alert_id} no encontrada")
        
        # 2. Validar que la alerta está abierta
        if alert["status"] not in ["open", "reopened"]:
            raise ValueError(
                f"Alerta {alert_id} tiene status '{alert['status']}'. "
                f"Solo se pueden remediar alertas con status 'open' o 'reopened'"
            )
        
        now = datetime.now(timezone.utc)
        
        # 3. Crear documento de remediación
        remediation_doc = {
            "remediation_id": self._generate_remediation_id(),
            "alert_id": alert_id,
            "user_id": user_id,
            "team_id": team_id,
            "type": remediation_type,
            "status": "pending",  # Esperando verificación
            "action_ts": now,
            "notes": notes or "",
            "metadata": metadata or {},
            "created_at": now,
            "updated_at": now
        }
        
        # 4. Insertar en MongoDB
        result = await self.collection.insert_one(remediation_doc)
        remediation_doc["_id"] = str(result.inserted_id)
        
        # 5. Actualizar status de la alerta a "pending_verification"
        await self.alert_service.update_status(
            alert_id,
            "pending_verification",
            event_metadata={
                "remediation_id": remediation_doc["remediation_id"],
                "user_id": user_id,
                "type": remediation_type
            }
        )
        
        # 6. Disparar rescan automático si está habilitado
        if auto_trigger_rescan:
            try:
                # Usar RescanService para verificar si la vulnerabilidad aún existe
                rescan_result = await self.rescan_service.check_alert_exists(
                    alert_id=alert_id,
                    local_reopen_count=alert.get("reopen_count", 0),
                    remediation_id=remediation_doc["remediation_id"]
                )
                
                # 7. Procesar resultado del rescan (INVOCA GAMIFICATIONSERVICE)
                gamification_result = await self.process_rescan_result(
                    remediation_doc,
                    rescan_result.to_dict()
                )
                
                remediation_doc["rescan_triggered"] = True
                remediation_doc["rescan_result"] = rescan_result.to_dict()
                remediation_doc["gamification_result"] = gamification_result
                
            except Exception as e:
                logger.error(f"Error al disparar rescan automático: {e}")
                remediation_doc["rescan_triggered"] = False
                remediation_doc["rescan_error"] = str(e)
        else:
            remediation_doc["rescan_triggered"] = False
        
        return remediation_doc
    
    async def process_rescan_result(
        self,
        remediation: Dict[str, Any],
        rescan_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Procesar resultado de rescan e INVOCAR AL GAMIFICATIONSERVICE.
        
        🎯 AQUÍ ES DONDE SUCEDE LA MAGIA 🎯
        
        Este método:
        1. Obtiene la alerta completa
        2. Construye el contexto para el RuleEngine
        3. Invoca GamificationService.process_event("rescan_completed")
        4. El RuleEngine evalúa reglas y otorga puntos/penalizaciones
        5. Actualiza estados según el resultado
        
        Args:
            remediation: Dict con la remediación
            rescan_result: Dict con resultado del rescan
            
        Returns:
            Resultado del RuleEngine (puntos otorgados, badges, etc.)
        """
        # 1. Obtener alerta completa
        alert = await self.alert_service.get_alert(remediation["alert_id"])
        if not alert:
            raise ValueError(f"Alerta {remediation['alert_id']} no encontrada")
        
        # 2. Construir contexto para el RuleEngine
        context = {
            "Alert": alert,
            "Remediation": remediation,
            "RescanResult": rescan_result,
            "current_time": datetime.now(timezone.utc)
        }
        
        # 3. INVOCAR AL GAMIFICATIONSERVICE → RULEENGINE 🔥
        result = await self.gamification_service.process_event("rescan_completed", context)
        
        if not result or not isinstance(result, dict):
            raise ValueError("GamificationService returned invalid result")
        
        # 4. Determinar nuevos estados según resultado del rescan
        if rescan_result["still_exists"]:
            # Vulnerabilidad AÚN EXISTE = Falsa remediación
            new_remediation_status = "failed_verification"
            new_alert_status = "verified_persists"
        else:
            # Vulnerabilidad NO EXISTE = Remediación exitosa
            new_remediation_status = "verified_success"
            new_alert_status = "verified_resolved"
        
        # 5. Actualizar remediación
        await self.collection.update_one(
            {"remediation_id": remediation["remediation_id"]},
            {
                "$set": {
                    "status": new_remediation_status,
                    "verification_ts": datetime.now(timezone.utc),
                    "rescan_result": rescan_result,
                    "gamification_result": {
                        "rules_triggered": result["rules_triggered"],
                        "points_awarded": result["points_awarded"],
                        "penalties_applied": result["penalties_applied"],
                        "badges_awarded": result["badges_awarded"]
                    },
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        # 6. Actualizar alerta
        await self.alert_service.update_status(
            alert["alert_id"],
            new_alert_status,
            event_metadata={
                "remediation_id": remediation["remediation_id"],
                "still_exists": rescan_result["still_exists"],
                "reopen_count_changed": rescan_result["reopen_count_changed"],
                "rules_triggered": result["rules_triggered"]
            }
        )

        # 7. Si la vulnerabilidad reapareció, disparar evento alert_reopened para PEN-003
        if rescan_result.get("reopen_count_changed"):
            try:
                updated_alert = await self.alert_service.get_alert(alert["alert_id"])
                reopened_context = {
                    "Alert": updated_alert or alert,
                    "Remediation": remediation,
                    "RescanResult": rescan_result,
                    "current_time": datetime.now(timezone.utc),
                }
                await self.gamification_service.process_event("alert_reopened", reopened_context)
                logger.info(
                    f"Evento alert_reopened disparado para alerta {alert['alert_id']}"
                )
            except Exception as e:
                logger.error(f"Error disparando evento alert_reopened: {e}")

        # 8. Notificar a Discord el resultado de la remediación
        await self._send_remediation_notification(alert, remediation, rescan_result, result)

        logger.info(
            f"Remediación {remediation['remediation_id']} procesada: "
            f"status={new_remediation_status}, "
            f"rules_triggered={result['rules_triggered']}, "
            f"points_awarded={len(result['points_awarded'])}"
        )
        
        return result
    
    async def get_remediation(self, remediation_id: str) -> Optional[Dict[str, Any]]:
        """Obtener una remediación por ID"""
        remediation = await self.collection.find_one({"remediation_id": remediation_id})
        if remediation:
            remediation["_id"] = str(remediation["_id"])
        return remediation
    
    async def get_remediations_by_alert(self, alert_id: str) -> List[Dict[str, Any]]:
        """
        Obtener todas las remediaciones de una alerta.
        Útil para ver historial de intentos.
        """
        remediations = await self.collection.find(
            {"alert_id": alert_id}
        ).sort("action_ts", -1).to_list(length=None)
        
        for rem in remediations:
            rem["_id"] = str(rem["_id"])
        
        return remediations
    
    async def get_remediations_by_user(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Obtener remediaciones de un usuario"""
        query = {"user_id": user_id}
        if status:
            query["status"] = status
        
        remediations = await self.collection.find(query).sort("action_ts", -1).limit(limit).to_list(length=limit)
        
        for rem in remediations:
            rem["_id"] = str(rem["_id"])
        
        return remediations
    
    async def get_pending_remediations(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Obtener remediaciones pendientes de verificación.
        Útil para el timeout checker.
        """
        remediations = await self.collection.find(
            {"status": "pending"}
        ).sort("action_ts", 1).limit(limit).to_list(length=limit)
        
        for rem in remediations:
            rem["_id"] = str(rem["_id"])
        
        return remediations
    
    async def trigger_rescan_for_remediation(
        self,
        remediation_id: str,
        triggered_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Disparar rescan manualmente para una remediación existente.
        
        Útil para:
        - Re-verificar una remediación fallida
        - Verificar una remediación que quedó pendiente
        
        Returns:
            Resultado del RuleEngine después de procesar el rescan
        """
        remediation = await self.get_remediation(remediation_id)
        if not remediation:
            raise ValueError(f"Remediación {remediation_id} no encontrada")
        
        # Obtener alerta para acceder al reopen_count
        alert = await self.alert_service.get_alert(remediation["alert_id"])
        if not alert:
            raise ValueError(f"Alerta {remediation['alert_id']} no encontrada")
        
        # Disparar rescan usando RescanService
        rescan_result = await self.rescan_service.check_alert_exists(
            alert_id=alert["alert_id"],
            local_reopen_count=alert.get("reopen_count", 0)
        )
        
        # Procesar resultado con GamificationService
        return await self.process_rescan_result(remediation, rescan_result.to_dict())
    
    async def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas de remediaciones"""
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "total": {"$sum": 1},
                    "pending": {
                        "$sum": {"$cond": [{"$eq": ["$status", "pending"]}, 1, 0]}
                    },
                    "verified_success": {
                        "$sum": {"$cond": [{"$eq": ["$status", "verified_success"]}, 1, 0]}
                    },
                    "failed_verification": {
                        "$sum": {"$cond": [{"$eq": ["$status", "failed_verification"]}, 1, 0]}
                    }
                }
            }
        ]
        
        result = await self.collection.aggregate(pipeline).to_list(length=1)
        
        if result:
            stats = result[0]
            stats.pop("_id", None)
            
            # Calcular tasas
            total = stats["total"]
            if total > 0:
                stats["success_rate"] = round(
                    (stats["verified_success"] / total) * 100, 2
                )
                stats["failure_rate"] = round(
                    (stats["failed_verification"] / total) * 100, 2
                )
            else:
                stats["success_rate"] = 0.0
                stats["failure_rate"] = 0.0
            
            return stats
        
        return {
            "total": 0,
            "pending": 0,
            "verified_success": 0,
            "failed_verification": 0,
            "success_rate": 0.0,
            "failure_rate": 0.0
        }
    
    def _generate_remediation_id(self) -> str:
        """Generar ID único para remediación"""
        return f"rem_{uuid4().hex[:12]}"

    async def _send_remediation_notification(
        self,
        alert: Dict[str, Any],
        remediation: Dict[str, Any],
        rescan_result: Dict[str, Any],
        gamification_result: Dict[str, Any],
    ) -> None:
        """
        Envía notificación Discord con el resultado de la verificación.

        Construye objetos Alert y Remediation Pydantic para NotificationService.
        Los errores de notificación se logean pero no bloquean el flujo principal.
        """
        try:
            alert_obj = Alert(**{k: v for k, v in alert.items() if k != "_id"})
            remediation_obj = Remediation(
                **{
                    k: v
                    for k, v in remediation.items()
                    if k != "_id"
                }
            )

            if rescan_result.get("still_exists"):
                # Penalización: vulnerabilidad persiste
                penalty_points = sum(
                    p.get("points", 0) for p in gamification_result.get("penalties_applied", [])
                )
                await notification_service.notify_remediation_failed(
                    alert_obj, remediation_obj, penalty_points
                )
            else:
                # Recompensa: remediación exitosa
                points_earned = sum(
                    p.get("points", 0) for p in gamification_result.get("points_awarded", [])
                )
                await notification_service.notify_remediation_verified(
                    alert_obj, remediation_obj, points_earned
                )
        except Exception as e:
            logger.error(f"Error enviando notificación de remediación: {e}")


# Singleton global
_remediation_service_instance = None


def get_remediation_service() -> RemediationService:
    """Factory function para obtener instancia única del servicio"""
    global _remediation_service_instance
    if _remediation_service_instance is None:
        _remediation_service_instance = RemediationService()
    return _remediation_service_instance