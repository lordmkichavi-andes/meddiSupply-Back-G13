class GenerateRecommendationsUseCase:
    """
    Caso de Uso para generar recomendaciones de productos.
    Orquesta la llamada al RecommendationAgent.
    """
    def __init__(self, recommendation_agent):
        self.recommendation_agent = recommendation_agent

    def execute(self, client_id: int, regional_setting: str = 'CO') -> dict:
        """
        Ejecuta el proceso de recomendación.
        """
        if not client_id:
            raise ValueError("El client_id es obligatorio para generar recomendaciones.")

        recommendation_response = self.recommendation_agent.generate_recommendations(
            client_id=client_id, 
            regional_setting=regional_setting
        )

        if recommendation_response is None:
            raise Exception("Fallo en el Agente de Razonamiento (LLM).")

        return {
            "status": "success",
            "recommendations": recommendation_response.get('recommendations', [])
        }