import asyncio
import json
import logging
import unicodedata
from dataclasses import dataclass

from src.application.commands.ingrediente.create_ingrediente import (
    CreateIngredientCommand,
    CreateIngredientHandler,
)
from src.application.commands.menu.create_menu import (
    CreateMenuCommand,
    CreateMenuHandler,
)
from src.application.commands.plato.create_plato import (
    CreatePlatoCommand,
    CreatePlatoHandler,
)
from src.application.commands.plato.delete_plato_by_id import (
    DeletePlatoByIdCommand,
    DeletePlatoHandler,
)
from src.application.commands.plato_ingrediente.create_many_plato_ingrediente import (
    CreateManyPlatoIngredienteCommandHandler,
)
from src.application.commands.plato_ingrediente.create_plato_ingrediente import (
    CreatePlatoIngredienteRecetaCommand,
)
from src.application.commands.plato_ingrediente.delete_plato_ingrediente_by_platoid import (
    DeletePlatoIngredienteByPlatoIdCommand,
    DeletePlatoIngredienteByPlatoIdHandler,
)
from src.application.queries.ingrediente.get_all_ingredientes import (
    GetAllIngredientesHandler,
)
from src.application.queries.menu.get_current_menu import (
    GetCurrentMenuHandler,
    GetCurrentMenuQuery,
)
from src.application.queries.plato.get_plato_by_day import (
    GetPlatoByDayHandler,
    GetPlatoByDayQuery,
)
from src.domain.entities.plato import Plato
from src.domain.entities.plato_ingrediente import PlatoIngrediente
from src.domain.enums.plato_tipo import PlatoTipo
from src.domain.errors import MenuGenerationError
from src.domain.repositories.ingrediente_repository import IngredienteRepository
from src.domain.repositories.menu_repository import MenuRepository
from src.domain.repositories.plato_ingrediente_repository import (
    PlatoIngredienteRepository,
)
from src.domain.repositories.plato_repository import PlatoRepository


logger = logging.getLogger(__name__)


DIAS = ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo")
MOMENTOS = (
    ("desayuno", PlatoTipo.DESAYUNO),
    ("almuerzo", PlatoTipo.ALMUERZO),
    ("cena", PlatoTipo.CENA),
)
COMIDAS_POR_SEMANA = len(DIAS) * len(MOMENTOS)
TAMANO_LOTE = 50
CONCURRENCIA = 6


# Estructuras con los campos que devuelve la IA, normalizadas al dominio.
@dataclass(frozen=True)
class _IngredienteGenerado:
    clave: str
    nombre: str
    cantidad: float
    unidad: str


@dataclass(frozen=True)
class _PlatoGenerado:
    day: int
    tipo: PlatoTipo
    nombre: str
    ingredientes: list[_IngredienteGenerado]


