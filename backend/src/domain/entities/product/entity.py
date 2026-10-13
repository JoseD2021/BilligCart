from abc import ABC, abstractmethod


class Product(ABC):

  @abstractmethod
  def accept(self, visitor: "ProductVisitor") -> float:
    pass