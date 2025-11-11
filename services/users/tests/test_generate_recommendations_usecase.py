import unittest
from unittest.mock import Mock, MagicMock
import sys
import os
from src.domain.interfaces import UserRepository


# Asegurar que los módulos de src se pueden importar
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Importar el caso de uso a probar
from src.application.generate_recommendations_usecase import GenerateRecommendationsUseCase


class TestGenerateRecommendationsUseCase(unittest.TestCase):
    """
    Pruebas unitarias para el Caso de Uso GenerateRecommendationsUseCase.
    """

    def setUp(self):
        """Configuración inicial para cada test."""
        self.mock_recommendation_agent = Mock()

    def test_init_stores_recommendation_agent(self):
        """Prueba que el constructor almacena correctamente el recommendation_agent."""
        self.mock_repo = Mock(spec=UserRepository)
        use_case = GenerateRecommendationsUseCase(self.mock_recommendation_agent, self.mock_repo)
        self.assertEqual(use_case.recommendation_agent, self.mock_recommendation_agent)

    def test_execute_success(self):
        """Prueba la ejecución exitosa del caso de uso."""
        mock_recommendations = [
            {"product_id": 1, "product_sku": "SKU-001", "product_name": "Product 1", "score": 0.9, "reasoning": "High demand"},
            {"product_id": 2, "product_sku": "SKU-002", "product_name": "Product 2", "score": 0.8, "reasoning": "Good fit"}
        ]
        
        self.mock_recommendation_agent.generate_recommendations.return_value = {
            "recommendations": mock_recommendations
        }
        
        use_case = GenerateRecommendationsUseCase(self.mock_recommendation_agent)
        result = use_case.execute(client_id=123, regional_setting='CO')
        
        # Verificar que se llamó al agente con los parámetros correctos
        self.mock_recommendation_agent.generate_recommendations.assert_called_once_with(
            client_id=123,
            regional_setting='CO'
        )
        
        # Verificar el resultado
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["recommendations"], mock_recommendations)

    def test_execute_with_default_regional_setting(self):
        """Prueba la ejecución con el valor por defecto de regional_setting."""
        self.mock_recommendation_agent.generate_recommendations.return_value = {
            "recommendations": []
        }

        self.mock_repo = Mock(spec=UserRepository)
        use_case = GenerateRecommendationsUseCase(self.mock_recommendation_agent, self.mock_repo)
        result = use_case.execute(client_id=456)
        
        # Verificar que se usó el valor por defecto 'CO'
        self.mock_recommendation_agent.generate_recommendations.assert_called_once_with(
            client_id=456,
            regional_setting='CO'
        )
        
        self.assertEqual(result["status"], "success")

    def test_execute_with_empty_client_id(self):
        """Prueba que se lanza ValueError cuando client_id está vacío."""
        self.mock_repo = Mock(spec=UserRepository)
        use_case = GenerateRecommendationsUseCase(self.mock_recommendation_agent, self.mock_repo)
        with self.assertRaises(ValueError) as context:
            use_case.execute(client_id=None)
        
        self.assertIn("El client_id es obligatorio para generar recomendaciones", str(context.exception))
        self.mock_recommendation_agent.generate_recommendations.assert_not_called()

    def test_execute_with_zero_client_id(self):
        """Prueba que se lanza ValueError cuando client_id es 0."""
        self.mock_repo = Mock(spec=UserRepository)
        use_case = GenerateRecommendationsUseCase(self.mock_recommendation_agent, self.mock_repo)
        with self.assertRaises(ValueError) as context:
            use_case.execute(client_id=0)
        
        self.assertIn("El client_id es obligatorio para generar recomendaciones", str(context.exception))
        self.mock_recommendation_agent.generate_recommendations.assert_not_called()

    def test_execute_when_llm_returns_none(self):
        """Prueba que se lanza Exception cuando el agente retorna None."""
        self.mock_recommendation_agent.generate_recommendations.return_value = None

        self.mock_repo = Mock(spec=UserRepository)
        use_case = GenerateRecommendationsUseCase(self.mock_recommendation_agent, self.mock_repo)
        with self.assertRaises(Exception) as context:
            use_case.execute(client_id=789)
        
        self.assertIn("Fallo en el Agente de Razonamiento (LLM)", str(context.exception))
        self.mock_recommendation_agent.generate_recommendations.assert_called_once()

    def test_execute_with_empty_recommendations(self):
        """Prueba la ejecución cuando el agente retorna recomendaciones vacías."""
        self.mock_recommendation_agent.generate_recommendations.return_value = {
            "recommendations": []
        }

        self.mock_repo = Mock(spec=UserRepository)
        use_case = GenerateRecommendationsUseCase(self.mock_recommendation_agent, self.mock_repo)
        result = use_case.execute(client_id=999, regional_setting='MX')

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["recommendations"], [])

    def test_execute_with_missing_recommendations_key(self):
        """Prueba la ejecución cuando el agente retorna un dict sin la clave 'recommendations'."""
        self.mock_recommendation_agent.generate_recommendations.return_value = {
            "other_key": "value"
        }

        self.mock_repo = Mock(spec=UserRepository)
        use_case = GenerateRecommendationsUseCase(self.mock_recommendation_agent, self.mock_repo)
        result = use_case.execute(client_id=111)
        
        # Debe usar get() con valor por defecto []
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["recommendations"], [])


if __name__ == '__main__':
    unittest.main()

