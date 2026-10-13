from product_visitor import ProductVisitor


class PriceCalculatorVisitor(ProductVisitor):

  def visit_packed_product(self, product) -> float:
    # Regla: precio * unidades
    return product.unit_price * product.units

  def visit_fresh_product(self, product) -> float:
    # Regla: peso * precio por kg
    return product.price_per_kg * product.weight