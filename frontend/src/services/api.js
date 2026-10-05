// Cliente HTTP hacia el Backend (FastAPI). Centraliza la URL base y el
// manejo de errores para que las pantallas no repitan lógica de fetch.

const BASE_URL = "http://localhost:8000"; // cambiar por la URL real del API Gateway/Backend

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Error ${res.status}: ${body}`);
  }
  return res.json();
}

export const api = {
  // --- Preferencias del usuario ---
  getPreferencias: (usuarioId) => request(`/usuarios/${usuarioId}/preferencias`),
  guardarPreferencias: (usuarioId, data) =>
    request(`/usuarios/${usuarioId}/preferencias`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  // --- Menú semanal (generado por el servicio de Menú/Recetas) ---
  getMenuSemanal: (usuarioId) => request(`/usuarios/${usuarioId}/menu-semanal`),

  // --- Lista de compras (construida con el patrón Builder en el backend) ---
  getListaDeCompras: (usuarioId) => request(`/usuarios/${usuarioId}/lista-compras`),
  confirmarCompra: (usuarioId) =>
    request(`/usuarios/${usuarioId}/lista-compras/confirmar`, { method: "POST" }),

  // --- Estado del pedido (servicio propio de Repartidores) ---
  getEstadoPedido: (pedidoId) => request(`/pedidos/${pedidoId}/estado`),
};
