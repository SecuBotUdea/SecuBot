# app/services/gamification_service.py
"""
Servicio de gamificación - Wrapper del RuleEngine.
Provee una API conveniente para consultas de gamificación.

Responsable de:
- Calcular balances de puntos de usuarios
- Generar leaderboards
- Consultar badges otorgados
- Obtener estadísticas de progresión
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from app.database.connection import get_database
# Importar el RuleEngine cuando esté disponible
# from app.rule_engine.point_calculator import PointCalculator
# from app.rule_engine.badge_evaluator import BadgeEvaluator


class GamificationService:
    """
    Servicio principal de gamificación.
    Wrapper del RuleEngine que provee queries optimizadas.
    """

    def __init__(self):
        self.db = get_database()
        self.point_txns = self.db.point_transactions
        self.awards = self.db.awards
        self.users = self.db.users
        
        # TODO: Inicializar componentes del RuleEngine cuando estén disponibles
        # self.point_calculator = PointCalculator()
        # self.badge_evaluator = BadgeEvaluator()
        
        self._ensure_indexes()

    def _ensure_indexes(self):
        """Crear índices para queries de gamificación"""
        try:
            # Índices para point_transactions
            self.point_txns.create_index("user_id")
            self.point_txns.create_index("timestamp")
            self.point_txns.create_index([("user_id", 1), ("timestamp", -1)])
            self.point_txns.create_index("points")
            self.point_txns.create_index("rule_id")
            
            # Índices para awards (badges)
            self.awards.create_index("user_id")
            self.awards.create_index("badge_id")
            self.awards.create_index("awarded_at")
            self.awards.create_index([("user_id", 1), ("awarded_at", -1)])
            
        except Exception as e:
            print(f"Advertencia al crear índices de gamificación: {e}")

    def get_user_balance(self, user_id: str) -> Dict[str, Any]:
        """
        Calcular el balance total de puntos de un usuario.
        
        Wrapper de RuleEngine.calculate_user_balance()
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Dict con balance, nivel, progreso y multiplicador
        """
        # TODO: Usar RuleEngine cuando esté disponible
        # return self.point_calculator.calculate_user_balance(user_id)
        
        # Implementación temporal directa
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": None,
                "total_points": {"$sum": "$points"},
                "transaction_count": {"$sum": 1}
            }}
        ]
        
        result = list(self.point_txns.aggregate(pipeline))
        
        if not result:
            return {
                "user_id": user_id,
                "total_points": 0,
                "level": 1,
                "level_name": "Novice",
                "progress_to_next_level": 0.0,
                "points_to_next_level": 100,
                "multiplier": 1.0,
                "transaction_count": 0
            }
        
        total_points = result[0]["total_points"]
        transaction_count = result[0]["transaction_count"]
        
        # Sistema de niveles (5 niveles)
        level_thresholds = [0, 100, 500, 2000, 5000]
        level_names = ["Novice", "Apprentice", "Expert", "Master", "Legend"]
        level_multipliers = [1.0, 1.1, 1.2, 1.3, 1.5]
        
        # Calcular nivel actual
        level = 1
        for i, threshold in enumerate(level_thresholds):
            if total_points >= threshold:
                level = i + 1
        
        # Calcular progreso hacia siguiente nivel
        if level < len(level_thresholds):
            current_threshold = level_thresholds[level - 1]
            next_threshold = level_thresholds[level]
            progress_points = total_points - current_threshold
            required_points = next_threshold - current_threshold
            progress_percentage = (progress_points / required_points) * 100
            points_to_next = next_threshold - total_points
        else:
            # Nivel máximo alcanzado
            progress_percentage = 100.0
            points_to_next = 0
        
        return {
            "user_id": user_id,
            "total_points": total_points,
            "level": level,
            "level_name": level_names[level - 1],
            "progress_to_next_level": round(progress_percentage, 2),
            "points_to_next_level": max(0, points_to_next),
            "multiplier": level_multipliers[level - 1],
            "transaction_count": transaction_count
        }

    def get_leaderboard(
        self,
        limit: int = 10,
        team_id: Optional[str] = None,
        timeframe: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtener el leaderboard global o por equipo.
        
        Args:
            limit: Número de usuarios a retornar
            team_id: Filtrar por equipo (opcional)
            timeframe: 'daily', 'weekly', 'monthly', 'all-time' (default: 'all-time')
            
        Returns:
            Lista de usuarios ordenados por puntos descendente
        """
        # Construir filtro de tiempo
        time_filter = {}
        if timeframe:
            now = datetime.now(timezone.utc)
            if timeframe == "daily":
                from datetime import timedelta
                time_filter = {"timestamp": {"$gte": now - timedelta(days=1)}}
            elif timeframe == "weekly":
                from datetime import timedelta
                time_filter = {"timestamp": {"$gte": now - timedelta(weeks=1)}}
            elif timeframe == "monthly":
                from datetime import timedelta
                time_filter = {"timestamp": {"$gte": now - timedelta(days=30)}}
        
        # Pipeline de agregación
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
        
        # Ejecutar agregación
        results = list(self.point_txns.aggregate(pipeline))
        
        # Enriquecer con datos de usuario
        leaderboard = []
        for i, entry in enumerate(results):
            user_id = entry["_id"]
            user = self.users.find_one({"_id": user_id})
            
            # Filtrar por equipo si se especificó
            if team_id and (not user or user.get("team_id") != team_id):
                continue
            
            # Calcular nivel
            balance = self.get_user_balance(user_id)
            
            leaderboard.append({
                "rank": i + 1,
                "user_id": user_id,
                "username": user.get("username") if user else "Unknown",
                "display_name": user.get("display_name") if user else "Unknown User",
                "team_id": user.get("team_id") if user else None,
                "total_points": entry["total_points"],
                "level": balance["level"],
                "level_name": balance["level_name"],
                "transaction_count": entry["transaction_count"]
            })
        
        return leaderboard

    def get_user_badges(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Obtener todos los badges otorgados a un usuario.
        
        Query simple a la colección awards.
        
        Args:
            user_id: ID del usuario
            limit: Máximo de badges a retornar
            
        Returns:
            Lista de badges ordenados por fecha de otorgamiento descendente
        """
        cursor = self.awards.find(
            {"user_id": user_id}
        ).sort("awarded_at", -1).limit(limit)
        
        badges = []
        for award in cursor:
            award["_id"] = str(award["_id"])
            badges.append(award)
        
        return badges

    def get_badge_details(self, badge_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtener detalles de un badge específico desde rules.yaml.
        
        TODO: Integrar con RuleEngine.rule_loader
        """
        # Placeholder - en producción leer desde rules.yaml
        badge_definitions = {
            "first_blood": {
                "badge_id": "first_blood",
                "name": "First Blood",
                "description": "Cerró su primera vulnerabilidad crítica",
                "icon": "🎯",
                "tier": "bronze"
            },
            "speed_demon": {
                "badge_id": "speed_demon",
                "name": "Speed Demon",
                "description": "Remediación en menos de 24 horas",
                "icon": "⚡",
                "tier": "silver"
            },
            "perfect_week": {
                "badge_id": "perfect_week",
                "name": "Perfect Week",
                "description": "7 días consecutivos sin vulnerabilidades abiertas",
                "icon": "🏆",
                "tier": "gold"
            }
        }
        
        return badge_definitions.get(badge_id)

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Obtener estadísticas completas de gamificación de un usuario.
        
        Combina balance, badges, y métricas adicionales.
        """
        # Balance de puntos
        balance = self.get_user_balance(user_id)
        
        # Badges
        badges = self.get_user_badges(user_id)
        badge_count = len(badges)
        
        # Badges por tier
        badge_tiers = {"bronze": 0, "silver": 0, "gold": 0, "platinum": 0}
        for badge in badges:
            tier = badge.get("tier", "bronze")
            if tier in badge_tiers:
                badge_tiers[tier] += 1
        
        # Transacciones recientes
        recent_txns = list(
            self.point_txns.find(
                {"user_id": user_id}
            ).sort("timestamp", -1).limit(5)
        )
        
        for txn in recent_txns:
            txn["_id"] = str(txn["_id"])
        
        # Estadísticas de puntos
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": None,
                "total_earned": {
                    "$sum": {"$cond": [{"$gt": ["$points", 0]}, "$points", 0]}
                },
                "total_lost": {
                    "$sum": {"$cond": [{"$lt": ["$points", 0]}, "$points", 0]}
                },
                "max_single_gain": {"$max": "$points"},
                "avg_gain": {"$avg": "$points"}
            }}
        ]
        
        points_stats = list(self.point_txns.aggregate(pipeline))
        
        if points_stats:
            stats = points_stats[0]
            stats.pop("_id", None)
        else:
            stats = {
                "total_earned": 0,
                "total_lost": 0,
                "max_single_gain": 0,
                "avg_gain": 0
            }
        
        return {
            "user_id": user_id,
            "balance": balance,
            "badges": {
                "total_count": badge_count,
                "by_tier": badge_tiers,
                "recent": badges[:5]  # 5 más recientes
            },
            "points_stats": stats,
            "recent_transactions": recent_txns
        }

    def get_global_stats(self) -> Dict[str, Any]:
        """
        Obtener estadísticas globales del sistema de gamificación.
        """
        # Total de puntos en circulación
        pipeline_points = [
            {"$group": {
                "_id": None,
                "total_points": {"$sum": "$points"},
                "total_transactions": {"$sum": 1},
                "unique_users": {"$addToSet": "$user_id"}
            }}
        ]
        
        points_result = list(self.point_txns.aggregate(pipeline_points))
        
        # Total de badges otorgados
        total_badges = self.awards.count_documents({})
        
        # Usuarios por nivel
        pipeline_levels = [
            {"$group": {
                "_id": "$user_id",
                "total_points": {"$sum": "$points"}
            }}
        ]
        
        user_points = list(self.point_txns.aggregate(pipeline_levels))
        
        levels_distribution = {
            "level_1": 0,
            "level_2": 0,
            "level_3": 0,
            "level_4": 0,
            "level_5": 0
        }
        
        level_thresholds = [0, 100, 500, 2000, 5000]
        for user in user_points:
            points = user["total_points"]
            level = 1
            for i, threshold in enumerate(level_thresholds):
                if points >= threshold:
                    level = i + 1
            
            levels_distribution[f"level_{level}"] += 1
        
        if points_result:
            return {
                "total_points_circulating": points_result[0]["total_points"],
                "total_transactions": points_result[0]["total_transactions"],
                "active_users": len(points_result[0]["unique_users"]),
                "total_badges_awarded": total_badges,
                "users_by_level": levels_distribution
            }
        
        return {
            "total_points_circulating": 0,
            "total_transactions": 0,
            "active_users": 0,
            "total_badges_awarded": 0,
            "users_by_level": levels_distribution
        }

    def get_recent_activity(
        self,
        limit: int = 20,
        user_id: Optional[str] = None,
        team_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtener actividad reciente de gamificación.
        Combina transacciones de puntos y badges otorgados.
        """
        activities = []
        
        # Construir query
        query = {}
        if user_id:
            query["user_id"] = user_id
        
        # Obtener transacciones recientes
        txns = list(
            self.point_txns.find(query)
            .sort("timestamp", -1)
            .limit(limit // 2)
        )
        
        for txn in txns:
            activities.append({
                "type": "points",
                "timestamp": txn["timestamp"],
                "user_id": txn["user_id"],
                "points": txn["points"],
                "reason": txn.get("reason", ""),
                "rule_id": txn.get("rule_id")
            })
        
        # Obtener badges recientes
        badges = list(
            self.awards.find(query)
            .sort("awarded_at", -1)
            .limit(limit // 2)
        )
        
        for badge in badges:
            activities.append({
                "type": "badge",
                "timestamp": badge["awarded_at"],
                "user_id": badge["user_id"],
                "badge_id": badge["badge_id"],
                "badge_name": badge.get("badge_name", badge["badge_id"])
            })
        
        # Ordenar por timestamp descendente
        activities.sort(key=lambda x: x["timestamp"], reverse=True)
        
        # Filtrar por equipo si se especificó
        if team_id:
            filtered = []
            for activity in activities[:limit]:
                user = self.users.find_one({"_id": activity["user_id"]})
                if user and user.get("team_id") == team_id:
                    filtered.append(activity)
            return filtered
        
        return activities[:limit]

    def award_points(
        self,
        user_id: str,
        points: int,
        reason: str,
        rule_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Otorgar puntos a un usuario manualmente (admin override).
        
        En producción, esto debería pasar por el RuleEngine.
        Este método es para casos especiales.
        """
        now = datetime.now(timezone.utc)
        
        txn_doc = {
            "user_id": user_id,
            "points": points,
            "reason": reason,
            "rule_id": rule_id or "manual_override",
            "timestamp": now,
            "metadata": metadata or {}
        }
        
        result = self.point_txns.insert_one(txn_doc)
        txn_doc["_id"] = str(result.inserted_id)
        
        return txn_doc


# Singleton global para uso en toda la aplicación
_gamification_service_instance = None


def get_gamification_service() -> GamificationService:
    """Factory function para obtener instancia única del servicio"""
    global _gamification_service_instance
    if _gamification_service_instance is None:
        _gamification_service_instance = GamificationService()
    return _gamification_service_instance