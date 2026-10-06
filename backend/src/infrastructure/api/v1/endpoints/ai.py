from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.application.use_cases.generate_response import GenerateResponseUseCase
from src.infrastructure.ai.ollama import OllamaClient

# ai = APIRouter(prefix="/ai", tags=["AI"])
ai = APIRouter()

class PromptRequest(BaseModel):
  prompt: str


@ai.post("/generate")
def generate_text(body: PromptRequest):
  try:
    ai_client = OllamaClient()
    use_case = GenerateResponseUseCase(ai_client=ai_client)

    result = use_case.execute(body.prompt)
    return {"status": "success", "response": result}
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))