class PersistGeneratedMenuUseCase:
    """Interpreta la respuesta cruda de la IA y guarda el menú semanal.

    Orquesta los comandos y queries existentes (commands/, queries/) en lugar
    de tocar los repositorios directamente, para no duplicar la lógica de
    construcción/validación que ya vive en esos casos de uso.
    """

    def __init__(
        self,
        menu: MenuRepository,
        plato: PlatoRepository,
        ingrediente: IngredienteRepository,
        plato_ingrediente: PlatoIngredienteRepository,
    ):
        self._get_current_menu = GetCurrentMenuHandler(menu)
        self._create_menu = CreateMenuHandler(menu)

        self._get_plato_by_day = GetPlatoByDayHandler(plato)
        self._create_plato = CreatePlatoHandler(plato)
        self._delete_plato = DeletePlatoHandler(plato)

        self._delete_relaciones = DeletePlatoIngredienteByPlatoIdHandler(
            plato_ingrediente
        )
        self._create_many_relaciones = (
            CreateManyPlatoIngredienteCommandHandler(plato_ingrediente)
        )

        self._get_all_ingredientes = GetAllIngredientesHandler(ingrediente)
        self._create_ingrediente = CreateIngredientHandler(ingrediente)

    async def execute(self, user_id: str, response: str) -> int:
        """Guarda el menú y devuelve la cantidad de platos persistidos."""
        platos = _interpretar_menu(response)
        await self._persistir(user_id, platos)
        return len(platos)

    async def _persistir(
        self,
        user_id: str,
        platos: list[_PlatoGenerado],
    ) -> None:
        menu_id = await self._asegurar_menu(user_id)

        antiguos = await self._listar_platos(menu_id)
        if antiguos:
            await self._borrar_platos(
                [plato.id for plato in antiguos if plato.id is not None]
            )

        try:
            async def crear_plato(plato: _PlatoGenerado) -> None:
                await self._create_plato.handle(
                    CreatePlatoCommand(
                        menu_id=menu_id,
                        type=plato.tipo,
                        name=plato.nombre,
                        day=plato.day,
                    )
                )

            await self._en_lotes(platos, crear_plato)

            nuevos = await self._listar_platos(menu_id)
            id_por_comida = {
                _clave_comida(plato.day, plato.type): plato.id
                for plato in nuevos
                if plato.id is not None
            }

            id_por_ingrediente: dict[str, int] = {}
            todos = await self._get_all_ingredientes.handle()
            for ingrediente in todos:
                clave = _sin_acentos(ingrediente.name)
                if clave and clave not in id_por_ingrediente:
                    id_por_ingrediente[clave] = ingrediente.id

            por_crear: dict[str, str] = {}
            for plato in platos:
                for ingrediente in plato.ingredientes:
                    if ingrediente.clave not in id_por_ingrediente:
                        por_crear.setdefault(
                            ingrediente.clave,
                            ingrediente.nombre,
                        )

            async def crear_ingrediente(item) -> None:
                clave, nombre = item
                fila = await self._create_ingrediente.handle(
                    CreateIngredientCommand(name=nombre)
                )
                fila_id = _fila_id(fila)
                if fila_id is None:
                    raise MenuGenerationError(
                        "No se pudo guardar un ingrediente."
                    )
                id_por_ingrediente[clave] = fila_id

            await self._en_lotes(list(por_crear.items()), crear_ingrediente)

            relaciones: list[PlatoIngrediente] = []
            for plato in platos:
                plato_id = id_por_comida.get(
                    _clave_comida(plato.day, plato.tipo)
                )
                if plato_id is None:
                    raise MenuGenerationError(
                        "No se pudo guardar el menú completo. "
                        "Intenta de nuevo."
                    )
                for ingrediente in plato.ingredientes:
                    relaciones.append(
                        PlatoIngrediente(
                            quantity=ingrediente.cantidad,
                            unit=ingrediente.unidad,
                            plato_id=plato_id,
                            ingrediente_id=id_por_ingrediente[ingrediente.clave],
                        )
                    )

            for inicio in range(0, len(relaciones), TAMANO_LOTE):
                await self._create_many_relaciones.handle(
                    relaciones[inicio:inicio + TAMANO_LOTE]
                )
        except Exception:
            await self._revertir(menu_id)
            raise

    async def _asegurar_menu(self, user_id: str) -> int:
        menu = await self._get_current_menu.handle(
            GetCurrentMenuQuery(user_id=user_id)
        )
        if menu is None or menu.id is None:
            await self._create_menu.handle(CreateMenuCommand(user_id=user_id))
            menu = await self._get_current_menu.handle(
                GetCurrentMenuQuery(user_id=user_id)
            )

        if menu is None or menu.id is None:
            raise MenuGenerationError("No se pudo crear el menú de esta semana.")
        return menu.id

    async def _listar_platos(self, menu_id: int) -> list[Plato]:
        por_dia = await asyncio.gather(
            *(
                self._get_plato_by_day.handle(
                    GetPlatoByDayQuery(menu_id=menu_id, day=dia)
                )
                for dia in range(1, 8)
            )
        )
        return [plato for dia in por_dia for plato in dia]

    async def _borrar_plato(self, plato_id: int) -> None:
        await self._delete_relaciones.handle(
            DeletePlatoIngredienteByPlatoIdCommand(plato_id=plato_id)
        )
        await self._delete_plato.handle(DeletePlatoByIdCommand(id=plato_id))

    async def _borrar_platos(self, ids: list[int]) -> None:
        await self._en_lotes(ids, self._borrar_plato)

    async def _revertir(self, menu_id: int) -> None:
        try:
            parciales = await self._listar_platos(menu_id)
            await self._borrar_platos(
                [plato.id for plato in parciales if plato.id is not None]
            )
        except Exception:
            logger.exception(
                "No se pudo limpiar la generación fallida del menú %s.",
                menu_id,
            )

    async def _en_lotes(self, items, tarea, concurrencia: int = CONCURRENCIA) -> None:
        siguiente = 0
        fallo: Exception | None = None

        async def trabajador() -> None:
            nonlocal siguiente, fallo
            while fallo is None and siguiente < len(items):
                indice = siguiente
                siguiente += 1
                try:
                    await tarea(items[indice])
                except Exception as exc:  # noqa: BLE001
                    if fallo is None:
                        fallo = exc

        trabajadores = [
            trabajador()
            for _ in range(min(concurrencia, len(items)))
        ]
        if trabajadores:
            await asyncio.gather(*trabajadores)

        if fallo is not None:
            raise fallo


