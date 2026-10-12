
import os

import requests

from src.domain.repositories.ai_client_interface import AIClientInterface
from src.domain.entities.ai_response import AIResponseSchema


class OllamaClient(AIClientInterface):

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
    ):
        self.base_url = (
            base_url
            or os.getenv("OLLAMA_BASE_URL")
            or "http://ollama:11434"
        ).rstrip("/")

        self.model = (
            model
            or os.getenv("OLLAMA_MODEL")
            or "gemma3:270m"
        )

    def generate_response(self, prompt: str) -> str:
        full_prompt = (
            "Eres un asistente especializado en la creación de menús "
            "semanales. Genera un menú para los próximos 7 días, "
            "con desayuno, almuerzo y cena cada día. "
            "Respeta las preferencias, dietas y restricciones del usuario. "
            "Cada comida debe tener un nombre concreto y una lista "
            "de ingredientes con cantidades numéricas y unidades "
            "compatibles con el esquema JSON proporcionado. "
            "Devuelve únicamente el JSON solicitado, sin explicaciones "
            "adicionales ni precios. "
            f"Solicitud del usuario: {prompt}"
        )

        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,
                "format": AIResponseSchema.model_json_schema(),
                "options": {
                    "num_ctx": 8192,
                },
            },
            timeout=400,
        )

        response.raise_for_status()

        data = response.json()
        generated_text = data.get("response", "")

        if not isinstance(generated_text, str) or not generated_text.strip():
            raise RuntimeError(
                "Ollama devolvió una respuesta vacía."
            )

        return generated_text
