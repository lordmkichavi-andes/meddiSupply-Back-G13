import os
import time
import json
import requests
import random
import logging
from typing import List, Dict, Any, Optional
from src.domain.interfaces import UserRepository
import logging
import codecs

logger = logging.getLogger(__name__)

class RecommendationAgent:
    """
    Encapsula toda la lógica de obtención de inteligencia y la invocación 
    al LLM de Gemini.
    """
    
    def __init__(self, user_repository: UserRepository):
        
        self.MAX_RETRIES = 5
        self.BASE_DELAY = 1.0
        self.user_repository = user_repository
        self.LLM_PROVIDER = os.getenv("ACTIVE_LLM", "GEMINI").upper()
        self.API_KEY = os.getenv('LLM_API_KEY') 
        self.API_URL = os.getenv("LLM_API_URL", self._get_default_url(self.LLM_PROVIDER))
        self.MODEL_NAME = os.getenv('LLM_MODEL')
        
        if not self.API_KEY:
            logger.warning(f"La variable LLM_API_KEY está vacía. El proveedor {self.LLM_PROVIDER} no podrá ser invocado.")
            
        if not self.API_URL:
            logger.error(f"La URL de la API para el proveedor {self.LLM_PROVIDER} es inválida o no está definida.")


    def _get_default_url(self, provider: str) -> str:
        """Define URLs por defecto para proveedores conocidos si LLM_API_URL falta."""
        provider = provider.upper()
        
        if provider == 'GEMINI':
            return "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent"
        
        if provider == 'OPENAI':
            return "https://api.openai.com/v1/chat/completions" 
        
        if provider == 'CLAUDE':
            return "https://api.anthropic.com/v1/messages"
        
        return ""
        
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
        
        if self.LLM_PROVIDER == 'GEMINI':
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

        elif self.LLM_PROVIDER == 'OPENAI':
            if not self.MODEL_NAME:
                logger.error("LLM ERROR: La variable LLM_MODEL es requerida para OpenAI.")
                return None
                
            payload = {
                "model": self.MODEL_NAME, 
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"},
            }

        elif self.LLM_PROVIDER == 'CLAUDE':
            if not self.MODEL_NAME:
                logger.error("LLM ERROR: La variable LLM_MODEL es requerida para Claude.")
                return None
                
            payload = {
                "model": self.MODEL_NAME, 
                "system": "Eres un Motor de Razonamiento IA (LLM) para MediSupply. Genera una lista de tres (3) recomendaciones de productos y devuelve SOLO el objeto JSON.",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                
                "max_tokens": 4096, 
                "temperature": 0.1,  

                "tool_choice": {"type": "tool", "name": "recommendation_schema"},
                "tools": [
                    {
                        "name": "recommendation_schema",
                        "description": "Herramienta usada para forzar la salida a un objeto JSON específico que contiene una lista de recomendaciones.",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "recommendations": {
                                    "type": "array",
                                    "description": "Una lista de tres objetos de recomendación.",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "product_sku": {"type": "string"},
                                            "product_name": {"type": "string"},
                                            "score": {"type": "number"},
                                            "reasoning": {"type": "string"}
                                        },
                                        "required": ["product_sku", "product_name", "score", "reasoning"]
                                    }
                                }
                            }
                        }
                    }
                ]
            }

        endpoint_url = self.API_URL
        
        if not self.API_KEY:
            logger.error(f"LLM ERROR: La variable LLM_API_KEY {self.API_KEY} está vacía. No se puede llamar al servicio de {self.LLM_PROVIDER}.")
            return None

        if self.LLM_PROVIDER == 'GEMINI':
            endpoint_url = f"{self.API_URL}?key={self.API_KEY}"

        elif self.LLM_PROVIDER == 'OPENAI':
            if self.API_KEY:
                headers['Authorization'] = f'Bearer {self.API_KEY}'

        elif self.LLM_PROVIDER == 'CLAUDE':
            if self.API_KEY:
                headers['x-api-key'] = self.API_KEY
                headers['anthropic-version'] = '2023-06-01'
        
        if not endpoint_url or (not self.API_KEY and self.LLM_PROVIDER != 'GEMINI'): 
            logger.error(f"LLM ERROR: Configuración incompleta para el proveedor {self.LLM_PROVIDER}.")
            return None

        for attempt in range(self.MAX_RETRIES):
            try:
                response = requests.post(
                    endpoint_url,
                    json=payload, 
                    headers=headers, 
                    timeout=60
                )
                
                if response.status_code == 200:
                    response.encoding = 'utf-8'
                    result = response.json()
                    
                    json_str = self._extract_response(result)
                    
                    if json_str:
                        return json.loads(json_str)
                    else:
                        logger.error(f"LLM API - Proveedor {self.LLM_PROVIDER}: Respuesta 200, pero el texto generado está vacío.")
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
        
        catalog = self.user_repository.get_products()
        logger.error(f"catalog: {catalog}")
        client_profile = self.user_repository.db_get_client_data(client_id)
        logger.error(f"client_profile: {client_profile}")
        media_data = self.user_repository.get_recent_evidences_by_client(client_id) 
        logger.error(f"media_data: {media_data}")
        client_purchase_history = self.user_repository.get_recent_purchase_history(client_id)

        if not catalog:
            return None
        
        visit_evidences_tags = self._get_client_intelligence_tags(client_id, media_data) 
        
        full_prompt = self._build_agent_prompt(
            tags=visit_evidences_tags,
            catalog=catalog,
            client_profile=client_profile or {},
            regional_setting=regional_setting,
            client_purchase_history=client_purchase_history or {}
        )
        
        return self.invoke(full_prompt)

    def _extract_response(self, response_json: Dict[str, Any]) -> Optional[str]:
        """Extrae la cadena JSON de texto de la respuesta del proveedor activo."""
        
        if self.LLM_PROVIDER == 'GEMINI':
            if response_json.get('candidates') and response_json['candidates'][0]['content']['parts'][0]['text']:
                raw_text = response_json['candidates'][0]['content']['parts'][0]['text']
                
                try:
                    escaped_text = codecs.decode(raw_text, 'unicode_escape') 
                    corrected_text = escaped_text.encode('latin1').decode('utf8')
                    data = json.loads(corrected_text)
                    return json.dumps(data, ensure_ascii=False)
                    
                except Exception as e:
                    logger.error(f"Gemini: Fallo en la decodificación/parsing JSON. Error: {e}. Texto crudo (corrupto): {raw_text[:50]}...")
                    return None
        
        if self.LLM_PROVIDER == 'OPENAI':
            if response_json.get('choices') and response_json['choices'][0]['message']['content']:
                return response_json['choices'][0]['message']['content']
        
        if self.LLM_PROVIDER == 'CLAUDE':
            if response_json.get('content') and response_json['content'][0]['type'] == 'tool_use':
                tool_input = response_json['content'][0]['input']
                return json.dumps(tool_input)
            
            if response_json.get('content') and response_json['content'][0]['text']:
                 return response_json['content'][0]['text']
        
        logger.error(f"Fallo al extraer la respuesta del proveedor {self.LLM_PROVIDER}. Estructura inesperada.")
        return None
