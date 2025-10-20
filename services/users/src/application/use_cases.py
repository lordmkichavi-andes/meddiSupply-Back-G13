from typing import List, Dict, Any
from src.domain.interfaces import UserRepository
from src.domain.entities import User


class GetClientUsersUseCase:
    """
    Caso de uso: Obtener usuarios con rol CLIENT.
    Depende de UserRepository (patrón de inyección de dependencias).
    """

    def __init__(self, user_repository: UserRepository):
        self.repository = user_repository

    def execute(self) -> List[Dict[str, Any]]:
        """
        Ejecuta la lógica de negocio para obtener la lista de usuarios CLIENT.
        """
        # 1. Obtener usuarios con rol CLIENT (Usando el Repositorio)
        users = self.repository.get_users_by_role('CLIENT')

        # 2. Si no hay usuarios
        if not users:
            return []

        # 3. Formatear datos según necesidades del negocio
        formatted_users = []
        for user in users:
            formatted_users.append({
                "user_id": user.user_id,
                "name": user.name,
                "last_name": user.last_name,
                "password": user.password,
                "identification": user.identification,
                "phone": user.phone,
                "rol": user.role.value if hasattr(user.role, 'value') else user.role
            })

        return formatted_users

    def execute_by_seller(self, seller_id: int) -> List[Dict[str, Any]]:
        """
        Ejecuta la lógica de negocio para obtener la lista de usuarios CLIENT.
        """
        # 1. Obtener usuarios con rol CLIENT (Usando el Repositorio)
        users = self.repository.get_users_by_role(seller_id)

        # 2. Si no hay usuarios
        if not users:
            return []

        # 3. Formatear datos según necesidades del negocio
        formatted_users = []
        for user in users:
            formatted_users.append({
                "user_id": user.user_id,
                "name": user.name,
                "last_name": user.last_name,
                "password": user.password,
                "identification": user.identification,
                "phone": user.phone,
                "rol": user.role.value if hasattr(user.role, 'value') else user.role
            })

        return formatted_users