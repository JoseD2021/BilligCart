import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from src.domain.entities.pedido import Pedido
from src.infrastructure.api.v1.endpoints.compras import pedidos_con_estado_pago


def pedido(order_id):
    return Pedido(order_id, "user", 1, "key", [], 100, estado="pendiente")


def client_con_pagos(rows=None, error=None):
    query = MagicMock()
    query.select.return_value = query
    query.in_.return_value = query
    query.eq.return_value = query
    query.execute = AsyncMock(side_effect=error) if error else AsyncMock(
        return_value=SimpleNamespace(data=rows or []))
    client = MagicMock()
    client.table.return_value = query
    return client, query


class CourierPaymentStatusTests(unittest.IsolatedAsyncioTestCase):
    async def test_solo_marca_como_pagados_los_pedidos_confirmados(self):
        client, query = client_con_pagos([
            {"order_id": "pagado", "status": "succeeded"},
            {"order_id": "otro", "status": "succeeded"},
        ])
        result = await pedidos_con_estado_pago([pedido("pagado"), pedido("pendiente")], client)
        self.assertEqual(result[0]["pagado"], True)
        self.assertEqual(result[1]["pagado"], False)
        self.assertEqual(query.in_.call_args.args, ("order_id", ["pagado", "pendiente"]))

    async def test_sin_pedidos_no_consulta_la_base(self):
        client, _ = client_con_pagos()
        self.assertEqual(await pedidos_con_estado_pago([], client), [])
        client.table.assert_not_called()

    async def test_fallo_al_consultar_deja_estado_desconocido(self):
        client, _ = client_con_pagos(error=RuntimeError("Supabase no disponible"))
        result = await pedidos_con_estado_pago([pedido("p1")], client)
        self.assertIsNone(result[0]["pagado"])
