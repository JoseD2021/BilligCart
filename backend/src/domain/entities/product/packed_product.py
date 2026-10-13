from entity import Product


class PackedProduct(Product):

  def __init__(self, name: str, unit_price: float, units: int):
    self.name = name
    self.unit_price = unit_price
    self.units = units

  def accept(self, visitor) -> float:
    return visitor.visit_packed_product(self)