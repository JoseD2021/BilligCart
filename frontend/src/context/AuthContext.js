import React, { createContext, useContext, useEffect, useState } from "react";
import { supabase } from "../services/supabase";
import { api, setAuthToken } from "../services/api";

const AuthContext = createContext(null);

// Traduce los errores de Supabase Auth (error.code) a mensajes para el usuario.
function mensajeDeError(e) {
  switch (e?.code) {
    case "invalid_credentials":
      return "Correo o contraseña incorrectos.";
    case "email_not_confirmed":
      return "Debes confirmar tu correo antes de iniciar sesión. Revisa tu bandeja de entrada.";
    case "user_already_exists":
    case "email_exists":
      return "Ese correo ya tiene una cuenta.";
    case "weak_password":
      return "La contraseña es muy débil (mínimo 6 caracteres).";
    case "email_address_invalid":
    case "validation_failed":
      return "El correo no es válido.";
    case "over_request_rate_limit":
    case "over_email_send_rate_limit":
      return "Demasiados intentos. Espera un momento e intenta de nuevo.";
  }
  const m = (e?.message ?? "").toLowerCase();
  if (m.includes("fetch") || m.includes("network")) {
    return "No se pudo conectar con Supabase. Revisa EXPO_PUBLIC_SUPABASE_URL en frontend/.env y tu conexión.";
  }
  if (m.includes("invalid api key") || m.includes("apikey")) {
    return "La clave de Supabase es inválida. Revisa EXPO_PUBLIC_SUPABASE_ANON_KEY en frontend/.env y reinicia con: npx expo start -c";
  }
  return "No se pudo completar la operación. Intenta de nuevo.";
}

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null);
  const [cargandoSesion, setCargandoSesion] = useState(true);
  const [error, setError] = useState(null);

  const [backendUser, setBackendUser] = useState(null);

  async function cargarUsuarioBackend(token) {
    if (!token) { setBackendUser(null); return; }
    try {
      setBackendUser(await api.getMe());
    } catch (e) {
      console.warn("No se pudo cargar /auth/me:", e.message);
      setBackendUser(null);
    }
  }

  function aplicarSesion(s) {
    setSession(s);
    setAuthToken(s?.access_token ?? null);
  }

  useEffect(() => {
    supabase.auth
      .getSession()
      .then(async ({ data }) => { aplicarSesion(data.session); await cargarUsuarioBackend(data.session?.access_token); })
      .catch((e) => console.warn("No se pudo restaurar la sesión:", e.message))
      .finally(() => setCargandoSesion(false));

    const { data } = supabase.auth.onAuthStateChange(async (_evento, nueva) => { aplicarSesion(nueva); await cargarUsuarioBackend(nueva?.access_token); });
    return () => data.subscription.unsubscribe();
  }, []);

  // Login directo contra Supabase Auth (sin pasar por el backend).
  async function iniciarSesion(email, password) {
    setError(null);
    try {
      const { error: e } = await supabase.auth.signInWithPassword({ email, password });
      if (e) throw e;
      return true; // onAuthStateChange actualiza la sesión y la navegación cambia sola
    } catch (e) {
      console.warn("signInWithPassword:", e.message);
      setError(mensajeDeError(e));
      return false;
    }
  }

  async function registrarse({ email, password, role = "user" }) {
    setError(null);
    try {
      // El backend crea el usuario y escribe su rol en public."Roles" con service key.
      const data = await api.register({ email, password, role });
      if (data.access_token && data.refresh_token) {
        const { error: e } = await supabase.auth.setSession({
          access_token: data.access_token,
          refresh_token: data.refresh_token,
        });
        if (e) throw e;
        aplicarSesion({
          access_token: data.access_token,
          refresh_token: data.refresh_token,
          user: { id: data.id, email: data.email },
        });
        await cargarUsuarioBackend(data.access_token);
        return { ok: true, confirmarCorreo: false };
      }
      // Con "Confirm email" activo no hay sesión hasta confirmar el correo.
      setBackendUser({ id: data.id, email: data.email, role: data.role });
      return { ok: true, confirmarCorreo: true };
    } catch (e) {
      console.warn("register:", e.message);
      setError(e?.codigo || e?.code ? mensajeDeError(e) : e?.message ?? mensajeDeError(e));
      return { ok: false };
    }
  }

  async function cerrarSesion() {
    await supabase.auth.signOut();
  }

  const rawRole = backendUser?.role ?? session?.user?.app_metadata?.role;
  const role = rawRole === "repartidor" ? "repartidor" : "user";
  const usuario = session?.user
    ? {
        id: session.user.id,
        email: session.user.email,
        nombre: session.user.user_metadata?.nombre,
        role,
      }
    : null;

  return (
    <AuthContext.Provider
      value={{
        usuario,
        session,
        estaAutenticado: !!session,
        cargandoSesion,
        error,
        iniciarSesion,
        registrarse,
        cerrarSesion,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de AuthProvider");
  return ctx;
}
