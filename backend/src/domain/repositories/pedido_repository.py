from abc import ABC, abstractmethod

from src.domain.entities.pedido import Pedido


class PedidoRepository(ABC):
    @abstractmethod
    async def create(self, pedido: Pedido) -> Pedido: ...

    @abstractmethod
    async def get_current(self, user_id: str) -> Pedido | None: ...

    @abstractmethod
    async def get_by_id(self, user_id: str, pedido_id: str) -> Pedido | None: ...