def _fila_id(fila) -> int | None:
    if fila is None:
        return None
    if isinstance(fila, dict):
        return fila.get("id")
    return getattr(fila, "id", None)


def _sin_acentos(valor) -> str:
    texto = unicodedata.normalize(
        "NFD",
        str(valor if valor is not None else "").lower(),
    )
    return "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    ).strip()


def _capitalizar(texto: str) -> str:
    return f"{texto[0].upper()}{texto[1:]}" if texto else texto


def _tipo_key(tipo) -> str:
    return _sin_acentos(getattr(tipo, "value", tipo))


def _clave_comida(day: int, tipo) -> str:
    return f"{day}-{_tipo_key(tipo)}"


def _por_clave(obj) -> dict:
    if not isinstance(obj, dict):
        return {}
    return {_sin_acentos(k): v for k, v in obj.items()}


def _primer_valor(obj, *claves):
    if not isinstance(obj, dict):
        return None
    for clave in claves:
        valor = obj.get(clave)
        if valor is not None:
            return valor
    return None


def _extraer_json(raw):
    if isinstance(raw, dict):
        return raw

    texto = str(raw or "")
    inicio = texto.find("{")
    fin = texto.rfind("}")
    if inicio == -1 or fin <= inicio:
        raise MenuGenerationError(
            "La IA devolvió una respuesta vacía. Intenta de nuevo."
        )
    try:
        return json.loads(texto[inicio:fin + 1])
    except json.JSONDecodeError as exc:
        raise MenuGenerationError(
            "La IA devolvió una respuesta que no se pudo leer. "
            "Intenta de nuevo."
        ) from exc


def _interpretar_menu(raw) -> list[_PlatoGenerado]:
    data = _extraer_json(raw)
    if not isinstance(data, dict):
        data = {}

    semana = _por_clave(
        data.get("menuSemanal") or data.get("menu") or data
    )

    platos: list[_PlatoGenerado] = []
    faltan = 0

    for indice, clave_dia in enumerate(DIAS):
        dia = _por_clave(_primer_valor(semana, clave_dia))

        for clave, tipo in MOMENTOS:
            comida = _primer_valor(dia, clave)
            nombre = str(
                _primer_valor(comida, "name", "nombre") or ""
            ).strip()
            if not nombre:
                faltan += 1
                continue

            vistos: set[str] = set()
            ingredientes: list[_IngredienteGenerado] = []
            lista = _primer_valor(comida, "ingredients", "ingredientes")
            for item in lista if isinstance(lista, list) else []:
                nombre_ing = str(
                    _primer_valor(item, "name", "nombre") or ""
                ).strip()
                clave_ing = _sin_acentos(nombre_ing)
                if not clave_ing or clave_ing in vistos:
                    continue
                vistos.add(clave_ing)

                try:
                    cantidad = float(
                        _primer_valor(item, "cantidad", "quantity") or 0
                    )
                except (TypeError, ValueError):
                    cantidad = 0

                unidad = (
                    str(_primer_valor(item, "unit", "unidad") or "").strip()
                    or "unidad"
                )

                ingredientes.append(
                    _IngredienteGenerado(
                        clave=clave_ing,
                        nombre=_capitalizar(nombre_ing),
                        cantidad=cantidad if cantidad > 0 else 1,
                        unidad=unidad,
                    )
                )

            platos.append(
                _PlatoGenerado(
                    day=indice + 1,
                    tipo=tipo,
                    nombre=nombre,
                    ingredientes=ingredientes,
                )
            )

    if faltan > 0:
        raise MenuGenerationError(
            "La IA no devolvió el menú completo "
            f"(faltaron {faltan} de {COMIDAS_POR_SEMANA} comidas). "
            "Intenta de nuevo."
        )

    return platos
