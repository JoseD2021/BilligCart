import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from src.infrastructure.supabase.repositories.pedido_repository import SupabasePedidoRepository


def pedido_row(**overrides):
    row = {
        "id": "order-1", "user_id": "customer-1", "menu_id": 1, "checkout_key": "key",
        "items": [], "total": 100, "estado": "confirmado",
        "repartidor_id": "courier-1",
    }
    row.update(overrides)
    return row


def database(rows):
    query = MagicMock()
    for name in ("select", "eq", "in_", "is_", "order", "limit"):
        getattr(query, name).return_value = query
    query.execute = AsyncMock(return_value=SimpleNamespace(data=rows))
    client = MagicMock()
    client.table.return_value = query
    client.auth.admin.get_user_by_id = AsyncMock()
    return client


class CourierEmailFromFkTests(unittest.IsolatedAsyncioTestCase):
    async def test_email_se_resuelve_desde_auth_por_repartidor_id(self):
        client = database([pedido_row()])
        client.auth.admin.get_user_by_id = AsyncMock(return_value=SimpleNamespace(
            user=SimpleNamespace(email="courier@example.com")))
        pedido = await SupabasePedidoRepository(client).get_by_id("customer-1", "order-1")
        self.assertEqual(pedido.repartidor_email, "courier@example.com")
        client.auth.admin.get_user_by_id.assert_awaited_once_with("courier-1")

    async def test_sin_repartidor_no_se_consulta_auth(self):
        client = database([pedido_row(repartidor_id=None)])
        pedido = await SupabasePedidoRepository(client).get_current("customer-1")
        self.assertIsNone(pedido.repartidor_email)
        client.auth.admin.get_user_by_id.assert_not_awaited()

    async def test_fallo_de_auth_no_impide_devolver_el_pedido(self):
        client = database([pedido_row()])
        client.auth.admin.get_user_by_id = AsyncMock(side_effect=RuntimeError("Auth no disponible"))
        pedidos = await SupabasePedidoRepository(client).list_for_user("customer-1")
        self.assertIsNone(pedidos[0].repartidor_email)
