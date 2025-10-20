from typing import List, Dict, Any
from src.domain.interfaces import UserRepository
from src.domain.entities import User


class RegisterVisitUseCase:
    """
    Caso de uso: Registrar las visitas de los sellers   ||
    Depende de UserRepository (patrón de inyección de dependencias).
    """

    def __init__(self, user_repository: UserRepository):
        self.repository = user_repository

    def execute(self, client_id: int, seller_id: int, fecha: date, findings: str) -> Dict[str, Any]:
        """
        Ejecuta la lógica de negocio para registrar una visita.

        :param client_id: ID del cliente visitado.
        :param seller_id: ID del vendedor que realiza la visita.
        :param fecha: Objeto date con la fecha de la visita.
        :param findings: Observaciones y hallazgos de la visita.
        :return: Un diccionario con el resultado del registro.
        """
        # 1. Crear el objeto o estructura de datos de la Visita
        visit_data = {
            "client_id": client_id,
            "seller_id": seller_id,
            # Aseguramos que la fecha se almacene en el formato adecuado para el repositorio/BD
            "date": fecha,
            "findings": findings
        }

        # 2. Persistir la Visita (Llamando al Repositorio)
        # Se asume que el método `save_visit` maneja la conexión y el almacenamiento.
        new_visit = self.repository.save_visit(visit_data)

        # 3. Retornar el resultado del registro
        # Opcionalmente, puedes retornar el ID o detalles de la visita recién creada
        return {
            "message": "Visita registrada con éxito en la base de datos.",
            "visit_id": new_visit.visit_id if hasattr(new_visit, 'visit_id') else None
        }