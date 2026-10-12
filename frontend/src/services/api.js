import { Platform } from "react-native";

// Cliente HTTP hacia el Backend (FastAPI). Centraliza la URL base, el
// token de sesión y el manejo de errores para que las pantallas no
// repitan lógica de fetch.

// En web las llamadas van al mismo origen (/api/v1) y metro.config.js las reenvía al
// backend (así no hace falta CORS). En el celular se usa la URL completa del .env.
const BASE_URL =
  Platform.OS === "web"
    ? "/api/v1"
    : process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

// Token de sesión en memoria. AuthContext lo actualiza al iniciar/cerrar
// sesión; cualquier llamada posterior a request() lo usa automáticamente.
let authToken = null;
export function setAuthToken(token) {
  authToken = token;
}

// Mensajes en español para los errores de dominio que devuelve el backend:
// { "error": "<NombreDelError>", "message": "..." }
const MENSAJES = {
  InvalidCredentials: "Correo o contraseña incorrectos.",
  EmailAlreadyRegistered: "Ese correo ya tiene una cuenta.",
  InvalidEmail: "El correo no es válido.",
  WeakPassword: "La contraseña es muy débil (mínimo 6 caracteres).",
  InvalidRequestBodyError: "Revisa los datos ingresados.",
  BackendUnavailable: "No se pudo conectar con el servidor. ¿Está encendido el backend?",
};

export class ApiError extends Error {
  constructor(status, codigo, mensaje) {
    super(mensaje);
    this.status = status;
    this.codigo = codigo;
    this.mensaje = mensaje;
  }
}

async function leerError(res) {
  let body = null;
  try {
    body = await res.json();
  } catch (_) {
    /* el cuerpo no era JSON */
  }
  // Para depurar: muestra en la consola el detalle real que devolvió el backend.
  console.warn(`[api] ${res.status} ${res.url}`, body);
  const codigo = body?.error;
  if (codigo && MENSAJES[codigo]) return new ApiError(res.status, codigo, MENSAJES[codigo]);
  // FastAPI devuelve { detail: [...] } cuando falla la validación del cuerpo (p. ej. correo mal escrito).
  if (res.status === 422) return new ApiError(res.status, "ValidationError", "Revisa los datos ingresados.");
  // El endpoint /ai/generate responde 504 (IA tardó demasiado) o 503 (sin mensajería) con { detail }.
  if (res.status === 504) return new ApiError(res.status, "AITimeout", "La IA tardó demasiado en responder.");
  if (res.status === 503) return new ApiError(res.status, "AIUnavailable", "El servicio de IA no está disponible.");
  return new ApiError(res.status, codigo, "El servidor tuvo un problema. Intenta de nuevo.");
}

async function request(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...options.headers };
  if (authToken) headers["Authorization"] = `Bearer ${authToken}`;

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  if (!res.ok) throw await leerError(res);
  if (res.status === 204) return null;
  return res.json();
}

export const api = {

  login: (email, password) =>
    request(`/auth/login`, { method: "POST", body: JSON.stringify({ email, password }) }),
  registrar: ({ email, password }) =>
    request(`/auth/register`, { method: "POST", body: JSON.stringify({ email, password }) }),


  getPreferencias: (usuarioId) => request(`/usuarios/${usuarioId}/preferencias`),
  guardarPreferencias: (usuarioId, data) =>
    request(`/usuarios/${usuarioId}/preferencias`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  // --- Menú semanal (generado por el servicio de Menú/Recetas) ---
  getMenuSemanal: (usuarioId) => request(`/usuarios/${usuarioId}/menu-semanal`),

  // --- Menú: endpoints reales del backend (los usa services/menuGenerador.js) ---
  getMenuActual: () => request(`/menu/current`), // null si aún no hay menú de esta semana
  crearMenu: () => request(`/menu/create`, { method: "POST" }), // OJO: no devuelve el id
  generarConIA: (prompt) =>
    request(`/ai/generate`, { method: "POST", body: JSON.stringify({ prompt }) }),
  getPlatosPorDia: (menuId, dia) => request(`/plato/day/${dia}?menu_id=${menuId}`),
  crearPlato: (plato) => request(`/plato/create`, { method: "POST", body: JSON.stringify(plato) }), // OJO: no devuelve el id
  eliminarPlato: (id) => request(`/plato/delete/${id}`, { method: "DELETE" }),
  crearIngrediente: (name) =>
    request(`/ingrediente/create`, { method: "POST", body: JSON.stringify({ name }) }),
  crearPlatoIngredientes: (lista) =>
    request(`/plato-ingrediente/create-many`, { method: "POST", body: JSON.stringify(lista) }),
  getIngredientesDePlato: (platoId) => request(`/plato-ingrediente/get-by-plato/${platoId}`),
  getIngrediente: (id) => request(`/ingrediente/get/${id}`),
  eliminarIngredientesDePlato: (platoId) =>
    request(`/plato-ingrediente/delete-by-plato/${platoId}`, { method: "DELETE" }),


  getListaDeCompras: (usuarioId) => request(`/usuarios/${usuarioId}/lista-compras`),
  confirmarCompra: (usuarioId) =>
    request(`/usuarios/${usuarioId}/lista-compras/confirmar`, { method: "POST" }),

 
  getEstadoPedido: (pedidoId) => request(`/pedidos/${pedidoId}/estado`),
};
