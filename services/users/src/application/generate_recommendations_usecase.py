from src.domain.interfaces import UserRepository
import logging

logger = logging.getLogger(__name__)

class GenerateRecommendationsUseCase:
    """
    Caso de Uso para generar recomendaciones de productos.
    Orquesta la llamada al RecommendationAgent.
    """
    def __init__(self, recommendation_agent, user_repository: UserRepository):
        self.recommendation_agent = recommendation_agent
        self.repository = user_repository

    def execute(self, client_id: int, regional_setting: str = 'CO', visit_id: int = None) -> dict:
        """
        Ejecuta el proceso de recomendación.
        """
        if not client_id:
            raise ValueError("El client_id es obligatorio para generar recomendaciones.")

        recommendation_response = self.recommendation_agent.generate_recommendations(
            client_id=client_id, 
            regional_setting=regional_setting
        )

        if not recommendation_response or not recommendation_response.get('recommendations'):
            raise ValueError("El Agente LLM no pudo generar recomendaciones válidas.")

        all_products_list = self.repository.get_products() 

        final_recommendations = []
        all_products_map = {p['sku']: p for p in all_products_list}

        for rec in recommendation_response['recommendations']:
            sku = rec.get('product_sku')
            product_data = all_products_map.get(sku)
            
            if product_data:
                rec['product_id'] = product_data['product_id']
                rec['product_name'] = product_data['name'] 
                self.repository.save_suggestion(
                    visit_id=visit_id,
                    product_id=rec['product_id']
                )
                
                final_recommendations.append(rec)
            else:
                logger.warning(f"LLM recomendó SKU desconocido: {sku}")

        return {
            "status": "success",
            "recommendations": final_recommendations
        }