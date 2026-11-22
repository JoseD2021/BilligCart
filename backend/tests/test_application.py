import json
import unittest
from dataclasses import replace
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from src.application.access_policy import AccessPolicy
from src.application.queries.menu.get_weekly_menu import GetWeeklyMenu
from src.application.use_cases.generate_weekly_menu import GenerateWeeklyMenu
from src.application.use_cases.persist_generated_menu import (
    PersistGeneratedMenuUseCase,
    _interpretar_menu,
)
from src.application.use_cases.preferences import PreferencesUseCase
from src.application.use_cases.shopping import ShoppingUseCase
from src.domain.entities.menu import Menu
from src.domain.entities.plato import Plato
from src.domain.entities.plato_ingrediente import PlatoIngrediente
from src.domain.entities.preferencias import Preferencias
from src.domain.entities.user import User
from src.domain.enums.plato_tipo import PlatoTipo
from src.domain.errors import (
    AccessDenied,
    InvalidRequestBodyError,
    MenuGenerationError,
    OrderNotReady,
    ResourceNotFound,
)
from src.events.application.ai_event_handlers import on_menu_generation_completed
from src.events.contracts.ai_menu_events import MenuGenerationCompleted

USER = User("00000000-0000-0000-0000-000000000001", "user@example.com")


def generated_menu(quantity=100):
    return json.dumps({"menuSemanal": {
        day: {meal: {"name": f"{day} {meal}", "ingredients": [
            {"name": "Arroz", "cantidad": quantity, "unit": "g"},
        ]} for meal in ("desayuno", "almuerzo", "cena")}
        for day in ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo")
    }})


class MemoryMenuData:
    def __init__(self):
        self.menu = Menu.default(USER.id)
        self.menu = replace(self.menu, id=1)
        self.dishes, self.ingredients, self.links = {}, {}, {}
        self.menus = SimpleNamespace(get_current=AsyncMock(side_effect=lambda user_id: self.menu),
                                     create=AsyncMock(side_effect=lambda menu: self.menu))
        self.platos = SimpleNamespace(
            get_by_menu_day=AsyncMock(side_effect=lambda menu_id, day: [p for p in self.dishes.values() if p.day == day]),
            create=AsyncMock(side_effect=self.create_dish), delete_by_id=AsyncMock(side_effect=lambda id: self.dishes.pop(id)),
        )
        self.ingredientes = SimpleNamespace(
            get_all=AsyncMock(side_effect=lambda: list(self.ingredients.values())),
            create=AsyncMock(side_effect=self.create_ingredient),
            get_by_id=AsyncMock(side_effect=lambda id: self.ingredients.get(id)),
        )
        self.relaciones = SimpleNamespace(
            create_many=AsyncMock(side_effect=self.create_links),
            get_by_plato=AsyncMock(side_effect=lambda id: [r for r in self.links.values() if r.plato_id == id]),
            delete_by_plato=AsyncMock(side_effect=self.delete_links),
        )

    def create_dish(self, dish):
        dish = replace(dish, id=len(self.dishes) + 1)
        self.dishes[dish.id] = dish
        return dish

    def create_ingredient(self, ingredient):
        ingredient = replace(ingredient, id=len(self.ingredients) + 1)
        self.ingredients[ingredient.id] = ingredient
        return ingredient

    def create_links(self, links):
        result = []
        for link in links:
            link = replace(link, id=len(self.links) + 1)
            self.links[link.id] = link
            result.append(link)
        return result

    def delete_links(self, plato_id):
        self.links = {id: rel for id, rel in self.links.items() if rel.plato_id != plato_id}

    def persistence(self):
        return PersistGeneratedMenuUseCase(self.menus, self.platos, self.ingredientes, self.relaciones)

    def projection(self):
        return GetWeeklyMenu(self.menus, self.platos, self.ingredientes, self.relaciones)


class DomainTests(unittest.TestCase):
    def test_invalid_dish_is_rejected_without_persistence(self):
        for day, name in ((0, "Arroz"), (8, "Arroz"), (1, "  ")):
            with self.subTest(day=day, name=name), self.assertRaises(InvalidRequestBodyError):
                Plato(1, PlatoTipo.ALMUERZO, name, day)

    def test_invalid_quantities_and_budget_are_rejected(self):
        for value in (-1, 0, float("nan"), float("inf")):
            with self.subTest(quantity=value), self.assertRaises(InvalidRequestBodyError):
                PlatoIngrediente(value, "g", 1, 1)
        for budget in (-1, float("nan"), float("inf")):
            with self.subTest(budget=budget), self.assertRaises(InvalidRequestBodyError):
                Preferencias(USER.id, presupuesto_semanal=budget)

    def test_ai_requires_complete_menu_and_valid_ingredients(self):
        self.assertEqual(len(_interpretar_menu(generated_menu())), 21)
        for response in ("{}", generated_menu(-1), generated_menu(float("nan"))):
            with self.subTest(response=response[:30]), self.assertRaises(MenuGenerationError):
                _interpretar_menu(response)


