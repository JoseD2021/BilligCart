import { Platform } from "react-native";

// Cliente HTTP hacia el Backend (FastAPI). Centraliza la URL base, el
// token de sesión y el manejo de errores para que las pantallas no
// repitan lógica de fetch.

// En web las llamadas van al mismo origen (/api/v1) y metro.config.js las reenvía al
// backend (así no hace falta CORS). En el celular se usa la URL completa del .env.
const BASE_URL =
  Platform.OS === "web"
    ? "/api/v1"
    : process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000/v1";

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
  // La generación puede agotar el tiempo de espera o no tener mensajería disponible.
  if (res.status === 504) return new ApiError(res.status, "AITimeout", "La IA tardó demasiado en responder.");
  if (res.status === 503) return new ApiError(res.status, "AIUnavailable", "El servicio de IA no está disponible.");
  return new ApiError(res.status, codigo, body?.message ?? (typeof body?.detail === "string" ? body.detail : "El servidor tuvo un problema. Intenta de nuevo."));
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
  solicitarPago: (orderId, key) => request("/pagos", {
    method: "POST", headers: { "Idempotency-Key": key }, body: JSON.stringify({ order_id: orderId }),
  }),
  getPagoActual: (orderId) => request(`/pagos/pedido/${encodeURIComponent(orderId)}`),
  getPreferencias: () => request("/preferencias"),
  guardarPreferencias: (data) => request("/preferencias", { method: "PUT", body: JSON.stringify(data) }),
  getMenuSemanal: () => request("/menu/weekly"),
  generarMenuSemanal: () => request("/menu/generate", { method: "POST" }),
  getListaDeCompras: () => request("/compras"),
  confirmarCompra: () => request("/compras/confirmar", { method: "POST" }),
  getPedidoActual: () => request("/pedidos/current"),
  getEstadoPedido: (id) => request(`/pedidos/${encodeURIComponent(id)}/estado`),
};
