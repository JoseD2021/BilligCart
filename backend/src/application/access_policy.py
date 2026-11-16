from src.domain.entities.user import User
from src.domain.errors import AccessDenied, ResourceNotFound
from src.domain.repositories.menu_repository import MenuRepository
from src.domain.repositories.plato_repository import PlatoRepository
from src.domain.repositories.plato_ingrediente_repository import PlatoIngredienteRepository


class AccessPolicy:
    def __init__(self, menus: MenuRepository, platos: PlatoRepository, relaciones: PlatoIngredienteRepository):
        self.menus = menus
        self.platos = platos
        self.relaciones = relaciones

    async def menu(self, user: User, menu_id: int):
        menu = await self.menus.get_by_id(menu_id)
        if menu is None or str(menu.user_id) != str(user.id):
            # No revelar si un recurso de otro usuario existe.
            raise ResourceNotFound("Menú no encontrado.")
        return menu

    async def plato(self, user: User, plato_id: int):
        plato = await self.platos.get_by_id(plato_id)
        if plato is None:
            raise ResourceNotFound("Plato no encontrado.")
        await self.menu(user, plato.menu_id)
        return plato

    async def relacion(self, user: User, relacion_id: int):
        relacion = await self.relaciones.get_by_id(relacion_id)
        if relacion is None:
            raise ResourceNotFound("Relación no encontrada.")
        await self.plato(user, relacion.plato_id)
        return relacion

    @staticmethod
    def catalog_admin(user: User):
        if user.role != "admin":
            raise AccessDenied("Se requiere un administrador para modificar el catálogo compartido.")
