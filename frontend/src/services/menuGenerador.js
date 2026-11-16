import { api } from "./api";

export async function generarMenuSemanal(onProgreso = () => {}) {
  onProgreso("La IA está preparando y guardando tu menú. Puede tardar unos minutos...");
  return api.generarMenuSemanal();
}
