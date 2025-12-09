"""
Servicio de gamificación - Wrapper delgado del RuleEngine.
Provee queries convenientes y acceso simplificado al motor de reglas.

Responsable de:
- Exponer funcionalidad del RuleEngine de forma conveniente
- Proveer queries optimizadas para leaderboards
- Agregar datos de usuarios a resultados
- Manejar filtros por equipo/timeframe
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

from app.database.mongodb import get_database
from app.engines.rule_engine import RuleEngine, get_rule_loader
from app.utils.logger import get_logger

logger = get_logger(__name__)


class GamificationService:
    """
    Wrapper delgado del RuleEngine.
    Toda la lógica de negocio está en el RuleEngine.
    """

    def __init__(self):
        self.db = get_database()
        self.point_txns = self.db.point_transactions
        self.awards = self.db.awards
        self.users = self.db.users
        
        # RuleEngine maneja toda la lógica
        self.rule_engine = RuleEngine(self.db)
        self.rule_loader = get_rule_loader()

    # ========================================================================
    # WRAPPERS DIRECTOS DEL RULEENGINE
    # ========================================================================

    async def get_user_balance(self, user_id: str) -> Dict[str, Any]:
        """Wrapper de RuleEngine.calculate_user_balance()"""
        return await self.rule_engine.calculate_user_balance(user_id)

    async def process_event(self, event_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Wrapper de RuleEngine.process_event()"""
        return await self.rule_engine.process_event(event_name, context)

    async def evaluate_user_badges(self, user_id: str) -> List[Dict[str, Any]]:
        """Wrapper de BadgeEvaluator.evaluate_user_badges()"""
        return await self.rule_engine.badge_evaluator.evaluate_user_badges(user_id)

    # ========================================================================
    # QUERIES CONVENIENTES (NO DISPONIBLES EN RULEENGINE)
    # ========================================================================

    async def get_leaderboard(
        self,
        limit: int = 10,
        team_id: Optional[str] = None,
        timeframe: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Leaderboard con filtros de equipo/tiempo.
        Agrega datos de usuarios y niveles.
        """
        # Filtro de tiempo
        time_filter = {}
        if timeframe:
            now = datetime.now(timezone.utc)
            if timeframe == "daily":
                time_filter = {"timestamp": {"$gte": now - timedelta(days=1)}}
            elif timeframe == "weekly":
                time_filter = {"timestamp": {"$gte": now - timedelta(weeks=1)}}
            elif timeframe == "monthly":
                time_filter = {"timestamp": {"$gte": now - timedelta(days=30)}}
        
        # Agregación
        pipeline = [
            {"$match": time_filter},
            {"$group": {
                "_id": "$user_id",
                "total_points": {"$sum": "$points"},
                "transaction_count": {"$sum": 1}
            }},
            {"$sort": {"total_points": -1}},
            {"$limit": limit}
        ]
        
        results = await self.point_txns.aggregate(pipeline).to_list(length=None)
        
        # Enriquecer con datos de usuario y nivel
        leaderboard = []
        for i, entry in enumerate(results):
            user_id = entry["_id"]
            user = await self.users.find_one({"_id": user_id})
            
            # Filtrar por equipo
            if team_id and (not user or user.get("team_id") != team_id):
                continue
            
            # Obtener nivel (via RuleEngine)
            balance = await self.get_user_balance(user_id)
            
            leaderboard.append({
                "rank": i + 1,
                "user_id": user_id,
                "username": user.get("username") if user else "Unknown",
                "display_name": user.get("display_name") if user else "Unknown",
                "team_id": user.get("team_id") if user else None,
                "total_points": entry["total_points"],
                "level": balance["level"],
                "level_name": balance["level_name"],
                "transaction_count": entry["transaction_count"]
            })
        
        return leaderboard

    async def get_user_badges(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Query simple de badges de un usuario"""
        badges = await self.awards.find({"user_id": user_id}).sort("awarded_at", -1).limit(limit).to_list(length=limit)
        
        for badge in badges:
            badge["_id"] = str(badge["_id"])
        
        return badges

    async def get_badge_details(self, badge_id: str) -> Optional[Dict[str, Any]]:
        """Obtener definición de badge desde rules.yaml"""
        try:
            badge_rule = self.rule_loader.get_badge_by_id(badge_id) # type: ignore
            if not badge_rule:
                return None
            
            return {
                "badge_id": badge_rule.badge_id,
                "name": badge_rule.name,
                "description": badge_rule.description,
                "icon": badge_rule.icon,
                "tier": badge_rule.tier
            }
        except Exception as e:
            logger.error(f"Error obteniendo badge {badge_id}: {e}")
            return None

    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Estadísticas completas de un usuario.
        Combina balance (RuleEngine) + badges + transacciones recientes.
        """
        # Balance (via RuleEngine)
        balance = await self.get_user_balance(user_id)
        
        # Badges
        badges = await self.get_user_badges(user_id)
        badge_tiers = {"bronze": 0, "silver": 0, "gold": 0, "platinum": 0}
        for badge in badges:
            tier = badge.get("tier", "bronze")
            if tier in badge_tiers:
                badge_tiers[tier] += 1
        
        # Transacciones recientes
        recent_txns = await self.point_txns.find({"user_id": user_id}).sort("timestamp", -1).limit(5).to_list(length=5)
        for txn in recent_txns:
            txn["_id"] = str(txn["_id"])
        
        # Estadísticas de puntos
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": None,
                "total_earned": {"$sum": {"$cond": [{"$gt": ["$points", 0]}, "$points", 0]}},
                "total_lost": {"$sum": {"$cond": [{"$lt": ["$points", 0]}, "$points", 0]}},
                "max_single_gain": {"$max": "$points"}
            }}
        ]
        points_stats = await self.point_txns.aggregate(pipeline).to_list(length=1)
        stats = points_stats[0] if points_stats else {
            "total_earned": 0, "total_lost": 0, "max_single_gain": 0
        }
        stats.pop("_id", None)
        
        return {
            "user_id": user_id,
            "balance": balance,
            "badges": {
                "total_count": len(badges),
                "by_tier": badge_tiers,
                "recent": badges[:5]
            },
            "points_stats": stats,
            "recent_transactions": recent_txns
        }

    async def get_recent_activity(
        self,
        limit: int = 20,
        user_id: Optional[str] = None,
        team_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Actividad reciente: transacciones de puntos + badges otorgados"""
        activities = []
        query = {"user_id": user_id} if user_id else {}
        
        # Transacciones
        txns = await self.point_txns.find(query).sort("timestamp", -1).limit(limit // 2).to_list(length=limit // 2)
        for txn in txns:
            activities.append({
                "type": "points",
                "timestamp": txn["timestamp"],
                "user_id": txn["user_id"],
                "points": txn["points"],
                "reason": txn.get("reason", ""),
                "rule_id": txn.get("rule_id")
            })
        
        # Badges
        badges = await self.awards.find(query).sort("awarded_at", -1).limit(limit // 2).to_list(length=limit // 2)
        for badge in badges:
            activities.append({
                "type": "badge",
                "timestamp": badge["awarded_at"],
                "user_id": badge["user_id"],
                "badge_id": badge["badge_id"],
                "badge_name": badge.get("badge_name", badge["badge_id"])
            })
        
        # Ordenar y filtrar por equipo
        activities.sort(key=lambda x: x["timestamp"], reverse=True)
        
        if team_id:
            filtered = []
            for activity in activities[:limit]:
                user = await self.users.find_one({"_id": activity["user_id"]})
                if user and user.get("team_id") == team_id:
                    filtered.append(activity)
            return filtered
        
        return activities[:limit]

    async def get_available_rules(self) -> Dict[str, Any]:
        """Reglas disponibles desde rules.yaml"""
        return {
            "point_rules": [
                {"rule_id": r.rule_id, "name": r.name}
                for r in self.rule_loader.get_rules_by_type("points")
            ],
            "penalty_rules": [
                {"rule_id": r.rule_id, "name": r.name}
                for r in self.rule_loader.get_rules_by_type("penalty")
            ],
            "badge_rules": [
                {"badge_id": b.badge_id, "name": b.name, "tier": b.tier} # type: ignore
                for b in self.rule_loader.get_all_active_badges()
            ]
        }


# Singleton
_gamification_service_instance = None

def get_gamification_service() -> GamificationService:
    """Factory function para obtener instancia única del servicio"""
    global _gamification_service_instance
    if _gamification_service_instance is None:
        _gamification_service_instance = GamificationService()
    return _gamification_service_instance