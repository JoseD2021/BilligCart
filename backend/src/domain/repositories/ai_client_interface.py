from abc import ABC, abstractmethod


class AIClientInterface(ABC):

  @abstractmethod
  def generate_response(self, prompt: str, user_id: str | None = None) -> str:
    pass