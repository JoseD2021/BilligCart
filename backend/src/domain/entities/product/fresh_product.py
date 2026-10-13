from entity import Product


class FreshProduct(Product):

  def __init__(self, name: str, price_per_kg: float, weight: float):
    self.name = name
    self.price_per_kg = price_per_kg
    self.weight = weight 

  def accept(self, visitor) -> float:
    return visitor.visit_fresh_product(self)