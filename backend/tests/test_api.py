import unittest
from dataclasses import replace
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from src.application.commands.ingrediente.scrape_ingrediente import ScrapeIngredienteCommand
from src.domain.entities.ingrediente import Ingrediente
from src.domain.entities.menu import Menu
from src.domain.entities.plato import Plato
from src.domain.entities.plato_ingrediente import PlatoIngrediente
from src.domain.entities.user import User
from src.domain.enums.plato_tipo import PlatoTipo
from src.domain.errors import InvalidCredentials
from src.infrastructure.api.v1 import dependencies as deps
from src.infrastructure.api.v1.app import create_app

USER = User("00000000-0000-0000-0000-000000000001", "user@example.com")
DISH = {"menu_id": 1, "type": "Desayuno", "name": "Arroz", "day": 1}
LINK = {"plato_id": 1, "ingrediente_id": 1, "quantity": 100, "unit": "g"}


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.auth = SimpleNamespace(get_user_from_token=AsyncMock(return_value=USER))
        self.menus = SimpleNamespace(
            get_by_id=AsyncMock(side_effect=lambda id: Menu(date(2026, 11, 9), USER.id if id == 1 else "other", id=id)),
            get_current=AsyncMock(return_value=None),
        )
        self.platos = SimpleNamespace(
            get_by_id=AsyncMock(return_value=Plato(2, PlatoTipo.DESAYUNO, "Arroz", 1, id=2)),
            get_by_menu_day=AsyncMock(return_value=[]), create=AsyncMock(), update=AsyncMock(), delete_by_id=AsyncMock(),
        )
        self.links = SimpleNamespace(
            get_by_id=AsyncMock(return_value=PlatoIngrediente(100, "g", 2, 1, id=2)),
            create_many=AsyncMock(), create=AsyncMock(), update=AsyncMock(), delete_by_id=AsyncMock(),
        )
        self.ingredients = SimpleNamespace(create=AsyncMock(), update=AsyncMock(), delete_by_id=AsyncMock())
        self.prefs = SimpleNamespace(get_by_user_id=AsyncMock(return_value=None), save=AsyncMock(side_effect=lambda p: p))
        overrides = {
            deps.get_auth_service: self.auth, deps.get_menu_repository: self.menus,
            deps.get_plato_repository: self.platos, deps.get_plato_ingrediente_repository: self.links,
            deps.get_ingrediente_repository: self.ingredients, deps.get_preferencias_repository: self.prefs,
        }
        for dependency, value in overrides.items():
            self.app.dependency_overrides[dependency] = self.override(value)
        self.client = TestClient(self.app)
        self.headers = {"Authorization": "Bearer private-test-token"}

    @staticmethod
    def override(value):
        def provide():
            return value
        return provide

    def test_all_catalog_routes_require_authentication(self):
        routes = [
            ("POST", "/plato/create", DISH), ("PUT", "/plato/update/1", DISH),
            ("GET", "/plato/day/1?menu_id=1", None), ("DELETE", "/plato/delete/1", None),
            ("POST", "/ingrediente/create", {"name": "Arroz"}),
            ("PUT", "/ingrediente/update/1", {"name": "Arroz"}),
            ("POST", "/ingrediente/fetch/1", None), ("GET", "/ingrediente/get/1", None),
            ("DELETE", "/ingrediente/delete/1", None),
            ("POST", "/plato-ingrediente/create", LINK),
            ("POST", "/plato-ingrediente/create-many", [LINK]),
            ("PATCH", "/plato-ingrediente/update/1", {"quantity": 1, "unit": "g"}),
            ("GET", "/plato-ingrediente/get/1", None), ("GET", "/plato-ingrediente/get-by-plato/1", None),
            ("DELETE", "/plato-ingrediente/delete/1", None), ("DELETE", "/plato-ingrediente/delete-by-plato/1", None),
            ("GET", "/menu/weekly", None), ("POST", "/menu/generate", None),
            ("GET", "/preferencias", None), ("GET", "/compras", None), ("GET", "/pedidos/current", None),
            ("POST", "/compras/confirmar", None),
        ]
        for method, route, body in routes:
            with self.subTest(method=method, route=route):
                response = self.client.request(method, "/v1" + route, json=body)
                self.assertEqual(response.status_code, 401, response.text)
                self.assertEqual(response.headers["www-authenticate"], "Bearer")
        self.platos.create.assert_not_awaited()
        self.links.create_many.assert_not_awaited()

    def test_invalid_token_is_rejected(self):
        self.auth.get_user_from_token.side_effect = InvalidCredentials("expired")
        response = self.client.get("/v1/menu/weekly", headers=self.headers)
        self.assertEqual(response.status_code, 401)

    def test_other_users_menu_cannot_be_read_or_written(self):
        for method, route, body in (
            ("GET", "/plato/day/1?menu_id=2", None),
            ("POST", "/plato/create", dict(DISH, menu_id=2)),
            ("PUT", "/plato/update/2", DISH),
            ("DELETE", "/plato/delete/2", None),
            ("GET", "/plato-ingrediente/get/2", None),
            ("DELETE", "/plato-ingrediente/delete/2", None),
        ):
            with self.subTest(method=method, route=route):
                response = self.client.request(method, "/v1" + route, json=body, headers=self.headers)
                self.assertEqual(response.status_code, 404, response.text)
        self.platos.create.assert_not_awaited()
        self.platos.update.assert_not_awaited()
        self.platos.delete_by_id.assert_not_awaited()
        self.links.delete_by_id.assert_not_awaited()

    def test_update_cannot_move_owned_dish_into_foreign_menu(self):
        self.platos.get_by_id.return_value = Plato(1, PlatoTipo.DESAYUNO, "Arroz", 1, id=1)
        response = self.client.put("/v1/plato/update/1", json=dict(DISH, menu_id=2), headers=self.headers)
        self.assertEqual(response.status_code, 404)
        self.platos.update.assert_not_awaited()

    def test_owner_can_create_dish_and_get_its_persisted_id(self):
        self.platos.create.side_effect = lambda plato: replace(plato, id=10)
        response = self.client.post("/v1/plato/create", json=DISH, headers=self.headers)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["id"], 10)
        self.assertEqual(response.json()["type"], "Desayuno")

    def test_mixed_batch_is_authorized_before_any_insert(self):
        self.platos.get_by_id.side_effect = lambda id: Plato(id, PlatoTipo.DESAYUNO, "Arroz", 1, id=id)
        response = self.client.post("/v1/plato-ingrediente/create-many", json=[LINK, dict(LINK, plato_id=2)], headers=self.headers)
        self.assertEqual(response.status_code, 404)
        self.links.create_many.assert_not_awaited()

    def test_catalog_mutations_require_admin(self):
        for method, route, body in (
            ("POST", "/ingrediente/create", {"name": "Arroz"}),
            ("PUT", "/ingrediente/update/1", {"name": "Arroz"}),
            ("DELETE", "/ingrediente/delete/1", None),
        ):
            with self.subTest(method=method):
                response = self.client.request(method, "/v1" + route, json=body, headers=self.headers)
                self.assertEqual(response.status_code, 403, response.text)
        self.ingredients.create.assert_not_awaited()

    def test_any_authenticated_user_can_fetch_ingredient_price(self):
        handler = SimpleNamespace(handle=AsyncMock(return_value=Ingrediente.default("Arroz")))
        self.app.dependency_overrides[deps.get_scrape_ingredient_handler] = self.override(handler)
        response = self.client.post("/v1/ingrediente/fetch/1", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["name"], "Arroz")
        handler.handle.assert_awaited_once_with(ScrapeIngredienteCommand(user_id=USER.id, id=1))

    def test_preferences_use_authenticated_user_and_reject_user_id(self):
        response = self.client.put("/v1/preferencias", json={"restricciones": ["Sin gluten"], "presupuesto_semanal": 20000}, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["user_id"], USER.id)
        self.assertEqual(self.prefs.save.call_args.args[0].presupuesto_semanal, 20000)
        response = self.client.put("/v1/preferencias", json={"user_id": "other"}, headers=self.headers)
        self.assertEqual(response.status_code, 422)

    def test_logs_have_request_id_status_and_no_token(self):
        with self.assertLogs("billigcart.api", level="INFO") as logs:
            response = self.client.get("/v1/menu/weekly", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn("X-Request-ID", response.headers)
        output = "\n".join(logs.output)
        self.assertIn(response.headers["X-Request-ID"], output)
        self.assertIn("status=200", output)
        self.assertNotIn("private-test-token", output)

    def test_removed_stub_is_no_longer_an_endpoint(self):
        response = self.client.put("/v1/menu/update", json={"user_id": USER.id, "menu_id": 1}, headers=self.headers)
        self.assertEqual(response.status_code, 404)

    def test_generated_menu_endpoint_returns_persisted_projection(self):
        handler = SimpleNamespace(execute=AsyncMock(return_value={"id": 1, "dias": []}))
        self.app.dependency_overrides[deps.get_generate_weekly_menu] = self.override(handler)
        response = self.client.post("/v1/menu/generate", headers=self.headers)
        self.assertEqual(response.status_code, 201)
        handler.execute.assert_awaited_once_with(USER.id)

    def test_timeout_and_database_failure_do_not_expose_internal_details(self):
        handler = SimpleNamespace(execute=AsyncMock(side_effect=TimeoutError()))
        self.app.dependency_overrides[deps.get_generate_weekly_menu] = self.override(handler)
        self.assertEqual(self.client.post("/v1/menu/generate", headers=self.headers).status_code, 504)
        self.menus.get_current.side_effect = RuntimeError("secret database information")
        response = self.client.get("/v1/menu/weekly", headers=self.headers)
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("secret", response.text)
        self.assertIn("X-Request-ID", response.headers)