class ApplicationTests(unittest.IsolatedAsyncioTestCase):
    async def test_menu_and_relations_require_owner(self):
        menus = SimpleNamespace(get_by_id=AsyncMock(return_value=Menu(date(2026, 11, 9), "other", id=1)))
        platos = SimpleNamespace(get_by_id=AsyncMock(return_value=Plato(1, PlatoTipo.CENA, "Cena", 1, id=2)))
        links = SimpleNamespace(get_by_id=AsyncMock(return_value=PlatoIngrediente(1, "g", 2, 1, id=3)))
        access = AccessPolicy(menus, platos, links)
        for action in (access.menu(USER, 1), access.plato(USER, 2), access.relacion(USER, 3)):
            with self.assertRaises(ResourceNotFound):
                await action
        with self.assertRaises(AccessDenied):
            access.catalog_admin(USER)
        access.catalog_admin(replace(USER, role="admin"))

    async def test_persistence_and_weekly_projection_include_21_dishes_and_ingredients(self):
        data = MemoryMenuData()
        self.assertEqual(await data.persistence().execute(USER.id, generated_menu()), 21)
        self.assertEqual(len(data.ingredients), 1)
        self.assertEqual(len(data.links), 21)
        menu = await data.projection().execute(USER.id)
        self.assertEqual(len(menu["dias"]), 7)
        self.assertEqual(menu["dias"][0]["comidas"]["desayuno"]["ingredientes"][0]["nombre"], "Arroz")

    async def test_invalid_ai_does_not_delete_existing_menu(self):
        data = MemoryMenuData()
        await data.persistence().execute(USER.id, generated_menu())
        with self.assertRaises(MenuGenerationError):
            await data.persistence().execute(USER.id, "{}")
        self.assertEqual(len(data.dishes), 21)
        data.platos.delete_by_id.assert_not_awaited()

    async def test_generation_uses_server_preferences_and_waits_for_persistence(self):
        data = MemoryMenuData()
        prefs = PreferencesUseCase(SimpleNamespace(get_by_user_id=AsyncMock(
            return_value=Preferencias(USER.id, restricciones=["Sin gluten"], presupuesto_semanal=150000))))
        ai = SimpleNamespace(generate_response=Mock(return_value=generated_menu()))
        use_case = GenerateWeeklyMenu(prefs, ai, data.persistence(), data.projection())
        result = await use_case.execute(USER.id)
        self.assertIn("Sin gluten", ai.generate_response.call_args.args[0])
        self.assertIn("150000 COP", ai.generate_response.call_args.args[0])
        self.assertEqual(len(data.dishes), 21)
        self.assertEqual(result["id"], 1)

    async def test_preferences_failure_prevents_generation_without_dietary_restrictions(self):
        prefs = SimpleNamespace(get=AsyncMock(side_effect=RuntimeError("database unavailable")))
        ai = SimpleNamespace(generate_response=Mock())
        with self.assertRaises(RuntimeError):
            await GenerateWeeklyMenu(prefs, ai, None, None).execute(USER.id)
        ai.generate_response.assert_not_called()

    async def test_synchronous_generation_is_not_persisted_again_by_event_worker(self):
        persistence = SimpleNamespace(execute=AsyncMock())
        event = MenuGenerationCompleted(request_id="request", model="model", duration_ms=1,
                                        user_id=USER.id, response=generated_menu(), persist_via_events=False)
        await on_menu_generation_completed(event, persistence)
        persistence.execute.assert_not_awaited()
        await on_menu_generation_completed(replace(event, persist_via_events=True), persistence)
        persistence.execute.assert_awaited_once()

    async def test_shopping_aggregates_units_and_refuses_orders_without_prices(self):
        data = MemoryMenuData()
        await data.persistence().execute(USER.id, generated_menu())
        prefs = SimpleNamespace(get=AsyncMock(return_value=Preferencias(USER.id)))
        orders = SimpleNamespace(create=AsyncMock(side_effect=lambda order: order))
        shopping = ShoppingUseCase(data.projection(), prefs, orders)
        result = await shopping.get_list(USER.id)
        self.assertEqual(result.items[0].cantidad, 2100)
        self.assertIsNone(result.ultimos_fetch[1])
        self.assertEqual(result.precios_pendientes, 1)
        self.assertFalse(result.puede_confirmar)
        with self.assertRaises(OrderNotReady):
            await shopping.confirm(USER.id)
        orders.create.assert_not_awaited()
        data.ingredients[1] = replace(data.ingredients[1], price=5000)
        order = await shopping.confirm(USER.id)
        self.assertEqual(order.user_id, USER.id)
        self.assertEqual(order.estado, "pendiente")
        self.assertEqual(order.etapa, 0)
        self.assertIsNone(order.repartidor)
        self.assertEqual(order.total, 5000)
        second = await shopping.confirm(USER.id)
        self.assertEqual(order.checkout_key, second.checkout_key)

    async def test_confirm_can_explicitly_exclude_unpriced_ingredients(self):
        def ingredientes():
            return [
                {"id": 1, "nombre": "Arroz", "cantidad": 100, "unidad": "g", "tienda": "Éxito",
                 "precio": 4000, "ultimo_fetch": None},
                {"id": 2, "nombre": "Leche", "cantidad": 1, "unidad": "unidad", "tienda": None,
                 "precio": None, "ultimo_fetch": None},
            ]

        dias = [{"comidas": {comida: {"ingredientes": ingredientes()}
                             for comida in ("desayuno", "almuerzo", "cena")}} for _ in range(7)]
        weekly = SimpleNamespace(execute=AsyncMock(return_value={"id": 1, "dias": dias}))
        prefs = SimpleNamespace(get=AsyncMock(return_value=Preferencias(USER.id)))
        orders = SimpleNamespace(create=AsyncMock(side_effect=lambda order: order))
        shopping = ShoppingUseCase(weekly, prefs, orders)

        lista = await shopping.get_list(USER.id)
        self.assertTrue(lista.menu_completo)
        self.assertEqual(lista.precios_pendientes, 1)
        with self.assertRaises(OrderNotReady):
            await shopping.confirm(USER.id)

        order = await shopping.confirm(USER.id, omitir_sin_precio=True)
        self.assertEqual([item.ingrediente_id for item in order.items], [1])
        self.assertEqual(order.total, 4000)
        second = await shopping.confirm(USER.id, omitir_sin_precio=True)
        self.assertEqual(order.checkout_key, second.checkout_key)

        incompleta = ShoppingUseCase(SimpleNamespace(execute=AsyncMock(return_value={
            "id": 1, "dias": [{"comidas": {"desayuno": {"ingredientes": ingredientes()}}}],
        })), prefs, orders)
        with self.assertRaises(OrderNotReady):
            await incompleta.confirm(USER.id, omitir_sin_precio=True)

    async def test_compatible_units_are_combined(self):
        def ingredient(amount, unit):
            return {"id": 1, "nombre": "Arroz", "cantidad": amount, "unidad": unit, "tienda": None,
                    "precio": 4000, "ultimo_fetch": "2026-11-01T10:00:00+00:00"}
        weekly = SimpleNamespace(execute=AsyncMock(return_value={"id": 1, "dias": [{"comidas": {
            "desayuno": {"ingredientes": [ingredient(1, "kg")]},
            "almuerzo": {"ingredientes": [ingredient(500, "g")]},
        }}]}))
        shopping = ShoppingUseCase(weekly, SimpleNamespace(get=AsyncMock(return_value=Preferencias(USER.id))), None)
        result = await shopping.get_list(USER.id)
        self.assertEqual(result.items[0].cantidad, 1500)
        self.assertEqual(result.items[0].unidad, "g")
        self.assertEqual(result.ultimos_fetch[1], "2026-11-01T10:00:00+00:00")
        self.assertFalse(result.puede_confirmar)  # Solo dos comidas: menú incompleto.

    async def test_empty_menu_and_missing_order_have_explicit_results(self):
        weekly = SimpleNamespace(execute=AsyncMock(return_value=None))
        prefs = SimpleNamespace(get=AsyncMock(return_value=Preferencias(USER.id)))
        orders = SimpleNamespace(get_by_id=AsyncMock(return_value=None))
        shopping = ShoppingUseCase(weekly, prefs, orders)
        self.assertEqual((await shopping.get_list(USER.id)).items, [])
        with self.assertRaises(ResourceNotFound):
            await shopping.order(USER.id, "other-order")
