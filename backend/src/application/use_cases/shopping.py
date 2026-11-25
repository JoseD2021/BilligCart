import hashlib
import json
from dataclasses import asdict, replace
from uuid import uuid4

from src.application.queries.menu.get_weekly_menu import GetWeeklyMenu
from src.application.use_cases.preferences import PreferencesUseCase
from src.domain.entities.compra import ShoppingItem, ShoppingList
from src.domain.entities.pedido import Pedido
from src.domain.errors import (
    AccessDenied,
    InvalidOrderState,
    InvalidRequestBodyError,
    OrderNotReady,
    ResourceNotFound,
)
from src.domain.repositories.pedido_repository import PedidoRepository

# Las cantidades se agregan en una unidad común; el precio del catálogo es
# una referencia del producto encontrado, sin información de tamaño de empaque.
UNITS = {"kg": ("g", 1000), "kilogramo": ("g", 1000), "g": ("g", 1),
         "gr": ("g", 1), "gramos": ("g", 1), "l": ("ml", 1000),
         "litro": ("ml", 1000), "ml": ("ml", 1), "unidad": ("unidad", 1),
         "unidades": ("unidad", 1)}


class ShoppingUseCase:
    def __init__(self, weekly: GetWeeklyMenu, preferences: PreferencesUseCase, orders: PedidoRepository):
        self.weekly, self.preferences, self.orders = weekly, preferences, orders

    async def get_list(self, user_id: str) -> ShoppingList:
        menu = await self.weekly.execute(user_id)
        prefs = await self.preferences.get(user_id)
        items = {}
        ultimos_fetch = {}
        comidas = 0
        if menu:
            for dia in menu["dias"]:
                for comida in dia["comidas"].values():
                    comidas += 1
                    for ing in comida["ingredientes"]:
                        ultimos_fetch[ing["id"]] = ing.get("ultimo_fetch")
                        raw_unit = ing["unidad"].strip().lower()
                        unit, factor = UNITS.get(raw_unit, (raw_unit, 1))
                        key = f"{ing['id']}:{unit}"
                        quantity = ing["cantidad"] * factor
                        if key in items:
                            items[key] = replace(items[key], cantidad=items[key].cantidad + quantity)
                        else:
                            items[key] = ShoppingItem(key, ing["id"], ing["nombre"], quantity, unit,
                                                      ing["tienda"], ing["precio"])
        result = sorted(items.values(), key=lambda item: item.id)
        pending = sum(item.precio is None for item in result)
        menu_completo = bool(result) and comidas == 21
        # Un único precio de referencia por ingrediente, incluso si hay unidades distintas.
        prices = {item.ingrediente_id: item.precio for item in result}
        total = round(sum(price for price in prices.values() if price is not None), 2)
        return ShoppingList(menu["id"] if menu else None, prefs.presupuesto_semanal, total,
                            result, menu_completo and pending == 0, menu_completo, pending,
                            ultimos_fetch)

    async def confirm(self, user_id: str, omitir_sin_precio: bool = False,
                      items_ids: list[str] | None = None) -> Pedido:
        shopping = await self.get_list(user_id)
        if not shopping.menu_completo:
            raise OrderNotReady("Se requiere un menú completo para confirmar el pedido.")
        items = shopping.items
        if items_ids is not None:
            # El usuario eligió qué productos comprar: solo esos entran al pedido.
            wanted = set(items_ids)
            if wanted - {item.id for item in items}:
                raise InvalidRequestBodyError("La lista de compras cambió. Actualízala e inténtalo de nuevo.")
            items = [item for item in items if item.id in wanted]
            if any(item.precio is None for item in items):
                raise OrderNotReady("Hay productos seleccionados que no tienen precio.")
        else:
            if shopping.precios_pendientes and not omitir_sin_precio:
                raise OrderNotReady("Faltan precios para algunos ingredientes. Puedes confirmar sin incluirlos.")
            if omitir_sin_precio:
                items = [item for item in items if item.precio is not None]
        if not items:
            raise OrderNotReady("No hay ingredientes con precio para confirmar el pedido.")
        # Un único precio de referencia por ingrediente, igual que en get_list.
        prices = {item.ingrediente_id: item.precio for item in items}
        total = round(sum(price for price in prices.values() if price is not None), 2)
        snapshot = json.dumps({"menu_id": shopping.menu_id, "items": [asdict(item) for item in items]},
                              sort_keys=True, ensure_ascii=False)
        key = hashlib.sha256(snapshot.encode()).hexdigest()
        return await self.orders.create(Pedido(str(uuid4()), user_id, shopping.menu_id, key,
                                               items, total, estado="pendiente"))

    async def set_delivery(self, user_id: str, order_id: str, envio: dict) -> Pedido:
        order = await self.orders.get_by_id(user_id, order_id)
        if order is None:
            raise ResourceNotFound("Pedido no encontrado.")
        if order.estado == "entregado":
            raise InvalidOrderState("El pedido ya fue entregado.")
        updated = await self.orders.set_envio(user_id, order_id, envio)
        if updated is None:
            raise ResourceNotFound("Pedido no encontrado.")
        return updated

    async def current_order(self, user_id: str):
        return await self.orders.get_current(user_id)

    async def list_orders(self, user_id: str):
        return await self.orders.list_for_user(user_id)

    async def order(self, user_id: str, order_id: str):
        order = await self.orders.get_by_id(user_id, order_id)
        if order is None:
            raise ResourceNotFound("Pedido no encontrado.")
        return order

    async def available_for_courier(self):
        return await self.orders.list_available()

    async def assigned_to_courier(self, courier_id: str):
        return await self.orders.list_assigned(courier_id)

    async def accept(self, courier_id: str, order_id: str):
        order = await self.orders.assign(order_id, courier_id)
        if order is None:
            raise ResourceNotFound("Pedido no encontrado.")
        if order.repartidor_id != courier_id:
            raise AccessDenied("El pedido ya fue tomado por otro repartidor.")
        return order

    async def update_status(self, courier_id: str, order_id: str, estado: str):
        if estado not in ("confirmado", "en_camino", "entregado"):
            raise InvalidRequestBodyError("Estado inválido.")
        current = await self.orders.get_by_id_for_courier(courier_id, order_id)
        if current is None:
            raise ResourceNotFound("Pedido no encontrado o no asignado.")
        allowed = {"confirmado": {"confirmado", "en_camino"}, "en_camino": {"en_camino", "entregado"}, "entregado": {"entregado"}}
        if estado not in allowed.get(current.estado, set()):
            raise InvalidOrderState(f"No se puede pasar de {current.estado} a {estado}.")
        updated = await self.orders.update_estado(order_id, courier_id, estado)
        if updated is None:
            raise ResourceNotFound("Pedido no encontrado o no asignado.")
        return updated
