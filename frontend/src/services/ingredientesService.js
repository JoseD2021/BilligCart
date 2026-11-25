import { api } from "./api";

// Coincide con ScrapeIngredienteHandler._DAYS_TO_UPDATE del backend, que vuelve
// a validar la antigüedad antes de scrapear. Aquí evitamos la llamada innecesaria.
export const DIAS_PARA_ACTUALIZAR = 7;
const MS_POR_DIA = 24 * 60 * 60 * 1000;

export function necesitaFetch(ultimoFetch, ahora = Date.now()) {
  if (!ultimoFetch) return true;
  const fecha = Date.parse(ultimoFetch);
  return Number.isNaN(fecha) || ahora - fecha >= DIAS_PARA_ACTUALIZAR * MS_POR_DIA;
}

export function idsParaActualizar(lista, ahora = Date.now()) {
  const ultimosFetch = lista?.ultimos_fetch ?? {};
  const ids = new Set();
  for (const item of lista?.items ?? []) {
    if (necesitaFetch(ultimosFetch[item.ingrediente_id], ahora)) {
      ids.add(item.ingrediente_id);
    }
  }
  return [...ids];
}

// Cada fetch dispara dos scrapers: los hacemos en serie para no saturar el backend.
// Un fallo individual no impide cotizar los demás ingredientes.
export async function actualizarPrecios(lista, ahora = Date.now()) {
  const ids = idsParaActualizar(lista, ahora);
  const resultado = { actualizados: 0, errores: [] };
  for (const id of ids) {
    try {
      await api.fetchIngrediente(id);
      resultado.actualizados += 1;
    } catch (error) {
      resultado.errores.push({ id, mensaje: error?.message ?? "Error desconocido" });
    }
  }
  return resultado;
}
