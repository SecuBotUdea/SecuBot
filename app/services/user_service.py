# app/services/user_service.py
"""
Servicio de gestión de usuarios.
Responsable de CRUD básico de usuarios sin autenticación (sin password).
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from app.database.mongodb import get_database


class UserService:
    """
    Servicio principal para gestión de usuarios.
    
    Responsable de:
    - CRUD básico de usuarios
    - Validación de unicidad (username, email)
    - Gestión de roles y equipos
    - Queries para asignación de puntos y leaderboards
    """

    def __init__(self):
        self.db = get_database()
        self.collection = self.db.users
        self._ensure_indexes()

    def _ensure_indexes(self):
        """Crear índices estratégicos para optimizar queries"""
        try:
            # Índices únicos
            self.collection.create_index("username", unique=True)
            self.collection.create_index("email", unique=True)
            
            # Índices para búsquedas comunes
            self.collection.create_index("role")
            self.collection.create_index("team_id")
            self.collection.create_index("is_active")
            self.collection.create_index("email_verified")
            self.collection.create_index("created_at")
            
            # Índices compuestos
            self.collection.create_index([("role", 1), ("is_active", 1)])
            self.collection.create_index([("team_id", 1), ("is_active", 1)])
            
        except Exception as e:
            print(f"Advertencia al crear índices de usuarios: {e}")

    def create_user(
        self,
        username: str,
        email: str,
        display_name: Optional[str] = None,
        role: str = "developer",
        team_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Crear un nuevo usuario.
        
        Args:
            username: Nombre de usuario único
            email: Email único
            display_name: Nombre para mostrar (opcional, usa username por defecto)
            role: Rol del usuario (developer, team_lead, admin, super_admin)
            team_id: ID del equipo al que pertenece (opcional)
            metadata: Metadata adicional (opcional)
            
        Returns:
            Dict con el usuario creado
            
        Raises:
            ValueError: Si username o email ya existen
        """
        # Validar unicidad de username
        if self.collection.count_documents({"username": username}) > 0:
            raise ValueError(f"Username '{username}' ya existe")
        
        # Validar unicidad de email
        if self.collection.count_documents({"email": email}) > 0:
            raise ValueError(f"Email '{email}' ya existe")
        
        # Validar rol
        valid_roles = ["developer", "team_lead", "admin", "super_admin"]
        if role not in valid_roles:
            raise ValueError(f"Rol inválido. Valores permitidos: {valid_roles}")
        
        now = datetime.now(timezone.utc)
        
        # Construir documento del usuario
        user_doc = {
            "username": username,
            "email": email,
            "display_name": display_name or username,
            "role": role,
            "team_id": team_id,
            "metadata": metadata or {},
            "is_active": True,
            "email_verified": False,
            "created_at": now,
            "updated_at": now
        }
        
        # Insertar en MongoDB
        result = self.collection.insert_one(user_doc)
        user_doc["_id"] = str(result.inserted_id)
        
        return user_doc

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtener un usuario por su _id de MongoDB.
        
        Args:
            user_id: ID del usuario (ObjectId como string)
            
        Returns:
            Dict con el usuario o None si no existe
        """
        from bson import ObjectId
        
        try:
            user = self.collection.find_one({"_id": ObjectId(user_id)})
            if user:
                user["_id"] = str(user["_id"])
            return user
        except Exception:
            return None

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Obtener un usuario por su username.
        """
        user = self.collection.find_one({"username": username})
        if user:
            user["_id"] = str(user["_id"])
        return user

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Obtener un usuario por su email.
        """
        user = self.collection.find_one({"email": email})
        if user:
            user["_id"] = str(user["_id"])
        return user

    def update_user(
        self,
        user_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Actualizar campos de un usuario.
        
        Args:
            user_id: ID del usuario
            **kwargs: Campos a actualizar (display_name, role, team_id, metadata, etc.)
            
        Returns:
            Usuario actualizado
            
        Raises:
            ValueError: Si el usuario no existe
        """
        from bson import ObjectId
        
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"Usuario {user_id} no encontrado")
        
        # Preparar actualización
        update_data = {}
        
        # Campos permitidos para actualizar
        allowed_fields = [
            "display_name", "role", "team_id", "metadata",
            "is_active", "email_verified"
        ]
        
        for field in allowed_fields:
            if field in kwargs:
                update_data[field] = kwargs[field]
        
        # Siempre actualizar timestamp
        update_data["updated_at"] = datetime.now(timezone.utc)
        
        # Ejecutar actualización
        if update_data:
            self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_data}
            )
        getAlertResult = self.get_user(user_id)
        assert getAlertResult is not None
        
        return getAlertResult

    def delete_user(self, user_id: str) -> bool:
        """
        Eliminar un usuario (soft delete marcando is_active=False).
        
        Args:
            user_id: ID del usuario
            
        Returns:
            True si se eliminó exitosamente
        """
        from bson import ObjectId
        
        result = self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "is_active": False,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        return result.modified_count > 0

    def hard_delete_user(self, user_id: str) -> bool:
        """
        Eliminar un usuario permanentemente de la base de datos.
        ⚠️ ADVERTENCIA: Esta operación es irreversible.
        """
        from bson import ObjectId
        
        result = self.collection.delete_one({"_id": ObjectId(user_id)})
        return result.deleted_count > 0

    def list_users(
        self,
        role: Optional[str] = None,
        team_id: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Listar usuarios con filtros opcionales.
        
        Returns:
            Lista de usuarios ordenados por created_at descendente
        """
        query = {}
        
        if role:
            query["role"] = role
        if team_id:
            query["team_id"] = team_id
        if is_active is not None:
            query["is_active"] = is_active
        
        cursor = self.collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
        
        users = []
        for user in cursor:
            user["_id"] = str(user["_id"])
            users.append(user)
        
        return users

    def get_active_users(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Obtener usuarios activos.
        Útil para leaderboards y asignación de alertas.
        """
        return self.list_users(is_active=True, limit=limit)

    def get_users_by_team(self, team_id: str) -> List[Dict[str, Any]]:
        """
        Obtener todos los usuarios de un equipo específico.
        """
        return self.list_users(team_id=team_id, is_active=True, limit=1000)

    def get_users_by_role(self, role: str) -> List[Dict[str, Any]]:
        """
        Obtener usuarios por rol.
        """
        return self.list_users(role=role, limit=1000)

    def verify_email(self, user_id: str) -> Dict[str, Any]:
        """
        Marcar el email de un usuario como verificado.
        """
        return self.update_user(user_id, email_verified=True)

    def assign_to_team(self, user_id: str, team_id: str) -> Dict[str, Any]:
        """
        Asignar un usuario a un equipo.
        """
        return self.update_user(user_id, team_id=team_id)

    def change_role(self, user_id: str, new_role: str) -> Dict[str, Any]:
        """
        Cambiar el rol de un usuario.
        """
        valid_roles = ["developer", "team_lead", "admin", "super_admin"]
        if new_role not in valid_roles:
            raise ValueError(f"Rol inválido. Valores permitidos: {valid_roles}")
        
        return self.update_user(user_id, role=new_role)

    def update_metadata(self, user_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualizar metadata del usuario (mergea con metadata existente).
        """
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"Usuario {user_id} no encontrado")
        
        # Mergear metadata
        current_metadata = user.get("metadata", {})
        current_metadata.update(metadata)
        
        return self.update_user(user_id, metadata=current_metadata)

    def get_stats(self) -> Dict[str, Any]:
        """
        Obtener estadísticas generales de usuarios.
        """
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "total": {"$sum": 1},
                    "active": {
                        "$sum": {"$cond": [{"$eq": ["$is_active", True]}, 1, 0]}
                    },
                    "inactive": {
                        "$sum": {"$cond": [{"$eq": ["$is_active", False]}, 1, 0]}
                    },
                    "verified": {
                        "$sum": {"$cond": [{"$eq": ["$email_verified", True]}, 1, 0]}
                    },
                    "developers": {
                        "$sum": {"$cond": [{"$eq": ["$role", "developer"]}, 1, 0]}
                    },
                    "team_leads": {
                        "$sum": {"$cond": [{"$eq": ["$role", "team_lead"]}, 1, 0]}
                    },
                    "admins": {
                        "$sum": {"$cond": [{"$eq": ["$role", "admin"]}, 1, 0]}
                    },
                    "super_admins": {
                        "$sum": {"$cond": [{"$eq": ["$role", "super_admin"]}, 1, 0]}
                    }
                }
            }
        ]
        
        result = list(self.collection.aggregate(pipeline))
        
        if result:
            stats = result[0]
            stats.pop("_id", None)
            return stats
        
        return {
            "total": 0,
            "active": 0,
            "inactive": 0,
            "verified": 0,
            "developers": 0,
            "team_leads": 0,
            "admins": 0,
            "super_admins": 0
        }

    def user_exists(self, username: Optional[str] = None, email: Optional[str] = None) -> bool:
        """
        Verificar si existe un usuario por username o email.
        Útil para validaciones antes de crear.
        """
        if username:
            if self.collection.count_documents({"username": username}) > 0:
                return True
        
        if email:
            if self.collection.count_documents({"email": email}) > 0:
                return True
        
        return False

    def search_users(self, search_term: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Buscar usuarios por username, email o display_name.
        Búsqueda case-insensitive con regex.
        """
        regex_pattern = {"$regex": search_term, "$options": "i"}
        
        query = {
            "$or": [
                {"username": regex_pattern},
                {"email": regex_pattern},
                {"display_name": regex_pattern}
            ],
            "is_active": True
        }
        
        cursor = self.collection.find(query).limit(limit)
        
        users = []
        for user in cursor:
            user["_id"] = str(user["_id"])
            users.append(user)
        
        return users


# Singleton global para uso en toda la aplicación
_user_service_instance = None


def get_user_service() -> UserService:
    """Factory function para obtener instancia única del servicio"""
    global _user_service_instance
    if _user_service_instance is None:
        _user_service_instance = UserService()
    return _user_service_instance