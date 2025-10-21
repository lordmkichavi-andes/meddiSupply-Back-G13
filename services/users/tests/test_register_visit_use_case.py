import unittest
from unittest.mock import MagicMock
from datetime import date
from typing import Dict, Any


# Asume que esta es la ruta de tu Caso de Uso
# from src.application.use_cases import RegisterVisitUseCase
# He redefinido la clase aquí para que el test sea autocontenido y ejecutable
class RegisterVisitUseCase:
    """Caso de uso: Registrar las visitas de los sellers."""

    def __init__(self, user_repository):
        self.repository = user_repository

    def execute(self, client_id: int, seller_id: int, date: str, findings: str) -> Dict[str, Any]:
        """Ejecuta la lógica de negocio para registrar una visita."""
        new_visit = self.repository.save_visit(
            client_id=client_id,
            seller_id=seller_id,
            date=date,
            findings=findings,
        )
        return {
            "message": "Visita registrada con éxito en la base de datos.",
            "visit": new_visit
        }


class TestRegisterVisitUseCase(unittest.TestCase):

    def setUp(self):
        """Configuración previa a cada prueba."""
        # Creamos un mock para el repositorio (que implementa UserRepository)
        self.mock_repo = MagicMock()
        # Inicializamos el Caso de Uso con el repositorio mockeado
        self.use_case = RegisterVisitUseCase(self.mock_repo)

        # Datos de prueba
        self.client_id = 101
        self.seller_id = 202
        self.visit_date = date(2025, 10, 21).isoformat()  # Formato de fecha estándar
        self.findings = "El cliente aceptó la propuesta de servicios."

        # Datos esperados que devuelve el repositorio al guardar
        self.mock_visit_return = {
            "visit_id": 99,
            "client_id": self.client_id,
            "seller_id": self.seller_id,
            "date": self.visit_date,
            "findings": self.findings
        }

    def test_successful_visit_registration(self):
        """Prueba que el registro de una visita se ejecuta correctamente y retorna el mensaje esperado."""

        # Configurar el mock para que devuelva un valor simulado al llamar a save_visit
        self.mock_repo.save_visit.return_value = self.mock_visit_return

        # Ejecutar el Caso de Uso
        result = self.use_case.execute(
            client_id=self.client_id,
            seller_id=self.seller_id,
            date=self.visit_date,
            findings=self.findings
        )

        # 1. Verificar que el repositorio fue llamado exactamente una vez con los argumentos correctos
        self.mock_repo.save_visit.assert_called_once_with(
            client_id=self.client_id,
            seller_id=self.seller_id,
            date=self.visit_date,
            findings=self.findings,
        )

        # 2. Verificar el mensaje de éxito y la estructura de la respuesta
        self.assertIsInstance(result, dict)
        self.assertEqual(result["message"], "Visita registrada con éxito en la base de datos.")

        # 3. Verificar que el objeto de visita devuelto es el que simulamos
        self.assertEqual(result["visit"], self.mock_visit_return)

    def test_repository_raises_exception(self):
        """Prueba que si el repositorio lanza una excepción (ej. error de BD), el caso de uso la propaga."""

        # Configurar el mock para que lance una excepción específica al llamar a save_visit
        self.mock_repo.save_visit.side_effect = ConnectionError("Database connection lost.")

        # Verificar que al ejecutar el caso de uso, se lanza la misma excepción
        with self.assertRaises(ConnectionError) as cm:
            self.use_case.execute(
                client_id=self.client_id,
                seller_id=self.seller_id,
                date=self.visit_date,
                findings=self.findings
            )

        # Opcional: verificar el mensaje de la excepción propagada
        self.assertIn("Database connection lost.", str(cm.exception))


if __name__ == '__main__':
    unittest.main()
