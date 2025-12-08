"""
ActionExecutor - Ejecuta acciones definidas en reglas

Responsabilidades:
- Crear transacciones de puntos (PointTxn)
- Aplicar side effects (actualizar estados de entidades)
- Disparar eventos secundarios (evaluación de badges)
- Registrar evidencia en el ledger inmutable
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4


class ActionExecutor:
    """
    Ejecuta acciones definidas en reglas aplicables
    
    Usage:
        executor = ActionExecutor(db_session, point_calculator)
        
        result = await executor.execute_action(
            rule=rule,
            context=context,
            calculated_points=150
        )
    """
    
    def __init__(self, db_client, point_calculator):
        """
        Args:
            db_client: Cliente de base de datos (Motor para MongoDB)
            point_calculator: Instancia de PointCalculator
        """
        self.db = db_client
        self.point_calculator = point_calculator
    
    async def execute_point_award(
        self,
        rule_id: str,
        user_id: str,
        team_id: Optional[str],
        points: int,
        reason: str,
        evidence: List[str],
        context: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta otorgamiento de puntos
        
        Args:
            rule_id: ID de la regla que se dispara
            user_id: ID del usuario receptor
            team_id: ID del equipo (opcional, lo ignoramos por ahora)
            points: Puntos a otorgar (pueden ser negativos)
            reason: Razón legible para humanos
            evidence: Lista de IDs de evidencia (alert_id, rescan_id, etc.)
            context: Contexto con entidades involucradas
            metadata: Metadata adicional
        
        Returns:
            Dict con la transacción creada
        """
        # Construir transacción de puntos
        txn = {
            "txn_id": str(uuid4()),
            "user_id": user_id,
            "team_id": team_id,
            "rule_id": rule_id,
            "alert_id": context.get("Alert", {}).get("alert_id") if "Alert" in context else None,
            "points": points,
            "reason": reason,
            "timestamp": datetime.utcnow(),
            "evidence_refs": self._resolve_evidence(evidence, context),
            "penalty_reason": metadata.get("penalty_reason") if metadata else None,
            "original_alert_status": metadata.get("original_alert_status") if metadata else None,
            "metadata": metadata or {}
        }
        
        # Persistir en BD
        result = await self.db.point_transactions.insert_one(txn)
        
        # Evento secundario: evaluar badges
        # (esto se manejará en el RuleEngine principal)
        
        return {
            "txn_id": txn["txn_id"],
            "points": points,
            "user_id": user_id,
            "reason": reason
        }
    
    async def execute_penalty(
        self,
        rule_id: str,
        user_id: str,
        team_id: Optional[str],
        points: int,
        reason: str,
        penalty_reason: str,
        original_alert_status: str,
        evidence: List[str],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Ejecuta penalización (puntos negativos)
        
        Args:
            rule_id: ID de la regla de penalización
            user_id: Usuario penalizado
            team_id: Equipo (opcional)
            points: Puntos negativos
            reason: Razón de la penalización
            penalty_reason: Código de penalización (timeout, false_positive_mark, etc.)
            original_alert_status: Estado original de la alerta antes de penalización
            evidence: Evidencia
            context: Contexto
        
        Returns:
            Dict con la transacción creada
        """
        metadata = {
            "penalty_reason": penalty_reason,
            "original_alert_status": original_alert_status
        }
        
        return await self.execute_point_award(
            rule_id=rule_id,
            user_id=user_id,
            team_id=team_id,
            points=points,  # Ya debería ser negativo
            reason=reason,
            evidence=evidence,
            context=context,
            metadata=metadata
        )
    
    async def execute_side_effects(
        self,
        side_effects: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Ejecuta efectos secundarios definidos en una regla
        
        Args:
            side_effects: Lista de side effects desde la regla
            context: Contexto con entidades
        
        Returns:
            Lista de resultados de cada side effect
        """
        results = []
        
        for effect in side_effects:
            if "update_alert" in effect:
                result = await self._update_alert(effect["update_alert"], context)
                results.append({"type": "update_alert", "result": result})
            
            elif "update_remediation" in effect:
                result = await self._update_remediation(effect["update_remediation"], context)
                results.append({"type": "update_remediation", "result": result})
            
            elif "create_notification" in effect:
                result = await self._create_notification(effect["create_notification"], context)
                results.append({"type": "create_notification", "result": result})
        
        return results
    
    async def _update_alert(
        self,
        update_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Actualiza estado de una alerta
        
        Args:
            update_config: Configuración del update
                {
                    "alert_id": "Alert.alert_id",
                    "new_status": "verified_persists",
                    "notes": "Rescan confirmó..."
                }
            context: Contexto con entidades
        """
        alert_id = self._resolve_value(update_config.get("alert_id"), context)
        new_status = update_config.get("new_status")
        notes = update_config.get("notes", "")
        
        update_data = {
            "status": new_status,
            "updated_at": datetime.utcnow()
        }
        
        # Agregar nota a lifecycle_history si existe
        if notes:
            lifecycle_entry = {
                "status": new_status,
                "timestamp": datetime.utcnow(),
                "notes": notes
            }
            update_data["$push"] = {"lifecycle_history": lifecycle_entry}
        
        result = await self.db.alerts.update_one(
            {"alert_id": alert_id},
            {"$set": update_data} if "$push" not in update_data else {
                "$set": {k: v for k, v in update_data.items() if k != "$push"},
                **{"$push": update_data["$push"]}
            }
        )
        
        return {
            "alert_id": alert_id,
            "matched": result.matched_count,
            "modified": result.modified_count
        }
    
    async def _update_remediation(
        self,
        update_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Actualiza estado de una remediación"""
        remediation_id = self._resolve_value(update_config.get("remediation_id"), context)
        new_status = update_config.get("new_status")
        
        result = await self.db.remediations.update_one(
            {"remediation_id": remediation_id},
            {
                "$set": {
                    "status": new_status,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return {
            "remediation_id": remediation_id,
            "matched": result.matched_count,
            "modified": result.modified_count
        }
    
    async def _create_notification(
        self,
        notification_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Crea una notificación (para ser procesada por NotificationService)
        """
        target = self._resolve_value(notification_config.get("target"), context)
        message = notification_config.get("message", "")
        priority = notification_config.get("priority", "normal")
        
        notification = {
            "notification_id": str(uuid4()),
            "target_user_id": target,
            "message": message,
            "priority": priority,
            "status": "pending",
            "created_at": datetime.utcnow()
        }
        
        result = await self.db.notifications.insert_one(notification)
        
        return {
            "notification_id": notification["notification_id"],
            "inserted": bool(result.inserted_id)
        }
    
    def _resolve_evidence(
        self,
        evidence_list: List[str],
        context: Dict[str, Any]
    ) -> List[str]:
        """
        Resuelve referencias de evidencia desde el contexto
        
        Args:
            evidence_list: Lista de referencias (ej: ["Alert.alert_id", "RescanResult.rescan_id"])
            context: Contexto con entidades
        
        Returns:
            Lista de valores resueltos
        """
        resolved = []
        
        for evidence_ref in evidence_list:
            value = self._resolve_value(evidence_ref, context)
            if value is not None:
                resolved.append(str(value))
        
        return resolved
    
    def _resolve_value(self, expr: str, context: Dict[str, Any]) -> Any:
        """
        Resuelve un valor desde el contexto
        Similar a ConditionEvaluator._resolve_reference
        """
        if not expr or not isinstance(expr, str):
            return expr
        
        # Si no tiene punto, es un literal
        if "." not in expr:
            return expr
        
        parts = expr.split(".")
        entity_name = parts[0]
        
        if entity_name not in context:
            return None
        
        obj = context[entity_name]
        
        for part in parts[1:]:
            if obj is None:
                return None
            
            if isinstance(obj, dict):
                obj = obj.get(part)
            else:
                obj = getattr(obj, part, None)
        
        return obj