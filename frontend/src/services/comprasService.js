import { api } from "./api";
import { actualizarPrecios, idsParaActualizar } from "./ingredientesService";

// Caso de uso de la pantalla de compras: obtiene la lista y, solo si hay
// ingredientes cuya última cotización supera la ventana configurada, pide
// precios nuevos y devuelve la lista ya actualizada.
export async function getListaCompras({ refrescar = true, onLista = () => {}, onActualizando = () => {} } = {}) {
  let lista = await api.getListaDeCompras();
  onLista(lista);
  if (!refrescar || idsParaActualizar(lista).length === 0) {
    return { lista, actualizacion: null };
  }

  onActualizando();
  const actualizacion = await actualizarPrecios(lista);
  if (actualizacion.actualizados > 0) {
    lista = await api.getListaDeCompras();
  }
  return { lista, actualizacion };
}

export function confirmarCompra() {
  return api.confirmarCompra();
}
