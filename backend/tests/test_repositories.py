import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from src.domain.entities.ingrediente import Ingrediente
from src.domain.entities.pedido import Pedido
from src.domain.entities.plato import Plato
from src.domain.entities.plato_ingrediente import PlatoIngrediente
from src.domain.entities.preferencias import Preferencias
from src.domain.enums.plato_tipo import PlatoTipo
from src.domain.enums.tienda import Tienda
from src.domain.errors import InvalidRole
from src.infrastructure.supabase.auth_service import SupabaseAuthService
from src.infrastructure.supabase.repositories.ingrediente_repository import (
    SupabaseIngredienteRepository,
)
from src.infrastructure.supabase.repositories.pedido_repository import (
    SupabasePedidoRepository,
)
from src.infrastructure.supabase.repositories.plato_ingrediente_repository import (
    SupabasePlatoIngredienteRepository,
)
from src.infrastructure.supabase.repositories.plato_repository import (
    SupabasePlatoRepository,
)
from src.infrastructure.supabase.repositories.preferencias_repository import (
    SupabasePreferenciasRepository,
)


def database(row):
    query = MagicMock()
    for name in ("insert", "update", "upsert", "select", "eq", "maybe_single", "order", "limit"):
        getattr(query, name).return_value = query
    query.execute = AsyncMock(return_value=SimpleNamespace(data=[row]))
    client = MagicMock()
    client.table.return_value = query
    return client, query


class RepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_and_update_return_dish_entities_with_database_ids(self):
        row = {"id": 10, "menu_id": 1, "type": "Cena", "name": "Arroz", "day": 1, "description": None}
        client, _ = database(row)
        repository = SupabasePlatoRepository(client)
        entity = await repository.create(Plato(1, PlatoTipo.CENA, "Arroz", 1))
        self.assertIsInstance(entity, Plato)
        self.assertEqual(entity.id, 10)
        self.assertIs(entity.type, PlatoTipo.CENA)
        self.assertIsInstance(await repository.update(entity), Plato)

    async def test_ingredient_dates_and_enums_are_converted_on_all_reads_and_writes(self):
        row = {"id": 1, "name": "Arroz", "last_updated": "2026-11-15T10:30:00+00:00", "shop": "Exito", "price": 5000, "url": "https://example.com"}
        client, _ = database(row)
        repository = SupabaseIngredienteRepository(client)
        for entity in (await repository.create(Ingrediente.default("Arroz")), await repository.get_by_id(1)):
            self.assertIsInstance(entity, Ingrediente)
            self.assertIsInstance(entity.last_updated, datetime)
            self.assertIs(entity.shop, Tienda.Exito)

    async def test_bulk_relations_return_entities(self):
        row = {"id": 1, "plato_id": 2, "ingrediente_id": 3, "quantity": 100, "unit": "g"}
        client, query = database(row)
        repository = SupabasePlatoIngredienteRepository(client)
        result = await repository.create_many([PlatoIngrediente(100, "g", 2, 3)])
        self.assertIsInstance(result[0], PlatoIngrediente)
        query.execute.reset_mock()
        self.assertEqual(await repository.create_many([]), [])
        query.execute.assert_not_awaited()

    async def test_preferences_preserve_business_fields(self):
        row = {"id": 1, "user_id": "user", "restricciones": ["Vegano"], "presupuesto_semanal": 150000}
        client, query = database(row)
        result = await SupabasePreferenciasRepository(client).save(Preferencias("user", restricciones=["Vegano"], presupuesto_semanal=150000))
        self.assertIsInstance(result, Preferencias)
        self.assertEqual(result.restricciones, ["Vegano"])
        self.assertEqual(query.upsert.call_args.args[0]["presupuesto_semanal"], 150000)

    async def test_admin_role_comes_from_trusted_metadata(self):
        client = SimpleNamespace(auth=SimpleNamespace(get_user=AsyncMock(return_value=SimpleNamespace(user=SimpleNamespace(
            id="user", email="user@example.com", app_metadata={}, user_metadata={"role": "admin"},
        )))))
        user = await SupabaseAuthService(client).get_user_from_token("token")
        self.assertEqual(user.role, "user")

    async def test_admin_role_from_database_is_not_downgraded_to_user(self):
        client, _ = database({"rol": "admin"})
        auth_user = SimpleNamespace(id="user", email="user@example.com")
        client.auth = SimpleNamespace(
            get_user=AsyncMock(return_value=SimpleNamespace(user=auth_user))
        )
        user = await SupabaseAuthService(client).get_user_from_token("token")
        self.assertEqual(user.role, "admin")

    async def test_role_lookup_uses_trusted_client_after_login_mutates_auth_client(self):
        auth_user = SimpleNamespace(id="user", email="user@example.com")
        auth_client = SimpleNamespace(auth=SimpleNamespace(
            get_user=AsyncMock(return_value=SimpleNamespace(user=auth_user))
        ))
        role_client, _ = database({"rol": "admin"})
        user = await SupabaseAuthService(auth_client, role_client).get_user_from_token("token")
        self.assertEqual(user.role, "admin")

    async def test_sign_up_persists_selected_role_with_trusted_client(self):
        auth_client = SimpleNamespace(auth=SimpleNamespace(sign_up=AsyncMock(return_value=SimpleNamespace(
            user=SimpleNamespace(id="uid", email="repartidor@example.com"), session=None,
        ))))
        role_client, role_query = database(None)
        result = await SupabaseAuthService(auth_client, role_client).sign_up(
            "repartidor@example.com", "secret1", "repartidor"
        )
        self.assertEqual(result.user.role, "repartidor")
        self.assertIsNone(result.session)
        role_query.upsert.assert_called_once_with(
            {"user_id": "uid", "rol": "repartidor"}, on_conflict="user_id"
        )
        role_query.execute.assert_awaited()

    async def test_sign_up_rejects_admin_and_unknown_roles(self):
        auth_client = SimpleNamespace(auth=SimpleNamespace(sign_up=AsyncMock()))
        role_client, _ = database(None)
        service = SupabaseAuthService(auth_client, role_client)
        for role in ("admin", "otro"):
            with self.subTest(role=role), self.assertRaises(InvalidRole):
                await service.sign_up("user@example.com", "secret1", role)
        auth_client.auth.sign_up.assert_not_awaited()

    async def test_duplicate_checkout_does_not_overwrite_order_status(self):
        row = {"id": "order", "user_id": "user", "menu_id": 1, "checkout_key": "key", "items": [], "total": 5000, "estado": "en_camino"}
        client, query = database(row)
        result = await SupabasePedidoRepository(client).create(Pedido("new-order", "user", 1, "key", [], 5000))
        self.assertTrue(query.upsert.call_args.kwargs["ignore_duplicates"])
        self.assertNotIn("etapa", query.upsert.call_args.args[0])
        self.assertEqual(result.estado, "en_camino")
        self.assertEqual(result.id, "order")

    async def test_order_state_is_read_only_from_estado_column(self):
        row = {"id": "order", "user_id": "user", "menu_id": 1, "checkout_key": "key", "items": [], "total": 5000, "estado": "entregado", "etapa": 0}
        client, _ = database(row)
        result = await SupabasePedidoRepository(client).get_by_id("user", "order")
        self.assertEqual(result.estado, "entregado")

    async def test_order_read_always_filters_owner(self):
        row = {"id": "order", "user_id": "user", "menu_id": 1, "checkout_key": "key", "items": [], "total": 5000, "estado": "pendiente"}
        client, query = database(row)
        await SupabasePedidoRepository(client).get_by_id("user", "order")
        query.eq.assert_any_call("user_id", "user")
        query.eq.assert_any_call("id", "order")

    async def test_order_list_filters_owner_and_returns_all_orders(self):
        row = {"id": "order", "user_id": "user", "menu_id": 1, "checkout_key": "key", "items": [], "total": 5000, "estado": "pendiente"}
        client, query = database(row)
        result = await SupabasePedidoRepository(client).list_for_user("user")
        self.assertEqual([order.id for order in result], ["order"])
        query.eq.assert_any_call("user_id", "user")
        query.order.assert_called_with("created_at", desc=True)
