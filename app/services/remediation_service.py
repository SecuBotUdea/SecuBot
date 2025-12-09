"""
RemediationService - Gestión de remediaciones y orquestación con RuleEngine

⭐ SERVICIO CRÍTICO ⭐
Este es el corazón del sistema de gamificación verificada.

Responsabilidades:
- Registrar cuando un usuario marca una alerta como resuelta
- Coordinar con rescan_service para verificar la remediación
- INVOCAR AL RULEENGINE después del rescan (AQUÍ PASA LA MAGIA 🎯)
- Manejar penalizaciones por timeouts
- Gestionar reaperturas de alertas

Flujo completo:
1. Usuario dice "Resolví esta vulnerabilidad"
2. create_remediation() → guarda en BD con status="pending"
3. Dispara rescan automático
4. process_rescan_result() → INVOCA RULEENGINE 🔥
5. RuleEngine otorga puntos o penaliza
6. Actualiza estados de alert y remediation
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from uuid import uuid4

from app.database.mongodb import get_database
from app.services.alert_service import get_alert_service
from app.services.rescan_service import get_rescan_service
from app.engines.rule_engine import RuleEngine
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RemediationService:
    """
    Servicio principal para gestión de remediaciones.
    
    Este servicio es el PUENTE entre:
    - Las acciones del usuario (marcar como resuelta)
    - El rescan de verificación
    - El RuleEngine (gamificación)
    """
    
    def __init__(self):
        self.db = get_database()
        self.collection = self.db.remediations
        self.alert_service = get_alert_service()
        self.rescan_service = get_rescan_service(demo_mode=True)
    
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
            ValueError: Si la alerta no existe
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
                rescan_result = await self.rescan_service.trigger_rescan(
                    alert_id,
                    triggered_by=user_id
                )
                
                # 7. Procesar resultado del rescan (INVOCA RULEENGINE)
                gamification_result = await self.process_rescan_result(
                    remediation_doc,
                    rescan_result.to_dict()
                )
                
                remediation_doc["rescan_triggered"] = True
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
        Procesar resultado de rescan e INVOCAR AL RULEENGINE.
        
        🎯 AQUÍ ES DONDE SUCEDE LA MAGIA 🎯
        
        Este método:
        1. Obtiene la alerta y la remediación
        2. Construye el contexto para el RuleEngine
        3. Invoca RuleEngine.process_event("rescan_completed")
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
        
        # 3. INVOCAR AL RULEENGINE 🔥
        engine = RuleEngine(self.db)
        result = await engine.process_event("rescan_completed", context)
        
        if not result or not isinstance(result, dict):
            raise ValueError("RuleEngine returned invalid result")
        
        # 4. Actualizar estado de la remediación según resultado
        if rescan_result["present"]:
            # Vulnerabilidad AÚN PRESENTE = Falsa remediación
            new_status = "failed_verification"
            alert_new_status = "verified_persists"
        else:
            # Vulnerabilidad AUSENTE = Remediación exitosa
            new_status = "verified_success"
            alert_new_status = "verified_resolved"
        
        # 5. Actualizar remediación
        await self.collection.update_one(
            {"remediation_id": remediation["remediation_id"]},
            {
                "$set": {
                    "status": new_status,
                    "verification_ts": datetime.now(timezone.utc),
                    "rescan_result_ref": rescan_result.get("_id"),
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        # 6. Actualizar alerta
        await self.alert_service.update_status(
            alert["alert_id"],
            alert_new_status,
            event_metadata={
                "remediation_id": remediation["remediation_id"],
                "rescan_present": rescan_result["present"],
                "rules_triggered": result["rules_triggered"]
            }
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
        cursor = self.collection.find(
            {"alert_id": alert_id}
        ).sort("action_ts", -1)
        
        remediations = []
        async for rem in cursor:
            rem["_id"] = str(rem["_id"])
            remediations.append(rem)
        
        return remediations
    
    async def get_remediations_by_user(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Obtener remediaciones de un usuario.
        """
        query = {"user_id": user_id}
        if status:
            query["status"] = status
        
        cursor = self.collection.find(query).sort("action_ts", -1).limit(limit)
        
        remediations = []
        async for rem in cursor:
            rem["_id"] = str(rem["_id"])
            remediations.append(rem)
        
        return remediations
    
    async def get_pending_remediations(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Obtener remediaciones pendientes de verificación.
        Útil para el timeout checker (Fase 5).
        """
        cursor = self.collection.find(
            {"status": "pending"}
        ).sort("action_ts", 1).limit(limit)  # Más antiguas primero
        
        remediations = []
        async for rem in cursor:
            rem["_id"] = str(rem["_id"])
            remediations.append(rem)
        
        return remediations
    
    async def manual_verify_remediation(
        self,
        remediation_id: str,
        verified_by: str,
        success: bool,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verificación manual de remediación (sin rescan).
        Para casos especiales donde el admin verifica manualmente.
        
        Args:
            remediation_id: ID de la remediación
            verified_by: ID del admin que verifica
            success: True si fue exitosa, False si falló
            notes: Notas de la verificación
            
        Returns:
            Remediación actualizada
        """
        remediation = await self.get_remediation(remediation_id)
        if not remediation:
            raise ValueError(f"Remediación {remediation_id} no encontrada")
        
        new_status = "verified_success" if success else "failed_verification"
        
        # Actualizar remediación
        await self.collection.update_one(
            {"remediation_id": remediation_id},
            {
                "$set": {
                    "status": new_status,
                    "verification_ts": datetime.now(timezone.utc),
                    "verified_by": verified_by,
                    "verification_type": "manual",
                    "verification_notes": notes or "",
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        # Actualizar alerta
        alert_status = "verified_resolved" if success else "verified_persists"
        await self.alert_service.update_status(
            remediation["alert_id"],
            alert_status,
            event_metadata={
                "verification_type": "manual",
                "verified_by": verified_by
            }
        )
        
        # TODO: Disparar evento al RuleEngine si success=True
        # Para que otorgue puntos por remediación verificada manualmente
        
        updated_remediation = await self.get_remediation(remediation_id)
        if not updated_remediation:
            raise ValueError(f"Failed to retrieve updated remediation {remediation_id}")
        
        return updated_remediation
    
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
        
        # Disparar rescan
        rescan_result = await self.rescan_service.trigger_rescan(
            remediation["alert_id"],
            triggered_by=triggered_by or remediation["user_id"]
        )
        
        # Procesar resultado con RuleEngine
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
        
        cursor = self.collection.aggregate(pipeline)
        result = await cursor.to_list(length=None)
        
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


# Singleton global para uso en toda la aplicación
_remediation_service_instance = None


def get_remediation_service() -> RemediationService:
    """Factory function para obtener instancia única del servicio"""
    global _remediation_service_instance
    if _remediation_service_instance is None:
        _remediation_service_instance = RemediationService()
    return _remediation_service_instance