"""
RuleEngine - Orquestador principal del motor de reglas

Responsabilidades:
- Recibir eventos del sistema
- Seleccionar reglas aplicables
- Evaluar condiciones
- Ejecutar acciones
- Disparar evaluaciones de badges

Este es el corazón del sistema de gamificación verificada.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

from app.engines.rule_engine.loader import RuleLoader, get_rule_loader
from app.engines.rule_engine.condition_evaluator import ConditionEvaluator
from app.engines.rule_engine.action_executor import ActionExecutor
from app.engines.rule_engine.point_calculator import PointCalculator
from app.engines.rule_engine.badge_evaluator import BadgeEvaluator


class RuleEngine:
    """
    Motor de reglas que evalúa condiciones y ejecuta acciones
    
    Usage:
        engine = RuleEngine(db_client)
        
        # Procesar evento de rescan completado
        result = await engine.process_event(
            event_name="rescan_completed",
            context={
                "Alert": alert,
                "Remediation": remediation,
                "RescanResult": rescan_result
            }
        )
    """
    
    def __init__(self, db_client, rule_loader: Optional[RuleLoader] = None):
        """
        Args:
            db_client: Cliente de base de datos (Motor para MongoDB)
            rule_loader: Instancia de RuleLoader (opcional, usa singleton si None)
        """
        self.db = db_client
        self.rule_loader = rule_loader or get_rule_loader()
        
        # Configuración desde rules.yaml
        self.config = self.rule_loader.get_config()
        
        # Inicializar componentes
        self.point_calculator = PointCalculator(
            min_points=self.config.point_system.get("min_points", 0),
            allow_negative=self.config.point_system.get("allow_negative", True)
        )
        
        self.action_executor = ActionExecutor(db_client, self.point_calculator)
        self.badge_evaluator = BadgeEvaluator(db_client)
    
    async def process_event(
        self,
        event_name: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Procesa un evento del sistema
        
        Args:
            event_name: Nombre del evento ("rescan_completed", "grace_period_expired", etc.)
            context: Contexto con entidades involucradas
                     Ejemplo: {"Alert": alert_obj, "Remediation": rem_obj, "RescanResult": rescan_obj}
        
        Returns:
            Dict con resultados:
                {
                    "rules_evaluated": int,
                    "rules_triggered": int,
                    "points_awarded": List[dict],
                    "penalties_applied": List[dict],
                    "badges_awarded": List[dict],
                    "exclusions": List[dict]
                }
        """
        results: Dict[str, Any] = {
            "event_name": event_name,
            "rules_evaluated": 0,
            "rules_triggered": 0,
            "points_awarded": [],
            "penalties_applied": [],
            "badges_awarded": [],
            "exclusions": []
        }
        
        # Fase 1: Verificar reglas de exclusión
        if self._should_exclude(context):
            results["exclusions"].append({
                "reason": "Event excluded by exclusion rules",
                "timestamp": datetime.now(timezone.utc)
            })
            return results
        
        # Fase 2: Obtener reglas aplicables por evento
        applicable_rules = self.rule_loader.get_rules_by_event(event_name)
        results["rules_evaluated"] = len(applicable_rules)
        
        # Fase 3: Evaluar cada regla
        for rule in applicable_rules:
            try:
                triggered = await self._evaluate_and_execute_rule(rule, context, results)
                if triggered:
                    results["rules_triggered"] += 1
            except Exception as e:
                print(f"❌ Error evaluating rule {rule.rule_id}: {e}")
        
        # Fase 4: Evaluar badges si hubo cambios en puntos
        if results["points_awarded"] or results["penalties_applied"]:
            user_ids: Set[str] = set()
            
            for award in results["points_awarded"]:
                if "user_id" in award:
                    user_ids.add(award["user_id"])
            
            for penalty in results["penalties_applied"]:
                if "user_id" in penalty:
                    user_ids.add(penalty["user_id"])
            
            # Evaluar badges para usuarios afectados
            for user_id in user_ids:
                badges = await self.badge_evaluator.evaluate_user_badges(user_id)
                results["badges_awarded"].extend(badges)
        
        return results
    
    async def _evaluate_and_execute_rule(
        self,
        rule: Any,
        context: Dict[str, Any],
        results: Dict[str, Any]
    ) -> bool:
        """
        Evalúa una regla y ejecuta su acción si aplica
        
        Returns:
            True si la regla se disparó, False caso contrario
        """
        # Crear evaluador de condiciones
        evaluator = ConditionEvaluator(context)
        
        # Evaluar condiciones del trigger
        conditions_met = evaluator.evaluate_all(rule.trigger.conditions, operator="AND")
        
        if not conditions_met:
            return False
        
        # Regla aplicable - ejecutar acción
        if rule.type == "points":
            await self._execute_point_rule(rule, context, results)
        
        elif rule.type == "penalty":
            await self._execute_penalty_rule(rule, context, results)
        
        return True
    
    async def _execute_point_rule(
        self,
        rule: Any,
        context: Dict[str, Any],
        results: Dict[str, Any]
    ) -> None:
        """Ejecuta una regla de otorgamiento de puntos"""
        action = rule.action
        
        # Resolver usuario receptor
        user_id = self._resolve_recipient(action.recipient, context)
        
        if not user_id:
            return
        
        # Obtener nivel del usuario y calcular puntos con multiplicador
        user_level = await self._get_user_level(user_id)
        final_points = self.point_calculator.calculate_from_rule(
            rule_points=action.points,
            user_level=user_level
        )
        
        # Ejecutar otorgamiento
        txn = await self.action_executor.execute_point_award(
            rule_id=rule.rule_id,
            user_id=user_id,
            team_id=context.get("Remediation", {}).get("team_id") if "Remediation" in context else None,
            points=final_points,
            reason=action.reason,
            evidence=action.evidence,
            context=context,
            metadata=rule.metadata if hasattr(rule, 'metadata') else {}
        )
        
        results["points_awarded"].append(txn)
    
    async def _execute_penalty_rule(
        self,
        rule: Any,
        context: Dict[str, Any],
        results: Dict[str, Any]
    ) -> None:
        """Ejecuta una regla de penalización"""
        action = rule.action
        
        # Resolver usuario penalizado
        user_id = self._resolve_recipient(action.recipient, context)
        
        if not user_id:
            return
        
        # Ejecutar penalización
        txn = await self.action_executor.execute_penalty(
            rule_id=rule.rule_id,
            user_id=user_id,
            team_id=context.get("Remediation", {}).get("team_id") if "Remediation" in context else None,
            points=action.points,  # Ya negativo
            reason=action.reason,
            penalty_reason=action.penalty_reason or "unspecified",
            original_alert_status=action.original_alert_status or "unknown",
            evidence=action.evidence,
            context=context
        )
        
        results["penalties_applied"].append(txn)
        
        # Ejecutar side effects
        if hasattr(rule, 'side_effects') and rule.side_effects:
            await self.action_executor.execute_side_effects(
                rule.side_effects,
                context
            )
    
    def _should_exclude(self, context: Dict[str, Any]) -> bool:
        """
        Verifica si el evento debe ser excluido por reglas de exclusión
        
        Returns:
            True si debe excluirse, False caso contrario
        """
        exclusion_rules = self.rule_loader.get_rules_by_type("exclusion")
        
        for rule in exclusion_rules:
            evaluator = ConditionEvaluator(context)
            
            if evaluator.evaluate_all(rule.conditions, operator="AND"):
                # Cumple condiciones de exclusión
                return True
        
        return False
    
    def _resolve_recipient(self, recipient_expr: str, context: Dict[str, Any]) -> Optional[str]:
        """
        Resuelve el usuario receptor desde una expresión
        
        Args:
            recipient_expr: Expresión como "Remediation.user_id"
            context: Contexto con entidades
        
        Returns:
            user_id o None
        """
        if not recipient_expr:
            return None
        
        parts = recipient_expr.split(".")
        
        if len(parts) < 2:
            return None
        
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
        
        return str(obj) if obj else None
    
    async def _get_user_level(self, user_id: str) -> int:
        """
        Obtiene el nivel actual de un usuario
        
        Args:
            user_id: ID del usuario
        
        Returns:
            Nivel (1-5)
        """
        # Calcular balance total de puntos
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": None, "total": {"$sum": "$points"}}}
        ]
        
        result = await self.db.point_transactions.aggregate(pipeline).to_list(length=1)
        total_points = result[0]["total"] if result else 0
        
        # Calcular nivel
        return self.point_calculator.calculate_user_level(total_points)
    
    async def calculate_user_balance(self, user_id: str) -> Dict[str, Any]:
        """
        Calcula el balance completo de un usuario
        
        Args:
            user_id: ID del usuario
        
        Returns:
            Dict con total_points, level, progress_to_next_level, etc.
        """
        # Agregación para calcular balance
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": None,
                "total_points": {"$sum": "$points"},
                "positive_points": {
                    "$sum": {"$cond": [{"$gt": ["$points", 0]}, "$points", 0]}
                },
                "negative_points": {
                    "$sum": {"$cond": [{"$lt": ["$points", 0]}, "$points", 0]}
                },
                "transaction_count": {"$sum": 1}
            }}
        ]
        
        result = await self.db.point_transactions.aggregate(pipeline).to_list(length=1)
        
        if not result:
            return {
                "user_id": user_id,
                "total_points": 0,
                "level": 1,
                "level_name": "Aprendiz de Seguridad",
                "progress_to_next_level": {
                    "current_level": 1,
                    "next_level": 2,
                    "points_needed": 500,
                    "progress_percentage": 0.0
                }
            }
        
        stats = result[0]
        total_points = stats["total_points"]
        
        # Calcular nivel y progreso
        level = self.point_calculator.calculate_user_level(total_points)
        level_info = self.point_calculator.get_level_info(level)
        progress = self.point_calculator.calculate_progress_to_next_level(total_points)
        
        return {
            "user_id": user_id,
            "total_points": total_points,
            "positive_points": stats["positive_points"],
            "negative_points": stats["negative_points"],
            "transaction_count": stats["transaction_count"],
            "level": level,
            "level_name": level_info["name"],
            "level_perks": level_info["perks"],
            "progress_to_next_level": progress
        }


# ============================================================================
# HELPER FUNCTION
# ============================================================================

async def process_remediation_verified(
    db_client,
    alert: Dict[str, Any],
    remediation: Dict[str, Any],
    rescan_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Helper para procesar remediación verificada
    
    Usage:
        result = await process_remediation_verified(
            db_client=db,
            alert=alert_doc,
            remediation=remediation_doc,
            rescan_result=rescan_doc
        )
    """
    engine = RuleEngine(db_client)
    
    context = {
        "Alert": alert,
        "Remediation": remediation,
        "RescanResult": rescan_result,
        "current_time": datetime.utcnow()
    }
    
    return await engine.process_event("rescan_completed", context)