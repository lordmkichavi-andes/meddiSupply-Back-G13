import os
import time
import json
import requests
import random
import logging
from typing import List, Dict, Any, Optional
from src.clients.products_client import products_client
from src.clients.orders_client import orders_client
from src.domain.interfaces import UserRepository

def get_products() -> List[Dict[str, Any]]:
    """Obtiene todos los productos activos para el selector a través del microservicio de products."""
    try:
        return products_client.get_all_active_products()
    except Exception as e:
        logger.error(f"Error obteniendo productos del microservicio: {e}")
        return []

def get_client_data(client_id: int) -> List[Dict[str, Any]]:
    """
    Función helper para obtener la data del cliente.
    """
    try:
        return orders_client.get_client_detail(client_id)
    except Exception as e:
        logger.error(f"Fallo grave al usar el cliente: {e}")
        return []
        
class RecommendationAgent:
    """
    Encapsula toda la lógica de obtención de inteligencia y la invocación 
    al LLM de Gemini.
    """
    
    def __init__(self, user_repository: UserRepository):
        self.MAX_RETRIES = 5
        self.BASE_DELAY = 1.0
        self.GEMINI_API_URL = os.getenv(
            "GEMINI_API_URL", 
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent"
        )
        self.API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyDBM4aXt4948DT9Z_JkKmLKOvgRb19IZGA') 
        self.user_repository = user_repository
        
    def _get_client_intelligence_tags(self, client_id: int, media: List[Dict[str, str]]) -> List[str]:
        """
        MOCK: Simula la generación de tags de inteligencia visual.
        """
        TAGS_POSIBLES = [
            "COMPETENCIA_VISIBLE:Producto_Genérico_A", "COMPETENCIA_VISIBLE:Producto_Líder_B",
            "PRODUCTO_PROPIO_BAJO_STOCK", "PRODUCTO_PROPIO_SOBRE_STOCK",
            "MERCANCÍA_VENCIDA_VISIBLE", "EXHIBIDOR_VACÍO_COMPLETO"
        ]
        
        num_media = len(media)
        base_tags = min(num_media + 1, 5) 
        random.seed(client_id)
        variation_tags = random.randint(1, 3) 
        num_tags_to_select = min(base_tags + variation_tags, len(TAGS_POSIBLES))
        
        selected_tags = random.sample(TAGS_POSIBLES, k=num_tags_to_select)
        
        if "PRODUCTO_PROPIO_BAJO_STOCK" in selected_tags and "PRODUCTO_PROPIO_SOBRE_STOCK" in selected_tags:
             selected_tags.remove("PRODUCTO_PROPIO_SOBRE_STOCK")
    
        return selected_tags

    def _build_agent_prompt(
        self, tags: List[str], catalog: List[Dict[str, Any]], client_profile: Dict[str, Any], 
        regional_setting: str, client_purchase_history: List[Dict[str, Any]]
    ) -> str:
        tag_str = ", ".join(tags) if tags else "Ninguna registrada."
        catalog_list = "\n".join([f"- {p['name']} (SKU: {p['sku']})" for p in catalog])

        profile_summary = (
            f"Nombre: {client_profile.get('user_name', 'N/A')}.\n"
            f"Balance Pendiente: ${client_profile.get('balance', '0.00')}."
        )
        
        if client_purchase_history:
            history_summary = "\n".join([
                f"- SKU: {h.get('product_sku', 'N/A')} | Última Fecha: {h.get('last_purchase_date', 'N/A')}" 
                for h in client_purchase_history
            ])
        else:
            history_summary = "El cliente no tiene historial de compras reciente o disponible."

        return f"""
        Eres un Motor de Razonamiento IA (LLM) para MediSupply. Genera una lista de tres (3) recomendaciones de productos.

        **CONTEXTO DE DECISIÓN:**
        1. PAÍS OBJETIVO: {regional_setting}
        2. PERFIL: {profile_summary}
        3. EVIDENCIA VISUAL (Tags): {tag_str}
        4. HISTORIAL DE COMPRAS: {history_summary}
        5. CATÁLOGO DISPONIBLE: {catalog_list}

        ---
        TAREA CRÍTICA:
        A) Usa búsqueda web para encontrar restricciones sanitarias en {regional_setting} que afecten al catálogo.
        B) Genera 3 recomendaciones balanceando Táctica (Tags), Preferencia (Historial) y Legalidad (Web).
        C) SALIDA: Genera SOLO el objeto JSON.
        
        {{
            "recommendations": [
                {{"product_sku": "string", "product_name": "string", "score": 0.0, "reasoning": "string"}},
                {{"product_sku": "string", "product_name": "string", "score": 0.0, "reasoning": "string"}},
                {{"product_sku": "string", "product_name": "string", "score": 0.0, "reasoning": "string"}}
            ]
        }}
        """

    def invoke(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Invoca el LLM de Gemini con Google Search grounding, reintentos y Exponential Backoff.
        """
        headers = {'Content-Type': 'application/json'}
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "OBJECT",
                    "properties": {
                        "recommendations": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "product_sku": {"type": "STRING"},
                                    "product_name": {"type": "STRING"},
                                    "score": {"type": "NUMBER"},
                                    "reasoning": {"type": "STRING"}
                                }
                            }
                        }
                    }
                }
            }
        }
        
        if not self.API_KEY:
            logger.error("LLM ERROR: La variable API_KEY está vacía. No se puede llamar al servicio de Gemini.")
            return None

        for attempt in range(self.MAX_RETRIES):
            try:
                response = requests.post(
                    f"{self.GEMINI_API_URL}?key={self.API_KEY}", 
                    json=payload, 
                    headers=headers, 
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if result.get('candidates') and result['candidates'][0]['content']['parts'][0]['text']:
                        json_str = result['candidates'][0]['content']['parts'][0]['text']
                        return json.loads(json_str)
                    else:
                        logger.error("LLM API - Respuesta 200, pero el texto generado está vacío.")
                        return None
                        
                if response.status_code >= 500:
                    logger.warning(f"LLM API - Intento {attempt + 1}: Error de servidor ({response.status_code}). Reintentando...")
                    response.raise_for_status() 

                logger.error(f"LLM API - Error irrecuperable ({response.status_code}). Mensaje: {response.text}")
                return None

            except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as e:
                if attempt < self.MAX_RETRIES - 1:
                    delay = self.BASE_DELAY * (2 ** attempt) + (random.random() * 0.5)
                    time.sleep(delay)
                else:
                    logger.error(f"LLM API - Fallo después de {self.MAX_RETRIES} intentos. Error final: {e}")
                    return None
            except Exception as e:
                logger.error(f"LLM API - Error de parsing o estructura en la respuesta. Falló con: {e}")
                return None
        
        return None 
        
    def generate_recommendations(self, client_id: int, regional_setting: str) -> Optional[Dict[str, Any]]:
        """
        Main agent workflow: collects data and calls the AI.
        """
        
        catalog = get_products()
        client_profile = get_client_data(client_id)
        media_data = self.user_repository.get_recent_evidences_by_client(client_id) 
        client_purchase_history = self.user_repository.get_recent_purchase_history(client_id)

        if client_profile is None or not catalog:
             return None
        
        visit_evidences_tags = self._get_client_intelligence_tags(client_id, media_data) 
        
        full_prompt = self._build_agent_prompt(
            tags=visit_evidences_tags, catalog=catalog, client_profile=client_profile, 
            regional_setting=regional_setting, client_purchase_history=client_purchase_history
        )
        
        return self.invoke(full_prompt)
