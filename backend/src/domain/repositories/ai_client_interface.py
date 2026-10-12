from abc import ABC, abstractmethod


class AIClientInterface(ABC):

  @abstractmethod
  def generate_response(self, prompt: str) -> str:
    pass