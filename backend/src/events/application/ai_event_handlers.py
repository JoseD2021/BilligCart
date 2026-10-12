import asyncio
import json
import logging
import unicodedata
from dataclasses import dataclass

from src.domain.entities.ingrediente import Ingrediente
from src.domain.entities.menu import Menu
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
from src.events.contracts.ai_menu_events import (
    MenuGenerationCompleted,
    MenuGenerationFailed,
    MenuGenerationStarted,
)


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


# clases con los parametros usados en el frontend
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


@dataclass
class MenuRepositories:
    """Repositorios que necesita el guardado del menú, como interfaces de dominio."""

    menu: MenuRepository
    plato: PlatoRepository
    ingrediente: IngredienteRepository
    plato_ingrediente: PlatoIngredienteRepository


async def on_menu_generation_started(
    event: MenuGenerationStarted,
) -> None:
    logger.info(
        "Generación iniciada: request_id=%s model=%s",
        event.request_id,
        event.model,
    )


async def on_menu_generation_completed(
    event: MenuGenerationCompleted,
    repositories: MenuRepositories,
) -> None:
    logger.info(
        "Generación completada: request_id=%s model=%s duration_ms=%s",
        event.request_id,
        event.model,
        event.duration_ms,
    )

    if not event.user_id or not event.response:
        logger.warning(
            "El evento no trae user_id o respuesta; no se guarda el menú. "
            "request_id=%s",
            event.request_id,
        )
        return

    try:
        platos = _interpretar_menu(event.response)
        await _persistir_menu(repositories, event.user_id, platos)
    except Exception:
        logger.exception(
            "No se pudo guardar el menú generado. request_id=%s user_id=%s",
            event.request_id,
            event.user_id,
        )
        raise

    logger.info(
        "Menú guardado: request_id=%s user_id=%s platos=%s",
        event.request_id,
        event.user_id,
        len(platos),
    )


async def on_menu_generation_failed(
    event: MenuGenerationFailed,
) -> None:
    logger.warning(
        "Generación fallida: request_id=%s model=%s error_type=%s",
        event.request_id,
        event.model,
        event.error_type,
    )


# implementacion de los metodos usados en front al backend

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


# persistencia

async def _en_lotes(items, tarea, concurrencia: int = CONCURRENCIA) -> None:
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


async def _asegurar_menu(repo: MenuRepositories, user_id: str) -> int:
    menu = await repo.menu.get_current(user_id)
    if menu is None or menu.id is None:
        await repo.menu.create(Menu.default(user_id))
        menu = await repo.menu.get_current(user_id)

    if menu is None or menu.id is None:
        raise MenuGenerationError("No se pudo crear el menú de esta semana.")
    return menu.id


async def _listar_platos(
    repo: MenuRepositories,
    menu_id: int,
) -> list[Plato]:
    por_dia = await asyncio.gather(
        *(repo.plato.get_by_menu_day(menu_id, dia) for dia in range(1, 8))
    )
    return [plato for dia in por_dia for plato in dia]


async def _borrar_plato(repo: MenuRepositories, plato_id: int) -> None:
    await repo.plato_ingrediente.delete_by_plato(plato_id)
    await repo.plato.delete_by_id(plato_id)


async def _borrar_platos(
    repo: MenuRepositories,
    ids: list[int],
) -> None:
    await _en_lotes(ids, lambda plato_id: _borrar_plato(repo, plato_id))


async def _revertir(repo: MenuRepositories, menu_id: int) -> None:
    try:
        parciales = await _listar_platos(repo, menu_id)
        await _borrar_platos(
            repo,
            [plato.id for plato in parciales if plato.id is not None],
        )
    except Exception:
        logger.exception(
            "No se pudo limpiar la generación fallida del menú %s.",
            menu_id,
        )


def _fila_id(fila) -> int | None:
    if fila is None:
        return None
    if isinstance(fila, dict):
        return fila.get("id")
    return getattr(fila, "id", None)


async def _persistir_menu(
    repo: MenuRepositories,
    user_id: str,
    platos: list[_PlatoGenerado],
) -> None:
    menu_id = await _asegurar_menu(repo, user_id)

    antiguos = await _listar_platos(repo, menu_id)
    if antiguos:
        await _borrar_platos(
            repo,
            [plato.id for plato in antiguos if plato.id is not None],
        )

    try:
        async def crear_plato(plato: _PlatoGenerado) -> None:
            await repo.plato.create(
                Plato.default(
                    menu_id=menu_id,
                    type=plato.tipo,
                    name=plato.nombre,
                    day=plato.day,
                )
            )

        await _en_lotes(platos, crear_plato)

        nuevos = await _listar_platos(repo, menu_id)
        id_por_comida = {
            _clave_comida(plato.day, plato.type): plato.id
            for plato in nuevos
            if plato.id is not None
        }

        id_por_ingrediente: dict[str, int] = {}
        for ingrediente in await repo.ingrediente.get_all():
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
            fila = await repo.ingrediente.create(
                Ingrediente.default(name=nombre)
            )
            fila_id = _fila_id(fila)
            if fila_id is None:
                raise MenuGenerationError(
                    "No se pudo guardar un ingrediente."
                )
            id_por_ingrediente[clave] = fila_id

        await _en_lotes(list(por_crear.items()), crear_ingrediente)

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
            await repo.plato_ingrediente.create_many(
                relaciones[inicio:inicio + TAMANO_LOTE]
            )
    except Exception:
        await _revertir(repo, menu_id)
        raise
