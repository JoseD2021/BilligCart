from src.domain.repositories.ai_client_interface import AIClientInterface


class GenerateResponseUseCase:

  def __init__(self, ai_client: AIClientInterface):
    self.ai_client = ai_client

  def execute(self, prompt: str, user_id: str | None = None) -> str:
    return self.ai_client.generate_response(prompt, user_id)