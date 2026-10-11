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
  const codigo = body?.error;
  if (codigo && MENSAJES[codigo]) return new ApiError(res.status, codigo, MENSAJES[codigo]);
  // FastAPI devuelve { detail: [...] } cuando falla la validación del cuerpo (p. ej. correo mal escrito).
  if (res.status === 422) return new ApiError(res.status, "ValidationError", "Revisa los datos ingresados.");
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
  // --- Autenticación ---
  login: (email, password) =>
    request(`/auth/login`, { method: "POST", body: JSON.stringify({ email, password }) }),
  registrar: ({ email, password }) =>
    request(`/auth/register`, { method: "POST", body: JSON.stringify({ email, password }) }),

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
