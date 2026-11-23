from abc import ABC, abstractmethod

from src.domain.entities.pedido import Pedido


class PedidoRepository(ABC):
    @abstractmethod
    async def create(self, pedido: Pedido) -> Pedido: ...

    @abstractmethod
    async def get_current(self, user_id: str) -> Pedido | None: ...

    @abstractmethod
    async def get_by_id(self, user_id: str, pedido_id: str) -> Pedido | None: ...

    @abstractmethod
    async def list_available(self) -> list[Pedido]: ...

    @abstractmethod
    async def list_assigned(self, repartidor_id: str) -> list[Pedido]: ...

    @abstractmethod
    async def get_by_id_for_courier(self, repartidor_id: str, pedido_id: str) -> Pedido | None: ...

    @abstractmethod
    async def assign(self, pedido_id: str, repartidor_id: str, repartidor: str | None = None) -> Pedido | None: ...

    @abstractmethod
    async def update_estado(self, pedido_id: str, repartidor_id: str, estado: str) -> Pedido | None: ...
