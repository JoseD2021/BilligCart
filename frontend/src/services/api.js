// Cliente HTTP hacia el Backend (FastAPI). Centraliza la URL base, el
// token de sesión y el manejo de errores para que las pantallas no
// repitan lógica de fetch.

const BASE_URL = "http://localhost:8000"; // cambiar por la URL real del API Gateway/Backend

// Token de sesión en memoria. AuthContext lo actualiza al iniciar/cerrar
// sesión; cualquier llamada posterior a request() lo usa automáticamente.
let authToken = null;
export function setAuthToken(token) {
  authToken = token;
}

async function request(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...options.headers };
  if (authToken) headers["Authorization"] = `Bearer ${authToken}`;

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Error ${res.status}: ${body}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  // --- Autenticación ---
  login: (email, password) =>
    request(`/auth/login`, { method: "POST", body: JSON.stringify({ email, password }) }),
  registrar: (data) =>
    request(`/auth/registro`, { method: "POST", body: JSON.stringify(data) }),

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
