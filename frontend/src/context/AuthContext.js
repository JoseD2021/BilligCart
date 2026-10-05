import React, { createContext, useContext, useEffect, useState } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { api, setAuthToken } from "../services/api";

const AuthContext = createContext(null);
const STORAGE_KEY = "@planificador/session";

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null);
  const [token, setToken] = useState(null);
  const [cargandoSesion, setCargandoSesion] = useState(true);
  const [error, setError] = useState(null);

  // Al abrir la app, intenta restaurar la sesión guardada.
  useEffect(() => {
    (async () => {
      try {
        const guardado = await AsyncStorage.getItem(STORAGE_KEY);
        if (guardado) {
          const { usuario: u, token: t } = JSON.parse(guardado);
          setUsuario(u);
          setToken(t);
          setAuthToken(t);
        }
      } catch (e) {
        // Si falla la restauración, simplemente se pide iniciar sesión de nuevo.
        console.warn("No se pudo restaurar la sesión:", e.message);
      } finally {
        setCargandoSesion(false);
      }
    })();
  }, []);

  async function persistirSesion(usuarioData, tokenData) {
    setUsuario(usuarioData);
    setToken(tokenData);
    setAuthToken(tokenData);
    await AsyncStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ usuario: usuarioData, token: tokenData })
    );
  }

  async function iniciarSesion(email, password) {
    setError(null);
    try {
      const resp = await api.login(email, password);
      await persistirSesion(resp.usuario, resp.token);
      return true;
    } catch (e) {
      setError("Correo o contraseña incorrectos.");
      return false;
    }
  }

  async function registrarse(datos) {
    setError(null);
    try {
      const resp = await api.registrar(datos);
      await persistirSesion(resp.usuario, resp.token);
      return true;
    } catch (e) {
      setError("No se pudo crear la cuenta. Verifica los datos.");
      return false;
    }
  }

  // Modo demo: entra sin backend, usando un usuario falso en memoria.
  
  async function entrarModoDemo() {
    await persistirSesion({ id: "demo", nombre: "Usuario Demo" }, "token-demo");
  }

  async function cerrarSesion() {
    setUsuario(null);
    setToken(null);
    setAuthToken(null);
    await AsyncStorage.removeItem(STORAGE_KEY);
  }

  return (
    <AuthContext.Provider
      value={{
        usuario,
        token,
        estaAutenticado: !!token,
        cargandoSesion,
        error,
        iniciarSesion,
        registrarse,
        entrarModoDemo,
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
