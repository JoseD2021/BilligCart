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
            "model": "granite4.2:8b",
            "prompt": prompt,
            "stream": False,
            "format": AIResponseSchema.model_json_schema(),
            "options": {
                "num_ctx": 10000
            } 
        },
    )
    response.raise_for_status()
    return response.json().get("response", "")