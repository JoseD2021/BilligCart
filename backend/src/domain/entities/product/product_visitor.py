from abc import ABC, abstractmethod


class ProductVisitor(ABC):

  @abstractmethod
  def visit_packed_product(self, product) -> float:
    pass

  @abstractmethod
  def visit_fresh_product(self, product) -> float:
    pass