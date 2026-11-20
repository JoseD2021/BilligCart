import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.application.use_cases.generate_response import GenerateResponseUseCase
from src.infrastructure.api.v1.dependencies import get_current_user
from src.infrastructure.messaging.rabbitmq_ai_client import RabbitMQAIClient

ai = APIRouter(prefix="/ai", tags=["AI"])


class PromptRequest(BaseModel):
    prompt: str


@ai.post("/generate")
def generate_text(
    body: PromptRequest,
    current_user=Depends(get_current_user),
):
    use_case = GenerateResponseUseCase(ai_client=RabbitMQAIClient())

    try:
        result = use_case.execute(body.prompt, str(current_user.id))
    except TimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail="Tiempo de espera agotado esperando respuesta de IA",
        ) from exc
    except ConnectionError as exc:
        raise HTTPException(
            status_code=503,
            detail="No fue posible conectarse al sistema de mensajería",
        ) from exc

    except Exception:
        logging.getLogger(__name__).exception("Falló la generación de IA user_id=%s", current_user.id)

        raise HTTPException(
            status_code=500,
            detail="Error interno al generar respuesta"
        )
    return {"status": "success", "response": result}
