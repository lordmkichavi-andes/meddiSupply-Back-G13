import unittest
from unittest.mock import Mock, MagicMock
# Asegúrate de que las rutas de importación coincidan con la estructura de tu proyecto
from src.application.register_visit_usecase import RegisterVisitUseCase
from src.domain.interfaces import UserRepository


# --- Clase de Prueba ---
class TestRegisterVisitUseCase(unittest.TestCase):
    """
    Clase de prueba para el caso de uso RegisterVisitUseCase,
    aislando la dependencia UserRepository mediante mocking.
    """

    def setUp(self):
        """
        Configuración inicial antes de cada prueba:
        1. Mockear el UserRepository.
        2. Instanciar el Caso de Uso con el Mock.
        3. Definir datos de prueba.
        """
        # 1. Crear un Mock para simular la dependencia UserRepository
        # Usamos spec=UserRepository para garantizar que el mock tenga los métodos correctos
        self.mock_repo = Mock(spec=UserRepository)

        # 2. Instanciar el Caso de Uso con el Mock
        self.use_case = RegisterVisitUseCase(user_repository=self.mock_repo)

        # 3. Definir datos de prueba comunes
        self.client_id = 101
        self.seller_id = 202
        self.date = "2025-10-21"
        self.findings = "El cliente está interesado en la nueva línea de productos."

        # Datos simulados que el repositorio devolvería tras guardar
        self.mock_new_visit_data = {
            "id": 500,
            "client_id": self.client_id,
            "seller_id": self.seller_id,
            "date": self.date,
            "findings": self.findings,
            "created_at": "2025-10-21T10:00:00Z"
        }

        # Configurar el Mock: save_visit siempre devolverá los datos simulados
        self.mock_repo.save_visit.return_value = self.mock_new_visit_data

    def test_execute_successful_registration(self):
        """
        Verifica que el caso de uso registre la visita llamando al repositorio
        con los parámetros correctos y devuelva la estructura de respuesta esperada.
        """

        # 1. Ejecutar el método a probar
        result = self.use_case.execute(
            client_id=self.client_id,
            seller_id=self.seller_id,
            date=self.date,
            findings=self.findings
        )

        # 2. Verificaciones

        # A. **Verificar la llamada al repositorio (el corazón del test unitario)**
        # Asegura que el método 'save_visit' fue llamado exactamente una vez con los argumentos correctos.
        self.mock_repo.save_visit.assert_called_once_with(
            client_id=self.client_id,
            seller_id=self.seller_id,
            date=self.date,
            findings=self.findings
        )

        # B. **Verificar el resultado del caso de uso**
        expected_result = {
            "message": "Visita registrada con éxito en la base de datos.",
            "visit": self.mock_new_visit_data  # Debe contener los datos devueltos por el mock
        }
        self.assertEqual(result, expected_result,
                         "El resultado retornado por el Caso de Uso es incorrecto.")

    def test_execute_handles_repository_error(self):
        """
        Verifica que el caso de uso maneje y propague una excepción
        si el repositorio falla al guardar.
        """

        # Configurar el Mock para que lance una excepción al ser llamado
        # Esto simula un fallo de conexión a la base de datos o un error de lógica del repositorio.
        self.mock_repo.save_visit.side_effect = Exception("Fallo de conexión de la base de datos.")

        # 1. Ejecutar y verificar que se lanza la excepción
        with self.assertRaisesRegex(Exception, "Fallo de conexión de la base de datos."):
            self.use_case.execute(
                client_id=self.client_id,
                seller_id=self.seller_id,
                date=self.date,
                findings=self.findings
            )

        # 2. Verificación adicional: Confirmar que, aunque falló, el repositorio fue llamado
        self.mock_repo.save_visit.assert_called_once()


# --- Ejecución del archivo de prueba ---
if __name__ == '__main__':
    unittest.main()