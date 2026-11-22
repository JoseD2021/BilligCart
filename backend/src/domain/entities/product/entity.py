from __future__ import annotations

from abc import ABC, abstractmethod

from product_visitor import ProductVisitor


class Product(ABC):

  @abstractmethod
  def accept(self, visitor: ProductVisitor) -> float:
    pass