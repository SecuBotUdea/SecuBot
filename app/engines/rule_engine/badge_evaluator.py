"""
BadgeEvaluator - Evalúa criterios para otorgar badges

Responsabilidades:
- Evaluar condiciones complejas de badges (count, streak, distinct_count, sum)
- Verificar si un usuario cumple criterios para un badge
- Crear registros de Award cuando se cumplen condiciones
- Evitar otorgar badges duplicados
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4


class BadgeEvaluator:
    """
    Evalúa criterios de badges y otorga awards
    
    Usage:
        evaluator = BadgeEvaluator(db_client)
        
        # Evaluar todos los badges para un usuario
        await evaluator.evaluate_user_badges(user_id="user123")
        
        # Evaluar badge específico
        result = await evaluator.evaluate_badge(
            badge=badge_rule,
            user_id="user123"
        )
    """
    
    def __init__(self, db_client):
        """
        Args:
            db_client: Cliente de base de datos (Motor para MongoDB)
        """
        self.db = db_client
    
    async def evaluate_user_badges(
        self,
        user_id: str,
        team_id: Optional[str] = None,
        badge_rules: Optional[List[Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Evalúa todos los badges para un usuario
        
        Args:
            user_id: ID del usuario
            team_id: ID del equipo (opcional, lo ignoramos por ahora)
            badge_rules: Lista de BadgeRule a evaluar (si None, evalúa todos)
        
        Returns:
            Lista de badges otorgados en esta evaluación
        """
        newly_awarded = []
        
        # Si no se pasan badge_rules, obtenerlas del RuleLoader
        if badge_rules is None:
            from app.engines.rule_engine.loader import get_rule_loader
            loader = get_rule_loader()
            badge_rules = loader.get_all_active_badges()
        
        for badge in badge_rules:
            # Solo evaluar badges individuales (ignoramos team por ahora)
            if badge.criteria.type != "individual":
                continue
            
            # Verificar si el usuario ya tiene este badge
            existing_award = await self.db.awards.find_one({
                "badge_id": badge.badge_id,
                "user_id": user_id
            })
            
            if existing_award:
                continue  # Ya tiene este badge
            
            # Evaluar criterios
            meets_criteria = await self.evaluate_badge_criteria(
                badge=badge,
                user_id=user_id,
                team_id=team_id
            )
            
            if meets_criteria:
                # Otorgar badge
                award = await self.award_badge(
                    badge_id=badge.badge_id,
                    user_id=user_id,
                    team_id=team_id,
                    evidence=[]  # TODO: capturar evidencia específica
                )
                newly_awarded.append(award)
        
        return newly_awarded
    
    async def evaluate_badge_criteria(
        self,
        badge: Any,
        user_id: str,
        team_id: Optional[str] = None
    ) -> bool:
        """
        Evalúa si un usuario cumple los criterios de un badge
        
        Args:
            badge: BadgeRule a evaluar
            user_id: ID del usuario
            team_id: ID del equipo
        
        Returns:
            True si cumple los criterios, False caso contrario
        """
        criteria = badge.criteria
        
        # Evaluar cada condición
        for condition_dict in criteria.conditions:
            # Las condiciones pueden ser: count, streak, distinct_count, sum
            for condition_type, condition_config in condition_dict.items():
                
                if condition_type == "count":
                    result = await self._evaluate_count_condition(
                        condition_config,
                        user_id,
                        team_id
                    )
                
                elif condition_type == "streak":
                    result = await self._evaluate_streak_condition(
                        condition_config,
                        user_id,
                        team_id
                    )
                
                elif condition_type == "distinct_count":
                    result = await self._evaluate_distinct_count_condition(
                        condition_config,
                        user_id,
                        team_id
                    )
                
                elif condition_type == "sum":
                    result = await self._evaluate_sum_condition(
                        condition_config,
                        user_id,
                        team_id
                    )
                
                else:
                    result = False
                
                # Si alguna condición falla, no cumple el badge
                if not result:
                    return False
        
        return True
    
    async def _evaluate_count_condition(
        self,
        condition: Any,
        user_id: str,
        team_id: Optional[str]
    ) -> bool:
        """
        Evalúa condición de tipo COUNT
        
        Ejemplo:
            count:
              entity: "PointTxn"
              filters:
                - "user_id == current_user"
                - "rule_id == 'PTS-001'"
                - "points > 0"
              operator: ">="
              threshold: 1
        """
        entity = condition.entity
        filters = condition.filters
        operator = condition.operator
        threshold = condition.threshold
        
        # Construir query MongoDB desde filters
        query = self._build_query_from_filters(filters, user_id, team_id)
        
        # Determinar colección
        collection = self._get_collection(entity)
        
        # Ejecutar count
        count = await collection.count_documents(query)
        
        # Comparar con threshold
        return self._compare_values(count, operator, threshold)
    
    async def _evaluate_streak_condition(
        self,
        condition: Any,
        user_id: str,
        team_id: Optional[str]
    ) -> bool:
        """
        Evalúa condición de tipo STREAK (días consecutivos)
        
        Ejemplo:
            streak:
              entity: "PointTxn"
              filters: [...]
              consecutive_days: 7
              min_per_day: 1
        """
        entity = condition.entity
        filters = condition.filters
        consecutive_days = condition.consecutive_days
        min_per_day = condition.min_per_day
        
        # Construir query base
        base_query = self._build_query_from_filters(filters, user_id, team_id)
        collection = self._get_collection(entity)
        
        # Verificar últimos N días consecutivos
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for day_offset in range(consecutive_days):
            day_start = today - timedelta(days=day_offset)
            day_end = day_start + timedelta(days=1)
            
            day_query = {
                **base_query,
                "timestamp": {"$gte": day_start, "$lt": day_end}
            }
            
            count = await collection.count_documents(day_query)
            
            if count < min_per_day:
                return False  # Rompió la racha
        
        return True
    
    async def _evaluate_distinct_count_condition(
        self,
        condition: Any,
        user_id: str,
        team_id: Optional[str]
    ) -> bool:
        """
        Evalúa condición de tipo DISTINCT_COUNT
        
        Ejemplo:
            distinct_count:
              entity: "Alert"
              field: "source_id"
              filters: [...]
              operator: ">="
              threshold: 3
        """
        entity = condition.entity
        field = condition.field
        filters = condition.filters
        operator = condition.operator
        threshold = condition.threshold
        
        query = self._build_query_from_filters(filters, user_id, team_id)
        collection = self._get_collection(entity)
        
        # Obtener valores distintos
        distinct_values = await collection.distinct(field, query)
        count = len(distinct_values)
        
        return self._compare_values(count, operator, threshold)
    
    async def _evaluate_sum_condition(
        self,
        condition: Any,
        user_id: str,
        team_id: Optional[str]
    ) -> bool:
        """
        Evalúa condición de tipo SUM
        
        Ejemplo:
            sum:
              entity: "PointTxn"
              field: "points"
              filters: [...]
              operator: ">="
              threshold: 1000
        """
        entity = condition.entity
        field = condition.field
        filters = condition.filters
        operator = condition.operator
        threshold = condition.threshold
        
        query = self._build_query_from_filters(filters, user_id, team_id)
        collection = self._get_collection(entity)
        
        # Agregar suma usando pipeline
        pipeline = [
            {"$match": query},
            {"$group": {"_id": None, "total": {"$sum": f"${field}"}}}
        ]
        
        result = await collection.aggregate(pipeline).to_list(length=1)
        total = result[0]["total"] if result else 0
        
        return self._compare_values(total, operator, threshold)
    
    async def award_badge(
        self,
        badge_id: str,
        user_id: str,
        team_id: Optional[str],
        evidence: List[str]
    ) -> Dict[str, Any]:
        """
        Otorga un badge a un usuario
        
        Args:
            badge_id: ID del badge
            user_id: Usuario receptor
            team_id: Equipo (opcional)
            evidence: Referencias de evidencia
        
        Returns:
            Award creado
        """
        award = {
            "award_id": str(uuid4()),
            "badge_id": badge_id,
            "user_id": user_id,
            "team_id": team_id,
            "timestamp": datetime.utcnow(),
            "evidence_refs": evidence,
            "metadata": {}
        }
        
        await self.db.awards.insert_one(award)
        
        return award
    
    def _build_query_from_filters(
        self,
        filters: List[str],
        user_id: str,
        team_id: Optional[str]
    ) -> Dict[str, Any]:
        """
        Construye query MongoDB desde lista de filtros
        
        Args:
            filters: Lista de condiciones en formato string
                     Ejemplo: ["user_id == current_user", "points > 0"]
            user_id: Usuario actual (para resolver "current_user")
            team_id: Equipo actual
        
        Returns:
            Dict con query MongoDB
        """
        query = {}
        
        for filter_str in filters:
            # Parsear condición simple
            parts = filter_str.split()
            
            if len(parts) < 3:
                continue
            
            field = parts[0]
            operator = parts[1]
            value = " ".join(parts[2:])
            
            # Resolver valores especiales
            if value == "current_user":
                value = user_id
            elif value == "current_team":
                value = team_id
            else:
                value = self._parse_value(value)
            
            # Convertir operador a MongoDB
            if operator == "==":
                query[field] = value
            elif operator == "!=":
                query[field] = {"$ne": value}
            elif operator == ">":
                query[field] = {"$gt": value}
            elif operator == "<":
                query[field] = {"$lt": value}
            elif operator == ">=":
                query[field] = {"$gte": value}
            elif operator == "<=":
                query[field] = {"$lte": value}
            elif operator == "IN":
                query[field] = {"$in": value if isinstance(value, list) else [value]}
        
        return query
    
    def _parse_value(self, value_str: str) -> Any:
        """Parsea valor desde string"""
        value_str = value_str.strip()
        
        # String con comillas
        if value_str.startswith("'") and value_str.endswith("'"):
            return value_str[1:-1]
        
        # Lista
        if value_str.startswith("[") and value_str.endswith("]"):
            items = value_str[1:-1].split(",")
            return [item.strip().strip("'\"") for item in items]
        
        # Number
        try:
            return int(value_str)
        except ValueError:
            try:
                return float(value_str)
            except ValueError:
                return value_str
    
    def _get_collection(self, entity: str):
        """Obtiene colección MongoDB desde nombre de entidad"""
        entity_to_collection = {
            "PointTxn": self.db.point_transactions,
            "Alert": self.db.alerts,
            "Remediation": self.db.remediations,
            "RescanResult": self.db.rescan_results,
        }
        return entity_to_collection.get(entity)
    
    def _compare_values(self, value: Any, operator: str, threshold: Any) -> bool:
        """Compara valores con operador"""
        if operator == "==":
            return value == threshold
        elif operator == "!=":
            return value != threshold
        elif operator == ">":
            return value > threshold
        elif operator == "<":
            return value < threshold
        elif operator == ">=":
            return value >= threshold
        elif operator == "<=":
            return value <= threshold
        else:
            return False