import unittest
from unittest.mock import Mock, MagicMock
from src.application.register_visit import RegisterVisitUseCase
from src.domain.interfaces import UserRepository  # Asumiendo la ruta correcta


# No necesitamos importar User de src.domain.entities a menos que se use directamente
# en el resultado esperado, pero es bueno tener la ruta de las interfaces.

# --- Clase de Prueba ---
class TestRegisterVisitUseCase(unittest.TestCase):
    """
    Clase de prueba para el caso de uso RegisterVisitUseCase.
    """

    def setUp(self):
        """
        Configuración inicial antes de cada prueba.
        Inicializa un Mock para el UserRepository y la instancia del Caso de Uso.
        """
        # Crear un Mock para simular la dependencia UserRepository
        self.mock_repo = Mock(spec=UserRepository)

        # Instanciar el Caso de Uso con el Mock
        self.use_case = RegisterVisitUseCase(user_repository=self.mock_repo)

        # Definir datos de prueba comunes
        self.client_id = 101
        self.seller_id = 202
        self.date = "2025-10-21"
        self.findings = "El cliente necesita más información sobre el producto X."

        # Definir el valor de retorno simulado para el método save_visit
        # Este es el objeto o estructura que 'devuelve' el repositorio al guardar
        self.mock_new_visit_data = {
            "id": 500,
            "client_id": self.client_id,
            "seller_id": self.seller_id,
            "date": self.date,
            "findings": self.findings,
        }
        # Configurar el Mock para que devuelva los datos simulados cuando se llame a save_visit
        self.mock_repo.save_visit.return_value = self.mock_new_visit_data

    def test_execute_successful_registration(self):
        """
        Prueba que la ejecución del caso de uso registre la visita correctamente
        y retorne el resultado esperado.
        """
        print("\n--- Ejecutando test_execute_successful_registration ---")

        # 1. Ejecutar el método a probar
        result = self.use_case.execute(
            client_id=self.client_id,
            seller_id=self.seller_id,
            date=self.date,
            findings=self.findings
        )

        # 2. Verificaciones (Asserts)

        # Verificar que el método 'save_visit' del repositorio fue llamado
        # **exactamente una vez** y con los **argumentos correctos**.
        self.mock_repo.save_visit.assert_called_once_with(
            client_id=self.client_id,
            seller_id=self.seller_id,
            date=self.date,
            findings=self.findings
        )

        # Verificar el resultado retornado por el caso de uso
        expected_result = {
            "message": "Visita registrada con éxito en la base de datos.",
            "visit": self.mock_new_visit_data  # Debe contener los datos devueltos por el mock
        }
        self.assertEqual(result, expected_result,
                         "El resultado de la ejecución no coincide con el esperado.")

        print("Registro exitoso verificado.")

    def test_execute_repository_call_with_different_data(self):
        """
        Prueba que el caso de uso pase cualquier dato que reciba
        al método 'save_visit' del repositorio.
        """
        print("\n--- Ejecutando test_execute_repository_call_with_different_data ---")

        # Datos de prueba diferentes
        diff_client_id = 999
        diff_seller_id = 888
        diff_date = "2026-01-01"
        diff_findings = "Solo fue una visita de cortesía."

        # Ejecutar el método con los datos diferentes
        self.use_case.execute(
            client_id=diff_client_id,
            seller_id=diff_seller_id,
            date=diff_date,
            findings=diff_findings
        )

        # Verificar que el método 'save_visit' fue llamado con los nuevos argumentos
        self.mock_repo.save_visit.assert_called_once_with(
            client_id=diff_client_id,
            seller_id=diff_seller_id,
            date=diff_date,
            findings=diff_findings
        )
        print("Llamada al repositorio con datos diferentes verificada.")

    def test_execute_handles_empty_findings(self):
        """
        Prueba el comportamiento cuando los 'findings' son una cadena vacía,
        asumiendo que esto es un valor aceptable.
        """
        print("\n--- Ejecutando test_execute_handles_empty_findings ---")

        empty_findings = ""

        # Configurar un nuevo mock_new_visit_data para este caso si fuera necesario,
        # pero para este test solo verificamos la llamada.

        self.use_case.execute(
            client_id=self.client_id,
            seller_id=self.seller_id,
            date=self.date,
            findings=empty_findings
        )

        # Verificar la llamada al repositorio
        self.mock_repo.save_visit.assert_called_once_with(
            client_id=self.client_id,
            seller_id=self.seller_id,
            date=self.date,
            findings=empty_findings
        )
        print("Manejo de 'findings' vacíos verificado.")


# --- Ejecución del archivo de prueba ---
if __name__ == '__main__':
    unittest.main()