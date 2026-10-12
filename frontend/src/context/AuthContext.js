import React, { createContext, useContext, useEffect, useState } from "react";
import { supabase } from "../services/supabase";
import { setAuthToken } from "../services/api";

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

  function aplicarSesion(s) {
    setSession(s);
    // Token para las llamadas que aún van al backend (p. ej. confirmar compra).
    setAuthToken(s?.access_token ?? null);
  }

  useEffect(() => {
    supabase.auth
      .getSession()
      .then(({ data }) => aplicarSesion(data.session))
      .catch((e) => console.warn("No se pudo restaurar la sesión:", e.message))
      .finally(() => setCargandoSesion(false));

    const { data } = supabase.auth.onAuthStateChange((_evento, nueva) => aplicarSesion(nueva));
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

  async function registrarse({ email, password }) {
    setError(null);
    try {
      const { data, error: e } = await supabase.auth.signUp({ email, password });
      if (e) throw e;
      // Con "Confirm email" activo y el correo ya registrado, Supabase no da error:
      // devuelve un usuario sin identidades.
      if (data.user && (data.user.identities ?? []).length === 0) {
        setError("Ese correo ya tiene una cuenta.");
        return { ok: false };
      }
      // Con "Confirm email" activo no hay sesión hasta confirmar el correo.
      return { ok: true, confirmarCorreo: !data.session };
    } catch (e) {
      console.warn("signUp:", e.message);
      setError(mensajeDeError(e));
      return { ok: false };
    }
  }

  async function cerrarSesion() {
    await supabase.auth.signOut();
  }

  const usuario = session?.user
    ? {
        id: session.user.id,
        email: session.user.email,
        nombre: session.user.user_metadata?.nombre,
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
