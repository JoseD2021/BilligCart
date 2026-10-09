from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.application.use_cases.generate_response import (
    GenerateResponseUseCase
)

from src.infrastructure.messaging.rabbitmq_ai_client import (
    RabbitMQAIClient
)


ai = APIRouter()


class PromptRequest(BaseModel):
    prompt: str


@ai.post("/generate")
def generate_text(body: PromptRequest):

    try:

        ai_client = RabbitMQAIClient()

        use_case = GenerateResponseUseCase(
            ai_client=ai_client
        )

        result = use_case.execute(
            body.prompt
        )

        return {
            "status": "success",
            "response": result
        }

    except TimeoutError:

        raise HTTPException(
            status_code=504,
            detail=(
                "Tiempo de espera agotado "
                "esperando respuesta de IA"
            )
        )

    except ConnectionError:

        raise HTTPException(
            status_code=503,
            detail=(
                "No fue posible conectarse "
                "al sistema de mensajería"
            )
        )

    except Exception:

        raise HTTPException(
            status_code=500,
            detail="Error interno al generar respuesta"
        )