import requests

from src.domain.repositories.ai_client_interface import AIClientInterface
from src.domain.entities.ai_response import AIResponseSchema


class OllamaClient(AIClientInterface):

    def __init__(self, base_url: str = "http://ollama:11434"):
        self.base_url = base_url

    def generate_response(self, prompt: str) -> str:

        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": "gemma4:e4b",
                "prompt": "Eres un asistente en la creacion de un menu semanal, debes generar el menu de los proximos 7 dias (3 comidas al dia) en base a las preferencias, dietas y restricciones del usurio: "+prompt,
                #instruccion de prueba
                # "prompt": "Eres un asistente experto en nutrición y planificación de menús. Tu tarea es generar un menú semanal completo (7 días, 3 comidas por día: desayuno, almuerzo, cena) basado estrictamente en las preferencias, dietas y restricciones que el usuario proporcione. Instrucción clave: Debes asegurar que el menú cumpla con las restricciones. Si la dieta es vegetariana, ningún ingrediente debe ser carne. Si es baja en carbohidratos, las cantidades deben ser ajustadas. Tu salida debe ser UNA SOLA respuesta en formato JSON que adhiera exactamente a la estructura definida. No incluyas texto explicativo fuera del JSON. Perfil del usuario:"+prompt,
                "stream": False,
                "format": AIResponseSchema.model_json_schema(),
                "options": {
                    "num_ctx": 8192
                }
            },
        )

        response.raise_for_status()

        return response.json().get("response", "")